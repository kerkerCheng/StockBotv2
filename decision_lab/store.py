"""Decision Cohort 與 paper events 的 private transactional store。"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from storage.relational import (
    connect_sqlite,
    immediate_transaction,
    validate_private_destination,
)

from .models import ContextBundle, ProbeRecord, ShadowBaseline


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
