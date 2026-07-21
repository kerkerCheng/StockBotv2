"""Append-only Engine C manual observations and rebuildable projection。"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from typing import Any, Mapping


def _canonical(value: Mapping[str, Any]) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _is_sqlite(conn: Any) -> bool:
    return isinstance(conn, sqlite3.Connection)


def ensure_manual_observation_schema(conn: Any) -> None:
    """Bootstrap SQLite; Postgres schema is owned by versioned migrations。"""

    if not _is_sqlite(conn):
        return
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS manual_observations (
            observation_id TEXT PRIMARY KEY,
            ticker         TEXT NOT NULL,
            field_name     TEXT NOT NULL,
            value          TEXT NOT NULL,
            source_ref     TEXT NOT NULL,
            as_of          TEXT NOT NULL,
            author         TEXT NOT NULL,
            supersedes_id  TEXT REFERENCES manual_observations(observation_id),
            recorded_at    TEXT NOT NULL DEFAULT (datetime('now')),
            payload_digest TEXT NOT NULL UNIQUE
        );
        CREATE INDEX IF NOT EXISTS idx_manual_observation_field_time
            ON manual_observations (ticker, field_name, as_of, observation_id);
        """
    )


def append_manual_observation(
    conn: Any,
    *,
    ticker: str,
    field_name: str,
    value: str,
    source_ref: str,
    as_of: str,
    author: str,
    supersedes_id: str | None = None,
    commit: bool = True,
) -> str:
    fields = {
        "ticker": ticker.upper().strip(),
        "field_name": field_name.strip(),
        "value": value.strip(),
        "source_ref": source_ref.strip(),
        "as_of": as_of.strip(),
        "author": author.strip(),
        "supersedes_id": supersedes_id,
    }
    if any(not fields[key] for key in (
        "ticker", "field_name", "value", "source_ref", "as_of", "author"
    )):
        raise ValueError("manual observation requires value, provenance, as_of, and author")
    ensure_manual_observation_schema(conn)
    payload = _canonical(fields)
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    observation_id = "mo_" + digest[:32]
    try:
        values = (
            observation_id,
            fields["ticker"],
            fields["field_name"],
            fields["value"],
            fields["source_ref"],
            fields["as_of"],
            fields["author"],
            supersedes_id,
            digest,
        )
        projection = (
            fields["ticker"],
            fields["field_name"],
            fields["value"],
            fields["source_ref"],
            fields["as_of"],
        )
        if _is_sqlite(conn):
            conn.execute(
                """
                INSERT OR IGNORE INTO manual_observations (
                    observation_id, ticker, field_name, value, source_ref,
                    as_of, author, supersedes_id, payload_digest
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                values,
            )
            conn.execute(
                """
                INSERT INTO manual_fields (
                    ticker, field_name, value, source_note, updated_at
                ) VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(ticker, field_name) DO UPDATE SET
                    value=excluded.value,
                    source_note=excluded.source_note,
                    updated_at=excluded.updated_at
                """,
                projection,
            )
        else:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO manual_observations (
                        observation_id, ticker, field_name, value, source_ref,
                        as_of, author, supersedes_id, payload_digest
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT(payload_digest) DO NOTHING
                    """,
                    values,
                )
                cursor.execute(
                    """
                    INSERT INTO manual_fields (
                        ticker, field_name, value, source_note, updated_at
                    ) VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT(ticker, field_name) DO UPDATE SET
                        value=EXCLUDED.value,
                        source_note=EXCLUDED.source_note,
                        updated_at=EXCLUDED.updated_at
                    """,
                    projection,
                )
        if commit:
            conn.commit()
    except Exception:
        if commit:
            conn.rollback()
        raise
    return observation_id


def rebuild_manual_projection(conn: Any, *, commit: bool = True) -> int:
    ensure_manual_observation_schema(conn)
    select_sql = """
        SELECT ticker, field_name, value, source_ref, as_of
        FROM manual_observations
        ORDER BY as_of, recorded_at, observation_id
    """
    if _is_sqlite(conn):
        rows = conn.execute(select_sql).fetchall()
    else:
        with conn.cursor() as cursor:
            cursor.execute(select_sql)
            rows = cursor.fetchall()
    try:
        if _is_sqlite(conn):
            conn.execute("DELETE FROM manual_fields")
            for row in rows:
                conn.execute(
                    """
                    INSERT INTO manual_fields (
                        ticker, field_name, value, source_note, updated_at
                    ) VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(ticker, field_name) DO UPDATE SET
                        value=excluded.value,
                        source_note=excluded.source_note,
                        updated_at=excluded.updated_at
                    """,
                    tuple(row),
                )
        else:
            with conn.cursor() as cursor:
                cursor.execute("DELETE FROM manual_fields")
                for row in rows:
                    cursor.execute(
                        """
                        INSERT INTO manual_fields (
                            ticker, field_name, value, source_note, updated_at
                        ) VALUES (%s, %s, %s, %s, %s)
                        ON CONFLICT(ticker, field_name) DO UPDATE SET
                            value=EXCLUDED.value,
                            source_note=EXCLUDED.source_note,
                            updated_at=EXCLUDED.updated_at
                        """,
                        tuple(row),
                    )
        if commit:
            conn.commit()
    except Exception:
        if commit:
            conn.rollback()
        raise
    return len(rows)
