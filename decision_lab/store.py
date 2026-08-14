"""Decision Cohort 與 paper events 的 private transactional store。"""
from __future__ import annotations

import hashlib
import json
import math
import os
import sqlite3
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping

from identity.currency import is_settlement_currency
from identity.registry import get_registry

from .blocker_severity import fatal_blockers
from storage.relational import (
    connect_sqlite,
    immediate_transaction,
    validate_private_destination,
)

from .models import (
    ContextBundle,
    CoverageResult,
    DecisionExecutionResult,
    LifecycleResult,
    OutcomeResult,
    PreparedAction,
    ProbeRecord,
    ProbeSizingResult,
    ShadowBaseline,
)
from .redaction import sensitive_payload_path


_SCHEMA_PATH = Path(__file__).with_name("schema.sql")
_SCHEMA_VERSION = "7"


def _canonical_json(payload: Mapping[str, Any]) -> str:
    sensitive = sensitive_payload_path(payload)
    if sensitive is not None:
        raise ValueError(f"secret-bearing payload rejected at {sensitive}")
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
    return parsed.astimezone(timezone.utc)


def _timestamp(value: str, field: str) -> str:
    return _time(value, field).isoformat()


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
        private = private_root.resolve()
        marker = validate_private_destination(
            private / "decision_lab_authority.json",
            private_root=private,
            repo_root=repo_root,
        )
        marker_exists = marker.is_file()
        if marker_exists and not resolved.is_file():
            raise RuntimeError(
                "Decision Store authority is missing; restore the database before opening"
            )
        is_new = not resolved.exists()
        conn = connect_sqlite(resolved, create=is_new)
        try:
            if is_new:
                conn.executescript(_SCHEMA_PATH.read_text(encoding="utf-8"))
                conn.commit()
            integrity = conn.execute("PRAGMA integrity_check").fetchone()
            version_row = conn.execute(
                "SELECT value FROM decision_store_meta WHERE key = 'schema_version'"
            ).fetchone()
            if integrity is None or str(integrity[0]) != "ok" or version_row is None:
                raise RuntimeError("Decision Store authority is invalid")
            if str(version_row["value"]) != _SCHEMA_VERSION:
                raise RuntimeError(
                    "Decision Store schema version mismatch; use an explicit migration or empty bootstrap"
                )
            if not marker_exists:
                marker.parent.mkdir(parents=True, exist_ok=True)
                marker_temp = marker.with_suffix(".tmp")
                marker_temp.write_text(
                    _canonical_json(
                        {
                            "schema": "decision-store-authority-v1",
                            "database": resolved.relative_to(private).as_posix(),
                            "schema_version": _SCHEMA_VERSION,
                        }
                    )
                    + "\n",
                    encoding="utf-8",
                )
                os.replace(marker_temp, marker)
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

    def bind_cohort_identity(
        self,
        cohort_id: str,
        *,
        company_id: str,
        research_ticker: str,
        resolved_at: str,
    ) -> CohortRecord:
        """Monotonically bind one unresolved cohort to a registry identity pair。"""

        resolved_at = _timestamp(resolved_at, "resolved_at")
        registry = get_registry()
        company = registry.company(company_id)
        canonical_ticker = research_ticker.strip().upper()
        if company is None or company.research_ticker != canonical_ticker:
            raise ValueError("cohort identity pair is not canonical in the registry")
        payload = {
            "company_id": company_id,
            "research_ticker": canonical_ticker,
            "identity_registry_version": registry.version,
        }
        payload_json = _canonical_json(payload)
        payload_digest = _digest(payload_json)
        event_id = "de_" + _digest(
            _canonical_json(
                {
                    "cohort_id": cohort_id,
                    "event_type": "identity_resolved",
                    "payload_digest": payload_digest,
                    "observed_at": resolved_at,
                }
            )
        )[:32]
        with immediate_transaction(self._conn):
            row = self._conn.execute(
                """
                SELECT cohort_id, dedupe_key, company_id, research_ticker
                FROM decision_cohorts WHERE cohort_id = ?
                """,
                (cohort_id,),
            ).fetchone()
            if row is None:
                raise KeyError(f"cohort not found: {cohort_id}")
            current_pair = (row["company_id"], row["research_ticker"])
            requested_pair = (company_id, canonical_ticker)
            if current_pair == requested_pair:
                return CohortRecord(**dict(row))
            if current_pair != (None, None):
                raise ValueError("cohort identity remap is forbidden")
            self._conn.execute(
                """
                UPDATE decision_cohorts
                SET company_id = ?, research_ticker = ?
                WHERE cohort_id = ? AND company_id IS NULL AND research_ticker IS NULL
                """,
                (company_id, canonical_ticker, cohort_id),
            )
            self._conn.execute(
                """
                INSERT INTO decision_events (
                    event_id, cohort_id, event_type, payload_json,
                    payload_digest, observed_at
                ) VALUES (?, ?, 'identity_resolved', ?, ?, ?)
                """,
                (event_id, cohort_id, payload_json, payload_digest, resolved_at),
            )
            updated = self._conn.execute(
                """
                SELECT cohort_id, dedupe_key, company_id, research_ticker
                FROM decision_cohorts WHERE cohort_id = ?
                """,
                (cohort_id,),
            ).fetchone()
        assert updated is not None
        return CohortRecord(**dict(updated))

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
        observed_at = _timestamp(observed_at, "observed_at")
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
        company_id: str | None,
        research_ticker: str | None,
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
        observed_at = _timestamp(observed_at, "observed_at")
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
            "ticker": shadow.get("ticker"),
            "price": shadow.get("price"),
            "currency": shadow.get("currency"),
            "source": shadow.get("source"),
            "as_of": shadow.get("as_of"),
            "fetched_at": shadow.get("fetched_at"),
        }
        if shadow_payload["status"] == "observed":
            shadow_payload["as_of"] = _timestamp(
                str(shadow_payload["as_of"]), "shadow.as_of"
            )
            shadow_payload["fetched_at"] = _timestamp(
                str(shadow_payload["fetched_at"]), "shadow.fetched_at"
            )
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
                    shadow_id, cohort_id, status, ticker, price, currency,
                    source, as_of, fetched_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    shadow_id,
                    cohort_id,
                    shadow_payload["status"],
                    shadow_payload["ticker"],
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
                   ticker, source, as_of, fetched_at
            FROM shadow_observations WHERE cohort_id = ?
            """,
            (cohort_id,),
        ).fetchone()
        if row is None:
            raise KeyError(f"shadow not found for {cohort_id}")
        return ShadowBaseline(**dict(row))

    def backfill_shadow(
        self,
        cohort_id: str,
        snapshot: Mapping[str, Any],
        *,
        inception_at: str,
        backfilled_at: str,
        reason: str,
    ) -> ShadowBaseline:
        """把遺失的 Shadow 錨點以重建值補上；已觀測到的錨點永不覆寫。

        Shadow 記的是某個已知時刻的最後一個完整交易日收盤價——那是**可重建的
        事實**，不是只有當下才有的真相。因此一次瞬時故障造成的空錨點應該可以
        修復，而不是永久遺失（實測：9 個 cohort 有 7 個沒有價格，其中包含 §1 的
        co:axt）。

        兩道限制不得放寬：

        1. ``status == 'observed'`` 的錨點是已記錄的觀測，覆寫等於改寫歷史，
           一律拒絕。
        2. **回填值的 ``as_of`` 必須早於 inception 時刻。** 這是 hindsight 防線：
           用 inception 之後的價格補錨點會把基準點偷偷往有利方向移動，
           使「從知道這件事開始漲了多少」變成一個可被事後挑選的數字。
           ``tests/test_shadow_baseline.py`` 已鎖住 intake 路徑不做事後回填；
           這裡是明確、有稽核軌跡的修復路徑，同一條紀律必須成立。

        每次回填都留下 append-only ``shadow_backfilled`` 事件，來源標 ``backfill://``
        以便與真正的即時觀測區分——它是**可辯護的重建，不是重播**。
        """

        existing = self.get_shadow(cohort_id)
        if existing.status == "observed":
            raise ValueError(f"shadow already observed for {cohort_id}; refusing to overwrite")
        if str(snapshot.get("status")) != "observed":
            raise ValueError("backfill snapshot must be an observed market snapshot")
        for field in ("ticker", "price", "currency", "source", "as_of", "fetched_at"):
            if snapshot.get(field) in (None, ""):
                raise ValueError(f"backfill snapshot is missing {field}")
        inception = _timestamp(inception_at, "inception_at")
        as_of = _timestamp(str(snapshot["as_of"]), "snapshot.as_of")
        if datetime.fromisoformat(as_of) >= datetime.fromisoformat(inception):
            raise ValueError(
                "backfill snapshot must predate shadow inception; refusing hindsight anchor"
            )
        stamp = _timestamp(backfilled_at, "backfilled_at")
        with immediate_transaction(self._conn):
            self._conn.execute(
                """
                UPDATE shadow_observations
                SET status = ?, ticker = ?, price = ?, currency = ?,
                    source = ?, as_of = ?, fetched_at = ?
                WHERE cohort_id = ? AND status != 'observed'
                """,
                (
                    "observed",
                    str(snapshot["ticker"]),
                    float(snapshot["price"]),
                    str(snapshot["currency"]),
                    str(snapshot["source"]),
                    str(snapshot["as_of"]),
                    str(snapshot["fetched_at"]),
                    cohort_id,
                ),
            )
        self.append_event(
            cohort_id=cohort_id,
            event_type="shadow_backfilled",
            payload={
                "previous_status": existing.status,
                "reason": reason,
                "inception_at": inception,
                "price": float(snapshot["price"]),
                "currency": str(snapshot["currency"]),
                "as_of": str(snapshot["as_of"]),
                "source": str(snapshot["source"]),
            },
            observed_at=stamp,
        )
        return self.get_shadow(cohort_id)

    def count_shadows(self, cohort_id: str) -> int:
        row = self._conn.execute(
            "SELECT COUNT(*) AS count FROM shadow_observations WHERE cohort_id = ?",
            (cohort_id,),
        ).fetchone()
        return int(row["count"])

    def capital_expression_counters(self) -> dict[str, int]:
        """兩個常駐計數器：系統至今**輸出過**多少資本，以及**驗證過**多少判斷。

        它們存在的理由不是報表好看，是為了讓「開發迴圈有沒有進展」每天自己出現在
        使用者眼前。2026-08-13 的 audit 發現同一個診斷被正確寫下四次卻從未改到
        binding constraint，成因是判準住在要人主動想起來去讀的文件裡（D16：入口是
        使用者的一次動作，出口不該也要求使用者記得）。只要這兩個數字還是 0，
        每天的 brief 都會說出來。

        - ``live_range_nonzero``：歷來 ``live_supported_range`` 上界 > 0 的 decision 數。
          0 代表系統從未對任何標的說出「可以入場」——不論研究做得多好。
        - ``measured_outcomes``：``outcome_envelopes`` 中 ``absolute_return`` 非 null 的
          筆數。0 代表「系統的判斷準不準」永遠無法用證據回答。
        """

        decisions = 0
        live_nonzero = 0
        for row in self._conn.execute("SELECT payload_json FROM system_decisions"):
            decisions += 1
            try:
                sizing = json.loads(row["payload_json"]).get("sizing") or {}
                upper = (sizing.get("live_supported_range") or (0, 0))[1]
            except (ValueError, TypeError, IndexError, KeyError):
                continue
            if isinstance(upper, (int, float)) and not isinstance(upper, bool) and upper > 0:
                live_nonzero += 1
        outcomes = self._conn.execute(
            "SELECT COUNT(*) AS total,"
            " SUM(CASE WHEN absolute_return IS NOT NULL THEN 1 ELSE 0 END) AS measured"
            " FROM outcome_envelopes"
        ).fetchone()
        return {
            "decisions": decisions,
            "live_range_nonzero": live_nonzero,
            "outcomes": int(outcomes["total"] or 0),
            "measured_outcomes": int(outcomes["measured"] or 0),
        }

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

    def cohort_identity(self, cohort_id: str) -> dict[str, str | None]:
        row = self._conn.execute(
            """
            SELECT company_id, research_ticker
            FROM decision_cohorts WHERE cohort_id = ?
            """,
            (cohort_id,),
        ).fetchone()
        if row is None:
            raise KeyError(f"cohort not found: {cohort_id}")
        return {
            "company_id": row["company_id"],
            "research_ticker": row["research_ticker"],
        }

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
        confirmed_at = _timestamp(confirmed_at, "confirmed_at")
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
        evaluation_at = _timestamp(evaluation_at, "evaluation_at")
        payload_json = _canonical_json(payload)
        if _digest(payload_json) != digest:
            raise ValueError("context digest mismatch")
        context_id = "ctx_" + digest[:32]
        with immediate_transaction(self._conn):
            cohort = self._conn.execute(
                """
                SELECT company_id, research_ticker
                FROM decision_cohorts WHERE cohort_id = ?
                """,
                (cohort_id,),
            ).fetchone()
            identity = payload.get("identity")
            if (
                cohort is None
                or payload.get("cohort_id") != cohort_id
                or not isinstance(identity, Mapping)
                or identity.get("company_id") != cohort["company_id"]
                or identity.get("research_ticker") != cohort["research_ticker"]
            ):
                raise ValueError("context identity does not match cohort authority")
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
            SELECT ca.assessment_id, ca.cohort_id, ca.context_digest, ca.status,
                   ca.blockers_json, ca.paper_blockers_json, ca.live_blockers_json,
                   wo.work_order_id
            FROM coverage_assessments ca
            LEFT JOIN research_work_orders wo ON wo.assessment_id = ca.assessment_id
            WHERE ca.assessment_id = ?
            """,
            (assessment_id,),
        ).fetchone()
        if row is None:
            raise KeyError(f"coverage assessment not found: {assessment_id}")
        blockers = tuple(json.loads(row["blockers_json"])["items"])
        paper_blockers = tuple(json.loads(row["paper_blockers_json"])["items"])
        live_blockers = tuple(json.loads(row["live_blockers_json"])["items"])
        status = str(row["status"])
        # lane readiness 看的是「有沒有致命缺口」，不是 status 這個二元標籤。
        # status 的 analyzable ⟺ 零 blocker 是持久化 invariant（見
        # record_coverage_assessment），不能為了放行研究不完整的案例而鬆動；
        # 但拿它當 readiness 判準，等於讓任何一個非致命 blocker 也把 lane 打成
        # not_ready，於是 2026-08-02 對 coverage_cap 做的嚴重度分類在下游被抵銷。
        # lane blocker 也走同一套嚴重度分類（2026-08-13）：先前 `not paper_blockers`
        # ／`not live_blockers` 讓任一非致命 lane blocker 也把 lane 打成 not_ready，
        # 於是 diagnostic 級的 execution_intent_* 與 holdings_unconfirmed 擋掉 live 71/72 次。
        fatal = fatal_blockers(blockers)
        paper_ready = not fatal and not fatal_blockers(paper_blockers, lane="paper")
        live_ready = not fatal and not fatal_blockers(live_blockers, lane="live")
        return CoverageResult(
            assessment_id=str(row["assessment_id"]),
            cohort_id=str(row["cohort_id"]),
            context_digest=str(row["context_digest"]),
            status=status,
            blockers=blockers,
            paper_blockers=paper_blockers,
            live_blockers=live_blockers,
            paper_context_ready=paper_ready,
            live_context_ready=live_ready,
            paper_supported_position=0.0,
            live_supported_range=(0.0, 0.0),
            work_order_id=row["work_order_id"],
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
        expiry = _timestamp(expiry, "expiry")
        context = self._conn.execute(
            """
            SELECT cohort_id, evaluation_at
            FROM context_bundles WHERE context_digest = ?
            """,
            (context_digest,),
        ).fetchone()
        if context is None or context["cohort_id"] != cohort_id:
            raise ValueError("coverage context does not match cohort authority")
        if _time(expiry, "expiry") <= _time(
            str(context["evaluation_at"]), "context.evaluation_at"
        ):
            raise ValueError("coverage expiry must follow context evaluation")
        if status == "analyzable" and (
            not catalyst.strip() or not disproof.strip()
        ):
            raise ValueError("analyzable coverage requires catalyst and disproof")
        if status == "analyzable" and blockers:
            raise ValueError("analyzable coverage cannot contain core blockers")
        if status == "coverage_pending" and not blockers:
            raise ValueError("coverage_pending requires core blockers")
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
                        falsifiability, information_value, status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'proposed')
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

    def get_research_work_order(self, work_order_id: str) -> dict[str, Any]:
        row = self._conn.execute(
            """
            SELECT work_order_id, assessment_id, cohort_id, context_digest,
                   blockers_json, expiry, decision_relevance, falsifiability,
                   information_value, status, created_at
            FROM research_work_orders WHERE work_order_id = ?
            """,
            (work_order_id,),
        ).fetchone()
        if row is None:
            raise KeyError(f"research work order not found: {work_order_id}")
        result = dict(row)
        result["blockers"] = list(json.loads(result.pop("blockers_json"))["items"])
        return result

    def latest_research_work_order(self, cohort_id: str) -> dict[str, Any] | None:
        """Return the work order bound to the cohort's latest immutable decision."""

        row = self._conn.execute(
            """
            SELECT wo.work_order_id, sd.decision_id
            FROM system_decisions sd
            JOIN research_work_orders wo
              ON wo.assessment_id = sd.coverage_assessment_id
            WHERE sd.cohort_id = ?
            ORDER BY sd.effective_at DESC, sd.decision_id DESC
            LIMIT 1
            """,
            (cohort_id,),
        ).fetchone()
        if row is None:
            return None
        result = self.get_research_work_order(str(row["work_order_id"]))
        result["decision_id"] = str(row["decision_id"])
        return result

    def transition_research_work_order(
        self,
        *,
        work_order_id: str,
        to_status: str,
        operation_key: str,
        receipt: Mapping[str, Any],
        observed_at: str,
    ) -> dict[str, Any]:
        """Checkpoint one bounded research job and append its audit receipt atomically."""

        transitions = {
            "proposed": {"queued", "parked"},
            "queued": {"researching", "parked"},
            "researching": {"queued", "awaiting_approval", "completed", "parked"},
            "awaiting_approval": {"researching", "completed", "parked"},
            "completed": set(),
            "parked": set(),
        }
        if to_status not in transitions:
            raise ValueError(f"invalid research work order status: {to_status}")
        if not operation_key.strip():
            raise ValueError("operation_key is required")
        observed_at = _timestamp(observed_at, "observed_at")
        event_type = f"research_work_order_{to_status}"
        payload = {
            "work_order_id": work_order_id,
            "to_status": to_status,
            "operation_key": operation_key,
            "receipt": dict(receipt),
        }
        payload_json = _canonical_json(payload)
        payload_digest = _digest(payload_json)
        with immediate_transaction(self._conn):
            row = self._conn.execute(
                "SELECT cohort_id, status FROM research_work_orders WHERE work_order_id = ?",
                (work_order_id,),
            ).fetchone()
            if row is None:
                raise KeyError(f"research work order not found: {work_order_id}")
            cohort_id = str(row["cohort_id"])
            current = str(row["status"])

            for event in self._conn.execute(
                """
                SELECT payload_json FROM decision_events
                WHERE cohort_id = ? AND event_type = ?
                """,
                (cohort_id, event_type),
            ):
                stored = json.loads(event["payload_json"])
                if stored.get("operation_key") == operation_key:
                    if stored != payload or current != to_status:
                        raise ValueError("research work order operation key was reused")
                    return self.get_research_work_order(work_order_id)

            # Legacy v1.2 rows were born as queued.  A first explicit pq2 dispatch may
            # therefore audit queued -> queued; all other same-state transitions fail.
            legacy_dispatch = current == to_status == "queued"
            # 已完成／parked 的 bounded job receipt 仍保留在 append-only events；若
            # 同一 pq2 decision gap 再次收到 exact user go，允許明確重啟同一 work
            # order。這不是一般狀態回退：receipt 必須聲明並吻合 terminal prior
            # status，且帶穩定 todo 編號，否則仍 fail closed。
            terminal_redispatch = (
                current in {"completed", "parked"}
                and to_status == "queued"
                and receipt.get("prior_work_order_status") == current
                and isinstance(receipt.get("todo_n"), int)
            )
            if (
                not legacy_dispatch
                and not terminal_redispatch
                and to_status not in transitions.get(current, set())
            ):
                raise ValueError(
                    f"illegal research work order transition: {current} -> {to_status}"
                )
            self._conn.execute(
                "UPDATE research_work_orders SET status = ? WHERE work_order_id = ?",
                (to_status, work_order_id),
            )
            event_id = "de_" + _digest(_canonical_json({
                "cohort_id": cohort_id,
                "event_type": event_type,
                "payload_digest": payload_digest,
                "observed_at": observed_at,
            }))[:32]
            self._conn.execute(
                """
                INSERT INTO decision_events (
                    event_id, cohort_id, event_type, payload_json,
                    payload_digest, observed_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    event_id, cohort_id, event_type, payload_json,
                    payload_digest, observed_at,
                ),
            )
        return self.get_research_work_order(work_order_id)

    def rank_work_orders(self, *, capacity: int = 5) -> dict[str, list[dict[str, Any]]]:
        if capacity < 0:
            raise ValueError("capacity must be non-negative")
        authorized: set[str] = set()
        for event in self._conn.execute(
            """
            SELECT payload_json FROM decision_events
            WHERE event_type = 'research_work_order_queued'
            """
        ):
            payload = json.loads(event["payload_json"])
            work_order_id = payload.get("work_order_id")
            if isinstance(work_order_id, str) and work_order_id:
                authorized.add(work_order_id)
        rows = []
        for row in self._conn.execute(
                """
                SELECT work_order_id, cohort_id, context_digest, blockers_json, expiry,
                       decision_relevance, falsifiability, information_value,
                       status, created_at
                FROM research_work_orders
                WHERE status IN ('queued', 'researching')
                ORDER BY CASE status WHEN 'researching' THEN 0 ELSE 1 END,
                         decision_relevance DESC,
                         falsifiability DESC,
                         expiry ASC,
                         information_value DESC,
                         created_at ASC,
                         work_order_id ASC
                """
            ):
            item = dict(row)
            # v1.2 legacy rows were born as queued.  Only an explicit user-go
            # dispatch event grants pq1 research authority.
            if str(item["work_order_id"]) not in authorized:
                continue
            item["blockers"] = list(json.loads(item.pop("blockers_json"))["items"])
            rows.append(item)
        return {"selected": rows[:capacity], "backlog": rows[capacity:]}

    def _paper_exposure(
        self,
        *,
        paper_nav: float,
    ) -> dict[str, Any]:
        rows = [
            dict(row)
            for row in self._conn.execute(
                "SELECT company_id, weight FROM paper_position_projection WHERE weight > 0"
            )
        ]
        company_weights = {str(row["company_id"]): float(row["weight"]) for row in rows}
        return {
            "status": "available",
            "nav": paper_nav,
            "total_weight": sum(company_weights.values()),
            "company_weights": company_weights,
            "blockers": [],
        }

    def paper_exposure_snapshot(
        self,
        *,
        paper_nav: float,
    ) -> dict[str, Any]:
        """公開唯讀 wrapper；paper projection 仍是唯一模擬帳本 authority。"""

        if not math.isfinite(paper_nav) or paper_nav <= 0:
            raise ValueError("paper_nav must be positive and finite")
        return self._paper_exposure(paper_nav=paper_nav)

    def _latest_cohort_time(self, cohort_id: str) -> str | None:
        row = self._conn.execute(
            """
            SELECT MAX(event_time) AS latest FROM (
                SELECT observed_at AS event_time FROM decision_events WHERE cohort_id = ?
                UNION ALL
                SELECT evaluation_at FROM context_bundles WHERE cohort_id = ?
                UNION ALL
                SELECT effective_at FROM system_decisions WHERE cohort_id = ?
                UNION ALL
                SELECT effective_at FROM paper_events WHERE cohort_id = ?
                UNION ALL
                SELECT effective_at FROM probe_lifecycle_events WHERE cohort_id = ?
                UNION ALL
                SELECT lc.decided_at FROM live_choices lc
                JOIN system_decisions sd ON sd.decision_id = lc.decision_id
                WHERE sd.cohort_id = ?
                UNION ALL
                SELECT lf.executed_at FROM live_execution_reports lf
                JOIN system_decisions sd ON sd.decision_id = lf.decision_id
                WHERE sd.cohort_id = ?
            )
            """,
            (cohort_id,) * 7,
        ).fetchone()
        return str(row["latest"]) if row is not None and row["latest"] else None

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
        calculator: Callable[[Mapping[str, Any]], ProbeSizingResult],
        failure_at: str | None = None,
    ) -> DecisionExecutionResult:
        """Recompute paper capacity and commit decision/event in one transaction。"""

        if not idempotency_key.strip():
            raise ValueError("idempotency_key is required")
        effective_at = _timestamp(effective_at, "effective_at")
        request_json = _canonical_json(request_payload)
        request_digest = _digest(request_json)
        decision_id = "pd_" + _digest(idempotency_key)[:32]
        with immediate_transaction(self._conn):
            authority = self._conn.execute(
                """
                SELECT cb.cohort_id AS context_cohort,
                       cb.evaluation_at AS context_evaluation_at,
                       ca.cohort_id AS coverage_cohort,
                       ca.context_digest AS coverage_context
                FROM context_bundles cb
                JOIN coverage_assessments ca ON ca.assessment_id = ?
                WHERE cb.context_digest = ?
                """,
                (coverage_assessment_id, context_digest),
            ).fetchone()
            if (
                authority is None
                or authority["context_cohort"] != cohort_id
                or authority["coverage_cohort"] != cohort_id
                or authority["coverage_context"] != context_digest
            ):
                raise ValueError("decision authority context/coverage mismatch")
            if _time(effective_at, "effective_at") < _time(
                str(authority["context_evaluation_at"]), "context.evaluation_at"
            ):
                raise ValueError("decision cannot predate its frozen context")
            latest_causal = self._latest_cohort_time(cohort_id)
            if latest_causal is not None and _time(
                effective_at, "effective_at"
            ) < _time(latest_causal, "latest_causal"):
                raise ValueError("decision cannot predate the cohort causal timeline")
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

            exposure = self._paper_exposure(paper_nav=paper_nav)
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
                prior_event = self._conn.execute(
                    """
                    SELECT e.effective_at
                    FROM paper_position_projection p
                    JOIN paper_events e ON e.paper_event_id = p.source_event_id
                    WHERE p.company_id = ?
                    """,
                    (company_id,),
                ).fetchone()
                if prior_event is not None and _time(
                    effective_at, "effective_at"
                ) <= _time(str(prior_event["effective_at"]), "prior.effective_at"):
                    raise ValueError("paper update must follow its current source event")
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
        return float(self.paper_position_state(company_id)["weight"])

    def paper_position_state(
        self, company_id: str, *, as_of: str | None = None
    ) -> dict[str, Any]:
        if as_of is not None:
            cutoff = _timestamp(as_of, "as_of")
            rows = self._conn.execute(
                """
                SELECT paper_event_id, decision_id, payload_json
                FROM paper_events
                WHERE effective_at <= ?
                ORDER BY effective_at, paper_event_id
                """,
                (cutoff,),
            )
            latest: dict[str, Any] | None = None
            for row in rows:
                payload = json.loads(row["payload_json"])
                if payload.get("company_id") == company_id:
                    latest = {
                        "weight": float(payload["target_weight"]),
                        "source_event_id": row["paper_event_id"],
                        "decision_id": row["decision_id"],
                    }
            return latest or {
                "weight": 0.0,
                "source_event_id": None,
                "decision_id": None,
            }
        row = self._conn.execute(
            """
            SELECT p.weight, p.source_event_id, e.decision_id
            FROM paper_position_projection p
            LEFT JOIN paper_events e ON e.paper_event_id = p.source_event_id
            WHERE p.company_id = ?
            """,
            (company_id,),
        ).fetchone()
        if row is None:
            return {
                "weight": 0.0,
                "source_event_id": None,
                "decision_id": None,
            }
        return {
            "weight": float(row["weight"]),
            "source_event_id": row["source_event_id"],
            "decision_id": row["decision_id"],
        }

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

    def latest_decision_for_cohort(
        self, cohort_id: str, *, as_of: str | None = None
    ) -> dict[str, Any] | None:
        if as_of is None:
            row = self._conn.execute(
                """
                SELECT decision_id FROM system_decisions
                WHERE cohort_id = ?
                ORDER BY effective_at DESC, decision_id DESC LIMIT 1
                """,
                (cohort_id,),
            ).fetchone()
        else:
            row = self._conn.execute(
                """
                SELECT decision_id FROM system_decisions
                WHERE cohort_id = ? AND effective_at <= ?
                ORDER BY effective_at DESC, decision_id DESC LIMIT 1
                """,
                (cohort_id, _timestamp(as_of, "as_of")),
            ).fetchone()
        return self.get_decision(str(row["decision_id"])) if row is not None else None

    def signal_sources_for_cohort(self, cohort_id: str) -> tuple[str, ...]:
        sources = set()
        for row in self._conn.execute(
            """
            SELECT payload_json FROM decision_events
            WHERE cohort_id = ? AND event_type = 'qualified_signal'
            """,
            (cohort_id,),
        ):
            source_id = json.loads(row["payload_json"]).get("source_id")
            if isinstance(source_id, str) and source_id:
                sources.add(source_id)
        return tuple(sorted(sources))

    def latest_signal_payload(self, cohort_id: str) -> dict[str, Any]:
        """讀取 cohort 最近一筆原始 Signal，供 explicit reassessment 使用。"""

        row = self._conn.execute(
            """
            SELECT payload_json FROM decision_events
            WHERE cohort_id = ? AND event_type = 'qualified_signal'
            ORDER BY observed_at DESC, event_id DESC LIMIT 1
            """,
            (cohort_id,),
        ).fetchone()
        if row is None:
            raise KeyError(f"signal not found for cohort: {cohort_id}")
        return dict(json.loads(row["payload_json"]))

    def find_workflow_operation(
        self, operation_id: str, *, completed: bool
    ) -> dict[str, Any] | None:
        """依 server-owned operation ID 取得 immutable start/completion event。"""

        event_type = (
            "workflow_evaluation_completed"
            if completed
            else "workflow_evaluation_started"
        )
        for row in self._conn.execute(
            """
            SELECT event_id, cohort_id, payload_json, observed_at
            FROM decision_events WHERE event_type = ?
            ORDER BY observed_at, event_id
            """,
            (event_type,),
        ):
            payload = json.loads(row["payload_json"])
            if payload.get("operation_id") == operation_id:
                return {
                    "event_id": row["event_id"],
                    "cohort_id": row["cohort_id"],
                    "payload": payload,
                    "observed_at": row["observed_at"],
                }
        return None

    def list_operational_cohorts(self, *, as_of: str) -> list[dict[str, Any]]:
        """Today brief 專用唯讀列舉；不暴露 event/context private payload。"""

        cutoff = _timestamp(as_of, "as_of")
        rows = self._conn.execute(
            """
            SELECT cohort_id, company_id, research_ticker, created_at
            FROM decision_cohorts
            ORDER BY created_at, cohort_id
            """
        ).fetchall()
        result: list[dict[str, Any]] = []
        for row in rows:
            try:
                signal = self.latest_signal_payload(str(row["cohort_id"]))
            except KeyError:
                # 舊版／單元測試可由 decision 直接建立 cohort，沒有 qualified_signal。
                # 顯示 hint 是 additive；缺席時維持原 summary contract。
                signal = {}
            identity_hints = signal.get("identity_hints") or {}
            latest = self.latest_decision_for_cohort(
                str(row["cohort_id"]), as_of=cutoff
            )
            lifecycle = self.current_lifecycle(str(row["cohort_id"]))
            result.append(
                {
                    "cohort_id": row["cohort_id"],
                    "company_id": row["company_id"],
                    "research_ticker": row["research_ticker"],
                    # 未上市／無 ticker 的 company 仍可能依設計保持 unresolved。
                    # hint 只供 brief 顯示 exact 研究對象，不提升 identity authority。
                    "company_id_hint": identity_hints.get("company_id"),
                    "research_ticker_hint": identity_hints.get("research_ticker"),
                    "latest_decision_id": (
                        latest["decision_id"] if latest is not None else None
                    ),
                    "lifecycle_status": lifecycle.status,
                    "review_due_at": lifecycle.review_due_at,
                }
            )
        return result

    def get_coverage_metadata(self, assessment_id: str) -> dict[str, Any]:
        row = self._conn.execute(
            """
            SELECT assessment_id, catalyst, disproof, expiry
            FROM coverage_assessments WHERE assessment_id = ?
            """,
            (assessment_id,),
        ).fetchone()
        if row is None:
            raise KeyError(f"coverage assessment not found: {assessment_id}")
        return dict(row)

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
        confirmation_ref: str | None = None,
        approved_action_id: str | None = None,
        force_override: bool = False,
    ) -> str:
        decided_at = _timestamp(decided_at, "decided_at")
        if not math.isfinite(selected_weight) or selected_weight < 0:
            raise ValueError("selected_weight must be finite and non-negative")
        if confirmation_ref is not None and not confirmation_ref.strip():
            raise ValueError("confirmation_ref must be non-empty when provided")
        with immediate_transaction(self._conn):
            decision = self._conn.execute(
                """
                SELECT cohort_id, payload_json, effective_at
                FROM system_decisions WHERE decision_id = ?
                """,
                (decision_id,),
            ).fetchone()
            if decision is None:
                raise KeyError(f"decision not found: {decision_id}")
            if _time(decided_at, "decided_at") < _time(
                str(decision["effective_at"]), "decision.effective_at"
            ):
                raise ValueError("live choice cannot predate its decision")
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
            if confirmation_ref is not None:
                confirmation_payload = {
                    "choice_id": choice_id,
                    "decision_id": decision_id,
                    "confirmation_ref": confirmation_ref.strip(),
                }
                confirmation_json = _canonical_json(confirmation_payload)
                confirmation_digest = _digest(confirmation_json)
                confirmation_id = "de_" + _digest(
                    _canonical_json(
                        {
                            "cohort_id": decision["cohort_id"],
                            "event_type": "live_choice_confirmation",
                            "payload_digest": confirmation_digest,
                            "observed_at": decided_at,
                        }
                    )
                )[:32]
                self._conn.execute(
                    """
                    INSERT OR IGNORE INTO decision_events (
                        event_id, cohort_id, event_type, payload_json,
                        payload_digest, observed_at
                    ) VALUES (?, ?, 'live_choice_confirmation', ?, ?, ?)
                    """,
                    (
                        confirmation_id,
                        decision["cohort_id"],
                        confirmation_json,
                        confirmation_digest,
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
        executed_at = _timestamp(executed_at, "executed_at")
        if (
            not execution_ref.strip()
            or not math.isfinite(shares)
            or not math.isfinite(price)
            or price <= 0
            or not is_settlement_currency(currency)
        ):
            raise ValueError("invalid live fill")
        fill_id = "lf_" + _digest(execution_ref)[:32]
        with immediate_transaction(self._conn):
            choice = self._conn.execute(
                """
                SELECT lc.choice_id, lc.selected_weight, lc.decided_at,
                       sd.context_digest, sd.effective_at AS decision_effective_at
                FROM live_choices lc
                JOIN system_decisions sd ON sd.decision_id = lc.decision_id
                WHERE lc.decision_id = ?
                ORDER BY lc.decided_at DESC, lc.choice_id DESC LIMIT 1
                """,
                (decision_id,),
            ).fetchone()
            if choice is None:
                raise ValueError("live fill requires an explicit live choice")
            if float(choice["selected_weight"]) <= 0:
                raise ValueError("live fill requires a positive live choice")
            if _time(executed_at, "executed_at") < max(
                _time(str(choice["decided_at"]), "choice.decided_at"),
                _time(
                    str(choice["decision_effective_at"]),
                    "decision.effective_at",
                ),
            ):
                raise ValueError("live fill cannot predate its choice or decision")
            context = self.get_context_bundle(str(choice["context_digest"])).payload
            expected_currency = context.get("identity", {}).get("execution_currency")
            if currency != expected_currency:
                raise ValueError("live fill currency does not match execution identity")
            existing = self._conn.execute(
                """
                SELECT fill_id, decision_id, choice_id, execution_ref, shares,
                       price, currency, executed_at
                FROM live_execution_reports WHERE execution_ref = ?
                """,
                (execution_ref,),
            ).fetchone()
            expected = (
                decision_id,
                str(choice["choice_id"]),
                execution_ref,
                float(shares),
                float(price),
                currency,
                executed_at,
            )
            if existing is not None:
                actual = (
                    existing["decision_id"],
                    existing["choice_id"],
                    existing["execution_ref"],
                    float(existing["shares"]),
                    float(existing["price"]),
                    existing["currency"],
                    existing["executed_at"],
                )
                if actual != expected:
                    raise ValueError("execution_ref already belongs to a different fill")
                return str(existing["fill_id"])
            self._conn.execute(
                """
                INSERT OR IGNORE INTO live_execution_reports (
                    fill_id, decision_id, choice_id, execution_ref, shares,
                    price, currency, executed_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    fill_id,
                    decision_id,
                    choice["choice_id"],
                    execution_ref,
                    shares,
                    price,
                    currency,
                    executed_at,
                ),
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
            SELECT fill_id, choice_id, execution_ref, shares, price, currency, executed_at
            FROM live_execution_reports WHERE decision_id = ?
            ORDER BY executed_at DESC, fill_id DESC LIMIT 1
            """,
            (decision_id,),
        ).fetchone()
        return dict(row) if row is not None else None

    def latest_live_facts_for_cohort(
        self, cohort_id: str, *, as_of: str
    ) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
        cutoff = _timestamp(as_of, "as_of")
        choice = self._conn.execute(
            """
            SELECT lc.choice_id, lc.decision_id, lc.selected_weight,
                   lc.choice_type, lc.reason, lc.approved_action_id, lc.decided_at
            FROM live_choices lc
            JOIN system_decisions sd ON sd.decision_id = lc.decision_id
            WHERE sd.cohort_id = ? AND lc.decided_at <= ?
            ORDER BY lc.decided_at DESC, lc.choice_id DESC LIMIT 1
            """,
            (cohort_id, cutoff),
        ).fetchone()
        fill = self._conn.execute(
            """
            SELECT lf.fill_id, lf.decision_id, lf.choice_id, lf.execution_ref,
                   lf.shares, lf.price, lf.currency, lf.executed_at
            FROM live_execution_reports lf
            JOIN system_decisions sd ON sd.decision_id = lf.decision_id
            WHERE sd.cohort_id = ? AND lf.executed_at <= ?
            ORDER BY lf.executed_at DESC, lf.fill_id DESC LIMIT 1
            """,
            (cohort_id, cutoff),
        ).fetchone()
        return (
            dict(choice) if choice is not None else None,
            dict(fill) if fill is not None else None,
        )

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
        prepared_at = _timestamp(prepared_at, "prepared_at")
        expires_at = _timestamp(expires_at, "expires_at")
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
        decided_at = _timestamp(decided_at, "decided_at")
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
                """
                SELECT effective_at FROM system_decisions WHERE decision_id = ?
                """,
                (action["target_id"],),
            ).fetchone()
            if decision is None:
                raise KeyError("override target decision not found")
            if _time(decided_at, "decided_at") < _time(
                str(decision["effective_at"]), "decision.effective_at"
            ):
                raise ValueError("live override cannot predate its decision")
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
        effective_at = _timestamp(effective_at, "effective_at")
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
                SELECT paper_event_id, cohort_id, decision_id,
                       payload_json, effective_at
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
            current_source = self._conn.execute(
                """
                SELECT e.effective_at
                FROM paper_position_projection p
                JOIN paper_events e ON e.paper_event_id = p.source_event_id
                WHERE p.company_id = ?
                """,
                (company_id,),
            ).fetchone()
            if current_source is not None and _time(
                effective_at, "effective_at"
            ) <= _time(str(current_source["effective_at"]), "current.effective_at"):
                raise ValueError("paper amendment must follow the current source event")
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

    def current_lifecycle(self, cohort_id: str) -> LifecycleResult:
        row = self._conn.execute(
            """
            SELECT cohort_id, epoch, status, review_due_at, terminal_event_id
            FROM probe_lifecycle_epochs WHERE cohort_id = ?
            ORDER BY epoch DESC LIMIT 1
            """,
            (cohort_id,),
        ).fetchone()
        if row is None:
            cohort = self._conn.execute(
                "SELECT 1 FROM decision_cohorts WHERE cohort_id = ?", (cohort_id,)
            ).fetchone()
            if cohort is None:
                raise KeyError(f"cohort not found: {cohort_id}")
            return LifecycleResult(cohort_id, 1, "active", None, None)
        return LifecycleResult(
            cohort_id=str(row["cohort_id"]),
            epoch=int(row["epoch"]),
            status=str(row["status"]),
            review_due_at=row["review_due_at"],
            lifecycle_event_id=row["terminal_event_id"],
        )

    def lifecycle_epoch_started_at(self, cohort_id: str, epoch: int) -> str | None:
        row = self._conn.execute(
            """
            SELECT started_at FROM probe_lifecycle_epochs
            WHERE cohort_id = ? AND epoch = ?
            """,
            (cohort_id, epoch),
        ).fetchone()
        return str(row["started_at"]) if row is not None else None

    def _ensure_lifecycle_epoch(self, cohort_id: str, started_at: str) -> sqlite3.Row:
        row = self._conn.execute(
            """
            SELECT cohort_id, epoch, status, review_due_at, terminal_event_id
            FROM probe_lifecycle_epochs WHERE cohort_id = ?
            ORDER BY epoch DESC LIMIT 1
            """,
            (cohort_id,),
        ).fetchone()
        if row is not None:
            return row
        self._conn.execute(
            """
            INSERT INTO probe_lifecycle_epochs (
                cohort_id, epoch, status, started_at
            ) VALUES (?, 1, 'active', ?)
            """,
            (cohort_id, started_at),
        )
        row = self._conn.execute(
            """
            SELECT cohort_id, epoch, status, review_due_at, terminal_event_id
            FROM probe_lifecycle_epochs WHERE cohort_id = ? AND epoch = 1
            """,
            (cohort_id,),
        ).fetchone()
        assert row is not None
        return row

    def trigger_review_required(
        self,
        *,
        cohort_id: str,
        reason: str,
        evidence_refs: tuple[str, ...],
        effective_at: str,
        review_due_at: str,
    ) -> LifecycleResult:
        effective_at = _timestamp(effective_at, "effective_at")
        review_due_at = _timestamp(review_due_at, "review_due_at")
        with immediate_transaction(self._conn):
            latest_causal = self._latest_cohort_time(cohort_id)
            if latest_causal is not None and _time(
                effective_at, "effective_at"
            ) < _time(latest_causal, "latest_causal"):
                raise ValueError("review cannot predate the cohort causal timeline")
            current = self._ensure_lifecycle_epoch(cohort_id, effective_at)
            if current["status"] == "review_required":
                return LifecycleResult(
                    cohort_id, int(current["epoch"]), "review_required",
                    current["review_due_at"], None,
                )
            if current["status"] != "active":
                raise ValueError("terminal lifecycle cannot enter review_required")
            event_payload = {
                "cohort_id": cohort_id,
                "epoch": int(current["epoch"]),
                "from_status": "active",
                "to_status": "review_required",
                "reason": reason,
                "evidence_refs": evidence_refs,
                "effective_at": effective_at,
                "review_due_at": review_due_at,
            }
            digest = _digest(_canonical_json(event_payload))
            event_id = "le_" + digest[:32]
            self._conn.execute(
                """
                INSERT OR IGNORE INTO probe_lifecycle_events (
                    lifecycle_event_id, cohort_id, epoch, from_status,
                    to_status, reason, evidence_refs_json,
                    event_digest, effective_at
                ) VALUES (?, ?, ?, 'active', 'review_required', ?, ?, ?, ?)
                """,
                (
                    event_id,
                    cohort_id,
                    int(current["epoch"]),
                    reason,
                    _canonical_json({"items": evidence_refs}),
                    digest,
                    effective_at,
                ),
            )
            self._conn.execute(
                """
                UPDATE probe_lifecycle_epochs
                SET status = 'review_required', review_due_at = ?, updated_at = datetime('now')
                WHERE cohort_id = ? AND epoch = ?
                """,
                (review_due_at, cohort_id, int(current["epoch"])),
            )
            return LifecycleResult(
                cohort_id, int(current["epoch"]), "review_required", review_due_at, event_id
            )

    @staticmethod
    def _outcome_result(payload: Mapping[str, Any]) -> OutcomeResult:
        return OutcomeResult(
            outcome_id=str(payload["outcome_id"]),
            cohort_id=str(payload["cohort_id"]),
            epoch=int(payload["epoch"]),
            terminal_status=str(payload["terminal_status"]),
            claim_correctness=str(payload["claim_correctness"]),
            market_return_status=str(payload["market_return_status"]),
            absolute_return=(
                float(payload["absolute_return"])
                if payload.get("absolute_return") is not None
                else None
            ),
            benchmark_adjusted_return=(
                float(payload["benchmark_adjusted_return"])
                if payload.get("benchmark_adjusted_return") is not None
                else None
            ),
        )

    def close_lifecycle_with_outcome(
        self,
        *,
        cohort_id: str,
        terminal_status: str,
        outcome_payload: Mapping[str, Any],
        effective_at: str,
        failure_at: str | None = None,
    ) -> OutcomeResult:
        if terminal_status not in {"promoted", "rejected", "expired", "revised"}:
            raise ValueError("invalid terminal lifecycle status")
        effective_at = _timestamp(effective_at, "effective_at")
        with immediate_transaction(self._conn):
            latest_causal = self._latest_cohort_time(cohort_id)
            if latest_causal is not None and _time(
                effective_at, "effective_at"
            ) < _time(latest_causal, "latest_causal"):
                raise ValueError("outcome cannot predate the cohort causal timeline")
            current = self._ensure_lifecycle_epoch(cohort_id, effective_at)
            epoch = int(current["epoch"])
            if epoch > 1:
                previous = self._conn.execute(
                    """
                    SELECT payload_json FROM outcome_envelopes
                    WHERE cohort_id = ? AND epoch = ?
                    """,
                    (cohort_id, epoch - 1),
                ).fetchone()
                if previous is not None:
                    prior_payload = json.loads(previous["payload_json"])
                    if (
                        prior_payload.get("terminal_status") == "revised"
                        and prior_payload.get("effective_at") == effective_at
                    ):
                        prior_base = {
                            key: value
                            for key, value in prior_payload.items()
                            if key
                            not in {
                                "outcome_id",
                                "cohort_id",
                                "epoch",
                                "terminal_status",
                                "effective_at",
                            }
                        }
                        if (
                            terminal_status == "revised"
                            and _canonical_json(prior_base)
                            == _canonical_json(outcome_payload)
                        ):
                            return self._outcome_result(prior_payload)
                        raise ValueError("terminal revised epoch already closed at this timestamp")
            finalized_payload = dict(outcome_payload) | {
                "cohort_id": cohort_id,
                "epoch": epoch,
                "terminal_status": terminal_status,
                "effective_at": effective_at,
            }
            outcome_json_without_id = _canonical_json(finalized_payload)
            outcome_digest = _digest(outcome_json_without_id)
            outcome_id = "oe_" + outcome_digest[:32]
            finalized_payload["outcome_id"] = outcome_id
            outcome_json = _canonical_json(finalized_payload)
            existing = self._conn.execute(
                """
                SELECT outcome_id, outcome_digest, payload_json
                FROM outcome_envelopes WHERE cohort_id = ? AND epoch = ?
                """,
                (cohort_id, epoch),
            ).fetchone()
            if existing is not None:
                if existing["outcome_digest"] != outcome_digest:
                    raise ValueError("terminal epoch already has a different outcome")
                return self._outcome_result(json.loads(existing["payload_json"]))
            if current["status"] not in {"active", "review_required"}:
                raise ValueError("terminal lifecycle state is missing its outcome")
            event_payload = {
                "cohort_id": cohort_id,
                "epoch": epoch,
                "from_status": str(current["status"]),
                "to_status": terminal_status,
                "reason": finalized_payload["reason"],
                "evidence_refs": finalized_payload["evidence_refs"],
                "effective_at": effective_at,
            }
            event_digest = _digest(_canonical_json(event_payload))
            event_id = "le_" + event_digest[:32]
            self._conn.execute(
                """
                INSERT INTO probe_lifecycle_events (
                    lifecycle_event_id, cohort_id, epoch, from_status,
                    to_status, reason, evidence_refs_json,
                    event_digest, effective_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event_id,
                    cohort_id,
                    epoch,
                    current["status"],
                    terminal_status,
                    finalized_payload["reason"],
                    _canonical_json({"items": finalized_payload["evidence_refs"]}),
                    event_digest,
                    effective_at,
                ),
            )
            if failure_at == "after_terminal":
                raise RuntimeError("injected failure after terminal event")
            self._conn.execute(
                """
                INSERT INTO outcome_envelopes (
                    outcome_id, cohort_id, epoch, terminal_event_id,
                    outcome_digest, terminal_status, claim_correctness,
                    market_return_status, absolute_return,
                    benchmark_adjusted_return, calculator_version,
                    payload_json, effective_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    outcome_id,
                    cohort_id,
                    epoch,
                    event_id,
                    outcome_digest,
                    terminal_status,
                    finalized_payload["claim_correctness"],
                    finalized_payload["market_return_status"],
                    finalized_payload.get("absolute_return"),
                    finalized_payload.get("benchmark_adjusted_return"),
                    finalized_payload.get("calculator_version"),
                    outcome_json,
                    effective_at,
                ),
            )
            if failure_at == "after_outcome":
                raise RuntimeError("injected failure after outcome")
            self._conn.execute(
                """
                UPDATE probe_lifecycle_epochs
                SET status = ?, terminal_event_id = ?, review_due_at = NULL,
                    updated_at = datetime('now')
                WHERE cohort_id = ? AND epoch = ?
                """,
                (terminal_status, event_id, cohort_id, epoch),
            )
            if terminal_status == "revised":
                self._conn.execute(
                    """
                    INSERT INTO probe_lifecycle_epochs (
                        cohort_id, epoch, status, started_at
                    ) VALUES (?, ?, 'active', ?)
                    """,
                    (cohort_id, epoch + 1, effective_at),
                )
            elif terminal_status in {"promoted", "rejected", "expired"}:
                self._conn.execute(
                    """
                    UPDATE probe_projection SET status = ?, updated_at = datetime('now')
                    WHERE cohort_id = ?
                    """,
                    (terminal_status, cohort_id),
                )
            return self._outcome_result(finalized_payload)

    def get_outcome(self, outcome_id: str) -> dict[str, Any]:
        row = self._conn.execute(
            "SELECT payload_json FROM outcome_envelopes WHERE outcome_id = ?",
            (outcome_id,),
        ).fetchone()
        if row is None:
            raise KeyError(f"outcome not found: {outcome_id}")
        return json.loads(row["payload_json"])

    def lifecycle_invariant_violations(self) -> list[str]:
        violations: list[str] = []
        rows = self._conn.execute(
            """
            SELECT e.cohort_id, e.epoch, e.status, o.outcome_id
            FROM probe_lifecycle_epochs e
            LEFT JOIN outcome_envelopes o
              ON o.cohort_id = e.cohort_id AND o.epoch = e.epoch
            """
        )
        terminal = {"promoted", "rejected", "expired", "revised"}
        for row in rows:
            if row["status"] in terminal and row["outcome_id"] is None:
                violations.append(
                    f"terminal_without_outcome:{row['cohort_id']}:{row['epoch']}"
                )
            if row["status"] not in terminal and row["outcome_id"] is not None:
                violations.append(
                    f"outcome_on_nonterminal:{row['cohort_id']}:{row['epoch']}"
                )
        return violations
