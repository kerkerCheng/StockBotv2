"""Decision Cohort 與 paper events 的 private transactional store。"""
from __future__ import annotations

import hashlib
import json
import math
import sqlite3
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Mapping

from storage.relational import (
    connect_sqlite,
    immediate_transaction,
    validate_private_destination,
)

from .models import (
    ContextBundle,
    CoverageResult,
    DecisionExecutionResult,
    PreparedAction,
    ProbeRecord,
    ProbeSizingResult,
    ShadowBaseline,
)


_SCHEMA_PATH = Path(__file__).with_name("schema.sql")


def _canonical_json(payload: Mapping[str, Any]) -> str:
    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _time(value: str, field: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, ValueError) as exc:
        raise ValueError(f"{field} must be an ISO-8601 timestamp") from exc
    if parsed.tzinfo is None:
        raise ValueError(f"{field} must include timezone")
    return parsed


def _ensure_execution_schema(conn: sqlite3.Connection) -> None:
    columns = {
        str(row["name"])
        for row in conn.execute("PRAGMA table_info(paper_events)")
    }
    additions = {
        "decision_id": "TEXT REFERENCES system_decisions(decision_id)",
        "corrects_paper_event_id": "TEXT REFERENCES paper_events(paper_event_id)",
        "approved_action_id": "TEXT",
    }
    for column, declaration in additions.items():
        if column not in columns:
            conn.execute(f"ALTER TABLE paper_events ADD COLUMN {column} {declaration}")
    conn.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_paper_events_decision_digest
        ON paper_events (decision_id, payload_digest)
        WHERE decision_id IS NOT NULL
        """
    )
    conn.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_live_choices_approved_action
        ON live_choices (approved_action_id)
        WHERE approved_action_id IS NOT NULL
        """
    )
    conn.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_paper_events_approved_action
        ON paper_events (approved_action_id)
        WHERE approved_action_id IS NOT NULL
        """
    )


@dataclass(frozen=True)
class CohortRecord:
    cohort_id: str
    dedupe_key: str
    company_id: str | None
    research_ticker: str | None


@dataclass(frozen=True)
class EventRecord:
    event_id: str
    cohort_id: str
    event_type: str
    payload_digest: str
    observed_at: str


class DecisionStore:
    """SQLite v1 authority；不提供 destructive reset。"""

    def __init__(self, conn: sqlite3.Connection, path: Path):
        self._conn = conn
        self.path = path

    @classmethod
    def open(
        cls,
        path: Path,
        *,
        private_root: Path,
        repo_root: Path,
    ) -> "DecisionStore":
        resolved = validate_private_destination(
            path,
            private_root=private_root,
            repo_root=repo_root,
        )
        conn = connect_sqlite(resolved)
        try:
            conn.executescript(_SCHEMA_PATH.read_text(encoding="utf-8"))
            _ensure_execution_schema(conn)
            conn.commit()
        except BaseException:
            conn.close()
            raise
        return cls(conn, resolved)

    def close(self) -> None:
        self._conn.close()

    def table_names(self) -> set[str]:
        rows = self._conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        ).fetchall()
        return {str(row["name"]) for row in rows}

    def table_columns(self, table: str) -> set[str]:
        if table not in self.table_names():
            raise ValueError(f"unknown table: {table}")
        return {
            str(row["name"])
            for row in self._conn.execute(f'PRAGMA table_info("{table}")')
        }

    def ensure_cohort(
        self,
        *,
        dedupe_key: str,
        company_id: str | None,
        research_ticker: str | None,
    ) -> CohortRecord:
        if not dedupe_key.strip():
            raise ValueError("dedupe_key is required")
        cohort_id = "dc_" + _digest(dedupe_key)[:32]
        with immediate_transaction(self._conn):
            self._conn.execute(
                """
                INSERT OR IGNORE INTO decision_cohorts (
                    cohort_id, dedupe_key, company_id, research_ticker
                ) VALUES (?, ?, ?, ?)
                """,
                (cohort_id, dedupe_key, company_id, research_ticker),
            )
            row = self._conn.execute(
                """
                SELECT cohort_id, dedupe_key, company_id, research_ticker
                FROM decision_cohorts WHERE dedupe_key = ?
                """,
                (dedupe_key,),
            ).fetchone()
        assert row is not None
        if row["company_id"] != company_id or row["research_ticker"] != research_ticker:
            raise ValueError("dedupe_key already belongs to a different identity")
        return CohortRecord(**dict(row))

    def append_event(
        self,
        *,
        cohort_id: str,
        event_type: str,
        payload: Mapping[str, Any],
        observed_at: str,
    ) -> EventRecord:
        if not event_type.strip() or not observed_at.strip():
            raise ValueError("event_type and observed_at are required")
        payload_json = _canonical_json(payload)
        payload_digest = _digest(payload_json)
        identity = _canonical_json(
            {
                "cohort_id": cohort_id,
                "event_type": event_type,
                "payload_digest": payload_digest,
                "observed_at": observed_at,
            }
        )
        event_id = "de_" + _digest(identity)[:32]
        with immediate_transaction(self._conn):
            self._conn.execute(
                """
                INSERT OR IGNORE INTO decision_events (
                    event_id, cohort_id, event_type, payload_json,
                    payload_digest, observed_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    event_id,
                    cohort_id,
                    event_type,
                    payload_json,
                    payload_digest,
                    observed_at,
                ),
            )
            row = self._conn.execute(
                """
                SELECT event_id, cohort_id, event_type, payload_digest, observed_at
                FROM decision_events
                WHERE cohort_id = ? AND event_type = ?
                  AND payload_digest = ? AND observed_at = ?
                """,
                (cohort_id, event_type, payload_digest, observed_at),
            ).fetchone()
        assert row is not None
        return EventRecord(**dict(row))

    def capture_signal_inception(
        self,
        *,
        dedupe_key: str,
        company_id: str,
        research_ticker: str,
        signal_payload: Mapping[str, Any],
        observed_at: str,
        shadow: Mapping[str, Any],
        evidence_admission_status: str,
        source_registry_status: str,
        research_priority: int,
    ) -> dict[str, Any]:
        """Atomically append Signal and create the cohort's one immutable Shadow。"""

        if not dedupe_key.strip():
            raise ValueError("dedupe_key is required")
        cohort_id = "dc_" + _digest(dedupe_key)[:32]
        shadow_id = "sh_" + _digest(cohort_id)[:32]
        signal_json = _canonical_json(signal_payload)
        signal_digest = _digest(signal_json)
        signal_identity = _canonical_json(
            {
                "cohort_id": cohort_id,
                "event_type": "qualified_signal",
                "payload_digest": signal_digest,
                "observed_at": observed_at,
            }
        )
        signal_event_id = "de_" + _digest(signal_identity)[:32]
        shadow_payload = {
            "shadow_id": shadow_id,
            "status": shadow.get("status"),
            "price": shadow.get("price"),
            "currency": shadow.get("currency"),
            "source": shadow.get("source"),
            "as_of": shadow.get("as_of"),
            "fetched_at": shadow.get("fetched_at"),
        }
        shadow_json = _canonical_json(shadow_payload)
        shadow_digest = _digest(shadow_json)
        shadow_event_id = "de_" + _digest(
            _canonical_json(
                {
                    "cohort_id": cohort_id,
                    "event_type": "shadow_inception",
                    "payload_digest": shadow_digest,
                    "observed_at": observed_at,
                }
            )
        )[:32]

        with immediate_transaction(self._conn):
            self._conn.execute(
                """
                INSERT OR IGNORE INTO decision_cohorts (
                    cohort_id, dedupe_key, company_id, research_ticker
                ) VALUES (?, ?, ?, ?)
                """,
                (cohort_id, dedupe_key, company_id, research_ticker),
            )
            cohort = self._conn.execute(
                """
                SELECT company_id, research_ticker
                FROM decision_cohorts WHERE dedupe_key = ?
                """,
                (dedupe_key,),
            ).fetchone()
            assert cohort is not None
            if (
                cohort["company_id"] != company_id
                or cohort["research_ticker"] != research_ticker
            ):
                raise ValueError("dedupe_key already belongs to a different identity")

            self._conn.execute(
                """
                INSERT OR IGNORE INTO decision_events (
                    event_id, cohort_id, event_type, payload_json,
                    payload_digest, observed_at
                ) VALUES (?, ?, 'qualified_signal', ?, ?, ?)
                """,
                (
                    signal_event_id,
                    cohort_id,
                    signal_json,
                    signal_digest,
                    observed_at,
                ),
            )
            shadow_cursor = self._conn.execute(
                """
                INSERT OR IGNORE INTO shadow_observations (
                    shadow_id, cohort_id, status, price, currency,
                    source, as_of, fetched_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    shadow_id,
                    cohort_id,
                    shadow_payload["status"],
                    shadow_payload["price"],
                    shadow_payload["currency"],
                    shadow_payload["source"],
                    shadow_payload["as_of"],
                    shadow_payload["fetched_at"],
                ),
            )
            shadow_created = shadow_cursor.rowcount == 1
            if shadow_created:
                self._conn.execute(
                    """
                    INSERT INTO decision_events (
                        event_id, cohort_id, event_type, payload_json,
                        payload_digest, observed_at
                    ) VALUES (?, ?, 'shadow_inception', ?, ?, ?)
                    """,
                    (
                        shadow_event_id,
                        cohort_id,
                        shadow_json,
                        shadow_digest,
                        observed_at,
                    ),
                )
            self._conn.execute(
                """
                INSERT INTO probe_projection (
                    cohort_id, status, evidence_admission_status,
                    source_registry_status, research_priority
                ) VALUES (?, 'active', ?, ?, ?)
                ON CONFLICT(cohort_id) DO UPDATE SET
                    evidence_admission_status = CASE
                        WHEN probe_projection.evidence_admission_status = 'eligible_for_review'
                            THEN probe_projection.evidence_admission_status
                        ELSE excluded.evidence_admission_status
                    END,
                    source_registry_status = excluded.source_registry_status,
                    research_priority = excluded.research_priority,
                    updated_at = datetime('now')
                """,
                (
                    cohort_id,
                    evidence_admission_status,
                    source_registry_status,
                    research_priority,
                ),
            )
        return {
            "cohort_id": cohort_id,
            "signal_event_id": signal_event_id,
            "shadow_id": shadow_id,
            "shadow_created": shadow_created,
        }

    def list_events(
        self, cohort_id: str, *, event_type: str | None = None
    ) -> list[EventRecord]:
        sql = """
            SELECT event_id, cohort_id, event_type, payload_digest, observed_at
            FROM decision_events WHERE cohort_id = ?
        """
        params: list[Any] = [cohort_id]
        if event_type is not None:
            sql += " AND event_type = ?"
            params.append(event_type)
        sql += " ORDER BY observed_at, event_id"
        return [EventRecord(**dict(row)) for row in self._conn.execute(sql, params)]

    def get_shadow(self, cohort_id: str) -> ShadowBaseline:
        row = self._conn.execute(
            """
            SELECT shadow_id, cohort_id, status, price, currency,
                   source, as_of, fetched_at
            FROM shadow_observations WHERE cohort_id = ?
            """,
            (cohort_id,),
        ).fetchone()
        if row is None:
            raise KeyError(f"shadow not found for {cohort_id}")
        return ShadowBaseline(**dict(row))

    def count_shadows(self, cohort_id: str) -> int:
        row = self._conn.execute(
            "SELECT COUNT(*) AS count FROM shadow_observations WHERE cohort_id = ?",
            (cohort_id,),
        ).fetchone()
        return int(row["count"])

    def get_probe(self, cohort_id: str) -> ProbeRecord:
        row = self._conn.execute(
            """
            SELECT cohort_id, status, evidence_admission_status,
                   source_registry_status, research_priority
            FROM probe_projection WHERE cohort_id = ?
            """,
            (cohort_id,),
        ).fetchone()
        if row is None:
            raise KeyError(f"probe not found for {cohort_id}")
        return ProbeRecord(**dict(row))

    def table_count(self, table: str) -> int:
        if table not in self.table_names():
            raise ValueError(f"unknown table: {table}")
        row = self._conn.execute(f'SELECT COUNT(*) AS count FROM "{table}"').fetchone()
        return int(row["count"])

    def record_holdings_confirmation(
        self, sheet_digest: str, *, confirmed_at: str
    ) -> str:
        if len(sheet_digest) != 64 or not confirmed_at.strip():
            raise ValueError("holdings confirmation requires digest and confirmed_at")
        confirmation_id = "hc_" + _digest(f"{sheet_digest}:{confirmed_at}")[:32]
        with immediate_transaction(self._conn):
            self._conn.execute(
                """
                INSERT OR IGNORE INTO holdings_confirmations (
                    confirmation_id, sheet_digest, confirmed_at
                ) VALUES (?, ?, ?)
                """,
                (confirmation_id, sheet_digest, confirmed_at),
            )
        return confirmation_id

    def latest_holdings_confirmation(self, sheet_digest: str) -> dict[str, Any] | None:
        row = self._conn.execute(
            """
            SELECT confirmation_id, sheet_digest, confirmed_at
            FROM holdings_confirmations
            WHERE sheet_digest = ?
            ORDER BY confirmed_at DESC, confirmation_id DESC
            LIMIT 1
            """,
            (sheet_digest,),
        ).fetchone()
        return dict(row) if row is not None else None

    def freeze_context_bundle(
        self,
        *,
        cohort_id: str,
        digest: str,
        evaluation_at: str,
        payload: Mapping[str, Any],
    ) -> ContextBundle:
        payload_json = _canonical_json(payload)
        if _digest(payload_json) != digest:
            raise ValueError("context digest mismatch")
        context_id = "ctx_" + digest[:32]
        with immediate_transaction(self._conn):
            self._conn.execute(
                """
                INSERT OR IGNORE INTO context_bundles (
                    context_id, cohort_id, context_digest,
                    evaluation_at, payload_json
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (context_id, cohort_id, digest, evaluation_at, payload_json),
            )
            row = self._conn.execute(
                """
                SELECT context_id, cohort_id, context_digest,
                       evaluation_at, payload_json
                FROM context_bundles WHERE context_digest = ?
                """,
                (digest,),
            ).fetchone()
        assert row is not None
        if row["cohort_id"] != cohort_id or row["payload_json"] != payload_json:
            raise ValueError("context digest already belongs to different content")
        return ContextBundle(
            context_id=row["context_id"],
            cohort_id=row["cohort_id"],
            digest=row["context_digest"],
            evaluation_at=row["evaluation_at"],
            payload=json.loads(row["payload_json"]),
        )

    def get_context_bundle(self, context_digest: str) -> ContextBundle:
        row = self._conn.execute(
            """
            SELECT context_id, cohort_id, context_digest,
                   evaluation_at, payload_json
            FROM context_bundles WHERE context_digest = ?
            """,
            (context_digest,),
        ).fetchone()
        if row is None:
            raise KeyError(f"context not found: {context_digest}")
        return ContextBundle(
            context_id=str(row["context_id"]),
            cohort_id=str(row["cohort_id"]),
            digest=str(row["context_digest"]),
            evaluation_at=str(row["evaluation_at"]),
            payload=json.loads(row["payload_json"]),
        )

    def get_coverage_result(self, assessment_id: str) -> CoverageResult:
        row = self._conn.execute(
            """
            SELECT assessment_id, cohort_id, context_digest, status,
                   blockers_json, paper_blockers_json, live_blockers_json
            FROM coverage_assessments WHERE assessment_id = ?
            """,
            (assessment_id,),
        ).fetchone()
        if row is None:
            raise KeyError(f"coverage assessment not found: {assessment_id}")
        blockers = tuple(json.loads(row["blockers_json"])["items"])
        paper_blockers = tuple(json.loads(row["paper_blockers_json"])["items"])
        live_blockers = tuple(json.loads(row["live_blockers_json"])["items"])
        status = str(row["status"])
        paper_ready = status == "analyzable" and not paper_blockers
        return CoverageResult(
            assessment_id=str(row["assessment_id"]),
            cohort_id=str(row["cohort_id"]),
            context_digest=str(row["context_digest"]),
            status=status,
            blockers=blockers,
            paper_blockers=paper_blockers,
            live_blockers=live_blockers,
            paper_context_ready=paper_ready,
            live_context_ready=paper_ready and not live_blockers,
            paper_supported_position=0.0,
            live_supported_range=(0.0, 0.0),
            work_order_id=None,
        )

    def record_coverage_assessment(
        self,
        *,
        cohort_id: str,
        context_digest: str,
        status: str,
        blockers: tuple[str, ...],
        paper_blockers: tuple[str, ...],
        live_blockers: tuple[str, ...],
        catalyst: str,
        disproof: str,
        expiry: str,
        decision_relevance: int,
        falsifiability: int,
        information_value: int,
    ) -> dict[str, str | None]:
        if status not in {"coverage_pending", "analyzable"}:
            raise ValueError("invalid coverage status")
        for score in (decision_relevance, falsifiability, information_value):
            if isinstance(score, bool) or not isinstance(score, int) or not 0 <= score <= 10:
                raise ValueError("work-order scores must be integers from 0 to 10")
        assessment_payload = {
            "cohort_id": cohort_id,
            "context_digest": context_digest,
            "status": status,
            "blockers": blockers,
            "paper_blockers": paper_blockers,
            "live_blockers": live_blockers,
            "catalyst": catalyst,
            "disproof": disproof,
            "expiry": expiry,
        }
        assessment_id = "ca_" + _digest(_canonical_json(assessment_payload))[:32]
        work_order_id: str | None = None
        with immediate_transaction(self._conn):
            self._conn.execute(
                """
                INSERT OR IGNORE INTO coverage_assessments (
                    assessment_id, cohort_id, context_digest, status,
                    blockers_json, paper_blockers_json, live_blockers_json,
                    catalyst, disproof, expiry
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    assessment_id,
                    cohort_id,
                    context_digest,
                    status,
                    _canonical_json({"items": blockers}),
                    _canonical_json({"items": paper_blockers}),
                    _canonical_json({"items": live_blockers}),
                    catalyst,
                    disproof,
                    expiry,
                ),
            )
            self._conn.execute(
                """
                INSERT OR IGNORE INTO probe_projection (
                    cohort_id, status, evidence_admission_status,
                    source_registry_status, research_priority, coverage_status
                ) VALUES (?, 'active', 'unknown', 'candidate', 0, ?)
                """,
                (cohort_id, status),
            )
            self._conn.execute(
                """
                UPDATE probe_projection
                SET coverage_status = ?, updated_at = datetime('now')
                WHERE cohort_id = ?
                """,
                (status, cohort_id),
            )
            if status == "coverage_pending":
                work_order_id = "wo_" + _digest(assessment_id)[:32]
                self._conn.execute(
                    """
                    INSERT OR IGNORE INTO research_work_orders (
                        work_order_id, assessment_id, cohort_id, context_digest,
                        blockers_json, expiry, decision_relevance,
                        falsifiability, information_value
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        work_order_id,
                        assessment_id,
                        cohort_id,
                        context_digest,
                        _canonical_json({"items": blockers}),
                        expiry,
                        decision_relevance,
                        falsifiability,
                        information_value,
                    ),
                )
        return {"assessment_id": assessment_id, "work_order_id": work_order_id}

    def rank_work_orders(self, *, capacity: int = 5) -> dict[str, list[dict[str, Any]]]:
        if capacity < 0:
            raise ValueError("capacity must be non-negative")
        rows = [
            dict(row)
            for row in self._conn.execute(
                """
                SELECT work_order_id, cohort_id, context_digest, expiry,
                       decision_relevance, falsifiability, information_value,
                       status, created_at
                FROM research_work_orders
                WHERE status = 'queued'
                ORDER BY decision_relevance DESC,
                         falsifiability DESC,
                         expiry ASC,
                         information_value DESC,
                         created_at ASC,
                         work_order_id ASC
                """
            )
        ]
        return {"selected": rows[:capacity], "backlog": rows[capacity:]}

    def _paper_exposure(
        self,
        *,
        paper_nav: float,
        factor_resolver: Callable[[str], tuple[str, ...]],
    ) -> dict[str, Any]:
        rows = [
            dict(row)
            for row in self._conn.execute(
                "SELECT company_id, weight FROM paper_position_projection WHERE weight > 0"
            )
        ]
        company_weights = {str(row["company_id"]): float(row["weight"]) for row in rows}
        factor_weights: dict[str, float] = {}
        for company_id, weight in company_weights.items():
            for factor in factor_resolver(company_id):
                factor_weights[factor] = factor_weights.get(factor, 0.0) + weight
        return {
            "status": "available",
            "nav": paper_nav,
            "total_weight": sum(company_weights.values()),
            "company_weights": company_weights,
            "factor_weights": factor_weights,
            "blockers": [],
        }

    @staticmethod
    def _execution_result_from_payload(
        decision_id: str,
        decision_digest: str,
        payload: Mapping[str, Any],
        paper_event_id: str | None,
    ) -> DecisionExecutionResult:
        sizing = payload["sizing"]
        return DecisionExecutionResult(
            decision_id=decision_id,
            decision_digest=decision_digest,
            paper_event_id=paper_event_id,
            paper_funded=paper_event_id is not None,
            paper_target=float(sizing["paper_target"]),
            paper_max_supported_position=float(
                sizing["paper_max_supported_position"]
            ),
            action=str(sizing["action"]),
        )

    def atomic_assess_probe(
        self,
        *,
        cohort_id: str,
        context_digest: str,
        coverage_assessment_id: str,
        idempotency_key: str,
        effective_at: str,
        request_payload: Mapping[str, Any],
        paper_nav: float,
        company_id: str,
        factor_resolver: Callable[[str], tuple[str, ...]],
        calculator: Callable[[Mapping[str, Any]], ProbeSizingResult],
        failure_at: str | None = None,
    ) -> DecisionExecutionResult:
        """Recompute paper capacity and commit decision/event in one transaction。"""

        if not idempotency_key.strip():
            raise ValueError("idempotency_key is required")
        _time(effective_at, "effective_at")
        request_json = _canonical_json(request_payload)
        request_digest = _digest(request_json)
        decision_id = "pd_" + _digest(idempotency_key)[:32]
        with immediate_transaction(self._conn):
            existing = self._conn.execute(
                """
                SELECT decision_id, request_digest, decision_digest, payload_json
                FROM system_decisions WHERE idempotency_key = ?
                """,
                (idempotency_key,),
            ).fetchone()
            if existing is not None:
                if existing["request_digest"] != request_digest:
                    raise ValueError("idempotency key already belongs to a different request digest")
                event = self._conn.execute(
                    "SELECT paper_event_id FROM paper_events WHERE decision_id = ?",
                    (existing["decision_id"],),
                ).fetchone()
                return self._execution_result_from_payload(
                    str(existing["decision_id"]),
                    str(existing["decision_digest"]),
                    json.loads(existing["payload_json"]),
                    str(event["paper_event_id"]) if event is not None else None,
                )

            exposure = self._paper_exposure(
                paper_nav=paper_nav,
                factor_resolver=factor_resolver,
            )
            if failure_at == "after_capacity":
                raise RuntimeError("injected failure after capacity")
            sizing = calculator(exposure)
            decision_payload = {
                "request": request_payload,
                "paper_capacity_snapshot": exposure,
                "sizing": asdict(sizing),
            }
            decision_json = _canonical_json(decision_payload)
            decision_digest = _digest(decision_json)
            self._conn.execute(
                """
                INSERT INTO system_decisions (
                    decision_id, cohort_id, idempotency_key, request_digest,
                    decision_digest, context_digest, coverage_assessment_id,
                    policy_version, calculator_version, payload_json, effective_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    decision_id,
                    cohort_id,
                    idempotency_key,
                    request_digest,
                    decision_digest,
                    context_digest,
                    coverage_assessment_id,
                    sizing.policy_version,
                    sizing.calculator_version,
                    decision_json,
                    effective_at,
                ),
            )
            if failure_at == "after_decision":
                raise RuntimeError("injected failure after decision")

            current = float(exposure["company_weights"].get(company_id, 0.0))
            target = float(sizing.paper_target)
            paper_event_id: str | None = None
            if sizing.paper_status == "ELIGIBLE" and not math.isclose(
                current, target, abs_tol=1e-12
            ):
                event_payload = {
                    "company_id": company_id,
                    "decision_id": decision_id,
                    "decision_digest": decision_digest,
                    "context_digest": context_digest,
                    "policy_version": sizing.policy_version,
                    "calculator_version": sizing.calculator_version,
                    "target_weight": target,
                    "previous_weight": current,
                    "changed_weight": target - current,
                    "constraint_trace": sizing.constraint_trace,
                }
                event_json = _canonical_json(event_payload)
                event_digest = _digest(event_json)
                paper_event_id = "pe_" + _digest(f"{decision_id}:{event_digest}")[:32]
                self._conn.execute(
                    """
                    INSERT INTO paper_events (
                        paper_event_id, cohort_id, decision_id, event_type,
                        payload_json, payload_digest, effective_at
                    ) VALUES (?, ?, ?, 'target_update', ?, ?, ?)
                    """,
                    (
                        paper_event_id,
                        cohort_id,
                        decision_id,
                        event_json,
                        event_digest,
                        effective_at,
                    ),
                )
                if failure_at == "after_paper_event":
                    raise RuntimeError("injected failure after paper event")
                self._conn.execute(
                    """
                    INSERT INTO paper_position_projection (
                        company_id, weight, source_event_id
                    ) VALUES (?, ?, ?)
                    ON CONFLICT(company_id) DO UPDATE SET
                        weight = excluded.weight,
                        source_event_id = excluded.source_event_id,
                        updated_at = datetime('now')
                    """,
                    (company_id, target, paper_event_id),
                )
                if failure_at == "after_projection":
                    raise RuntimeError("injected failure after projection")
            return self._execution_result_from_payload(
                decision_id,
                decision_digest,
                decision_payload,
                paper_event_id,
            )

    def paper_position(self, company_id: str) -> float:
        row = self._conn.execute(
            "SELECT weight FROM paper_position_projection WHERE company_id = ?",
            (company_id,),
        ).fetchone()
        return float(row["weight"]) if row is not None else 0.0

    def get_decision(self, decision_id: str) -> dict[str, Any]:
        row = self._conn.execute(
            """
            SELECT decision_id, cohort_id, decision_digest, request_digest,
                   context_digest, policy_version, calculator_version,
                   payload_json, effective_at
            FROM system_decisions WHERE decision_id = ?
            """,
            (decision_id,),
        ).fetchone()
        if row is None:
            raise KeyError(f"decision not found: {decision_id}")
        result = dict(row)
        result["payload"] = json.loads(result.pop("payload_json"))
        return result

    def paper_event_for_decision(self, decision_id: str) -> dict[str, Any] | None:
        row = self._conn.execute(
            """
            SELECT paper_event_id, event_type, payload_json, effective_at
            FROM paper_events WHERE decision_id = ?
            ORDER BY effective_at, paper_event_id LIMIT 1
            """,
            (decision_id,),
        ).fetchone()
        if row is None:
            return None
        result = dict(row)
        result["payload"] = json.loads(result.pop("payload_json"))
        return result

    def list_paper_events(self, cohort_id: str) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            """
            SELECT paper_event_id, cohort_id, decision_id, event_type,
                   payload_json, payload_digest, effective_at,
                   corrects_paper_event_id, approved_action_id
            FROM paper_events WHERE cohort_id = ?
            ORDER BY effective_at, paper_event_id
            """,
            (cohort_id,),
        )
        result = []
        for row in rows:
            item = dict(row)
            item["payload"] = json.loads(item.pop("payload_json"))
            result.append(item)
        return result

    def record_live_choice(
        self,
        *,
        decision_id: str,
        selected_weight: float,
        decided_at: str,
        reason: str | None = None,
        approved_action_id: str | None = None,
        force_override: bool = False,
    ) -> str:
        _time(decided_at, "decided_at")
        if not math.isfinite(selected_weight) or selected_weight < 0:
            raise ValueError("selected_weight must be finite and non-negative")
        with immediate_transaction(self._conn):
            decision = self._conn.execute(
                "SELECT payload_json FROM system_decisions WHERE decision_id = ?",
                (decision_id,),
            ).fetchone()
            if decision is None:
                raise KeyError(f"decision not found: {decision_id}")
            payload = json.loads(decision["payload_json"])
            lower, upper = payload["sizing"]["live_supported_range"]
            if selected_weight > float(upper) + 1e-12 and not force_override:
                raise ValueError("selected live weight exceeds supported cap")
            if force_override and (not reason or not reason.strip() or not approved_action_id):
                raise ValueError("live override requires reason and approved action")
            choice_type = (
                "override"
                if force_override
                else "skipped"
                if selected_weight == 0
                else "below_range"
                if selected_weight < float(lower)
                else "accepted"
            )
            choice_id = "lc_" + _digest(
                _canonical_json(
                    {
                        "decision_id": decision_id,
                        "selected_weight": selected_weight,
                        "decided_at": decided_at,
                        "approved_action_id": approved_action_id,
                    }
                )
            )[:32]
            self._conn.execute(
                """
                INSERT OR IGNORE INTO live_choices (
                    choice_id, decision_id, selected_weight, choice_type,
                    reason, approved_action_id, decided_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    choice_id,
                    decision_id,
                    selected_weight,
                    choice_type,
                    reason,
                    approved_action_id,
                    decided_at,
                ),
            )
            return choice_id

    def record_live_fill(
        self,
        *,
        decision_id: str,
        execution_ref: str,
        shares: float,
        price: float,
        currency: str,
        executed_at: str,
    ) -> str:
        _time(executed_at, "executed_at")
        if (
            not execution_ref.strip()
            or not math.isfinite(shares)
            or not math.isfinite(price)
            or price <= 0
            or len(currency) != 3
            or not currency.isupper()
        ):
            raise ValueError("invalid live fill")
        fill_id = "lf_" + _digest(execution_ref)[:32]
        with immediate_transaction(self._conn):
            choice = self._conn.execute(
                "SELECT 1 FROM live_choices WHERE decision_id = ? LIMIT 1",
                (decision_id,),
            ).fetchone()
            if choice is None:
                raise ValueError("live fill requires an explicit live choice")
            self._conn.execute(
                """
                INSERT OR IGNORE INTO live_execution_reports (
                    fill_id, decision_id, execution_ref, shares,
                    price, currency, executed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (fill_id, decision_id, execution_ref, shares, price, currency, executed_at),
            )
        return fill_id

    def latest_live_choice(self, decision_id: str) -> dict[str, Any] | None:
        row = self._conn.execute(
            """
            SELECT choice_id, selected_weight, choice_type, reason,
                   approved_action_id, decided_at
            FROM live_choices WHERE decision_id = ?
            ORDER BY decided_at DESC, choice_id DESC LIMIT 1
            """,
            (decision_id,),
        ).fetchone()
        return dict(row) if row is not None else None

    def latest_live_fill(self, decision_id: str) -> dict[str, Any] | None:
        row = self._conn.execute(
            """
            SELECT fill_id, execution_ref, shares, price, currency, executed_at
            FROM live_execution_reports WHERE decision_id = ?
            ORDER BY executed_at DESC, fill_id DESC LIMIT 1
            """,
            (decision_id,),
        ).fetchone()
        return dict(row) if row is not None else None

    def prepare_action(
        self,
        *,
        action_type: str,
        target_id: str,
        payload: Mapping[str, Any],
        prepared_at: str,
        expires_at: str,
    ) -> PreparedAction:
        if action_type not in {"live_override", "paper_correction", "paper_reversal"}:
            raise ValueError("unsupported managed action")
        if not target_id.strip() or _time(expires_at, "expires_at") <= _time(
            prepared_at, "prepared_at"
        ):
            raise ValueError("managed action requires target and future expiry")
        payload_json = _canonical_json(payload)
        digest = _digest(
            _canonical_json(
                {
                    "action_type": action_type,
                    "target_id": target_id,
                    "payload": payload,
                    "prepared_at": prepared_at,
                    "expires_at": expires_at,
                }
            )
        )
        action_id = "pa_" + digest[:32]
        with immediate_transaction(self._conn):
            self._conn.execute(
                """
                INSERT OR IGNORE INTO prepared_actions (
                    action_id, action_type, target_id, payload_json,
                    action_digest, prepared_at, expires_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    action_id,
                    action_type,
                    target_id,
                    payload_json,
                    digest,
                    prepared_at,
                    expires_at,
                ),
            )
        return PreparedAction(action_id, action_type, target_id, digest, expires_at)

    def _prepared(self, action_id: str, digest: str) -> sqlite3.Row:
        row = self._conn.execute(
            "SELECT * FROM prepared_actions WHERE action_id = ?",
            (action_id,),
        ).fetchone()
        if row is None:
            raise KeyError(f"prepared action not found: {action_id}")
        if row["action_digest"] != digest:
            raise ValueError("prepared action digest mismatch")
        return row

    def apply_live_override(
        self, *, action_id: str, digest: str, decided_at: str
    ) -> str:
        with immediate_transaction(self._conn):
            action = self._prepared(action_id, digest)
            if action["action_type"] != "live_override":
                raise ValueError("prepared action is not a live override")
            if _time(decided_at, "decided_at") > _time(action["expires_at"], "expires_at"):
                raise ValueError("prepared action expired")
            existing = self._conn.execute(
                "SELECT choice_id FROM live_choices WHERE approved_action_id = ?",
                (action_id,),
            ).fetchone()
            if action["status"] == "applied":
                if existing is None:
                    raise ValueError("applied action is missing its live choice")
                return str(existing["choice_id"])
            payload = json.loads(action["payload_json"])
            selected = float(payload.get("selected_weight"))
            reason = str(payload.get("reason") or "").strip()
            if not math.isfinite(selected) or selected < 0:
                raise ValueError("live override selected weight is invalid")
            if not reason:
                raise ValueError("live override reason is required")
            # Inline the insert so action state and choice commit together.
            decision = self._conn.execute(
                "SELECT 1 FROM system_decisions WHERE decision_id = ?",
                (action["target_id"],),
            ).fetchone()
            if decision is None:
                raise KeyError("override target decision not found")
            choice_id = "lc_" + _digest(f"{action_id}:{decided_at}")[:32]
            self._conn.execute(
                """
                INSERT INTO live_choices (
                    choice_id, decision_id, selected_weight, choice_type,
                    reason, approved_action_id, decided_at
                ) VALUES (?, ?, ?, 'override', ?, ?, ?)
                """,
                (choice_id, action["target_id"], selected, reason, action_id, decided_at),
            )
            self._conn.execute(
                "UPDATE prepared_actions SET status = 'applied', applied_at = ? WHERE action_id = ?",
                (decided_at, action_id),
            )
            return choice_id

    def apply_paper_amendment(
        self, *, action_id: str, digest: str, effective_at: str
    ) -> str:
        with immediate_transaction(self._conn):
            action = self._prepared(action_id, digest)
            if action["action_type"] not in {"paper_correction", "paper_reversal"}:
                raise ValueError("prepared action is not a paper amendment")
            if _time(effective_at, "effective_at") > _time(action["expires_at"], "expires_at"):
                raise ValueError("prepared action expired")
            existing = self._conn.execute(
                "SELECT paper_event_id FROM paper_events WHERE approved_action_id = ?",
                (action_id,),
            ).fetchone()
            if action["status"] == "applied":
                if existing is None:
                    raise ValueError("applied action is missing its paper event")
                return str(existing["paper_event_id"])
            original = self._conn.execute(
                """
                SELECT paper_event_id, cohort_id, decision_id, payload_json
                FROM paper_events WHERE paper_event_id = ?
                """,
                (action["target_id"],),
            ).fetchone()
            if original is None:
                raise KeyError("paper amendment target not found")
            original_payload = json.loads(original["payload_json"])
            request = json.loads(action["payload_json"])
            target = 0.0 if action["action_type"] == "paper_reversal" else float(
                request.get("target_weight")
            )
            if not math.isfinite(target) or target < 0:
                raise ValueError("paper amendment target must be non-negative")
            if original["decision_id"]:
                decision = self._conn.execute(
                    "SELECT payload_json FROM system_decisions WHERE decision_id = ?",
                    (original["decision_id"],),
                ).fetchone()
                if decision is None:
                    raise ValueError("paper amendment decision reference is missing")
                maximum = float(
                    json.loads(decision["payload_json"])["sizing"][
                        "paper_max_supported_position"
                    ]
                )
                if target > maximum + 1e-12:
                    raise ValueError("paper amendment exceeds original supported cap")
            company_id = str(original_payload["company_id"])
            current = self.paper_position(company_id)
            event_payload = {
                "company_id": company_id,
                "target_weight": target,
                "previous_weight": current,
                "changed_weight": target - current,
                "reason": request.get("reason"),
                "corrects_paper_event_id": original["paper_event_id"],
                "approved_action_id": action_id,
            }
            event_json = _canonical_json(event_payload)
            event_digest = _digest(event_json)
            event_id = "pe_" + _digest(f"{action_id}:{event_digest}")[:32]
            self._conn.execute(
                """
                INSERT INTO paper_events (
                    paper_event_id, cohort_id, decision_id, event_type,
                    payload_json, payload_digest, effective_at,
                    corrects_paper_event_id, approved_action_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event_id,
                    original["cohort_id"],
                    original["decision_id"],
                    action["action_type"],
                    event_json,
                    event_digest,
                    effective_at,
                    original["paper_event_id"],
                    action_id,
                ),
            )
            self._conn.execute(
                """
                INSERT INTO paper_position_projection (company_id, weight, source_event_id)
                VALUES (?, ?, ?)
                ON CONFLICT(company_id) DO UPDATE SET
                    weight = excluded.weight,
                    source_event_id = excluded.source_event_id,
                    updated_at = datetime('now')
                """,
                (company_id, target, event_id),
            )
            self._conn.execute(
                "UPDATE prepared_actions SET status = 'applied', applied_at = ? WHERE action_id = ?",
                (effective_at, action_id),
            )
            return event_id
