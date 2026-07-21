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


_SCHEMA_PATH = Path(__file__).with_name("schema.sql")


def _canonical_json(payload: Mapping[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


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
