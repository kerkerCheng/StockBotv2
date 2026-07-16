"""
db.py — Engine C 資料庫連線抽象層（SQLite 預設，可換 Postgres）。

設計原則：
- 預設 SQLite，零安裝，本機單人用
- POSTGRES_DSN 或 POSTGRES_HOST 有設值時自動切換 Postgres
- 呼叫端不需知道底層是哪個 DB

用法:
    from engine_c.db import get_conn, DB_TYPE
    conn = get_conn()   # sqlite3.Connection 或 psycopg2.connection
"""
from __future__ import annotations

import os
import sqlite3
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_SQLITE_PATH = _ROOT / "engine_c" / "stockbot.db"

_PG_ENVS = ("POSTGRES_DSN", "POSTGRES_HOST")


def _use_postgres() -> bool:
    return any(os.environ.get(k) for k in _PG_ENVS)


DB_TYPE: str = "postgres" if _use_postgres() else "sqlite"


def _ensure_sqlite_schema(conn: sqlite3.Connection) -> None:
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS financial_snapshots (
            id                   INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker               TEXT    NOT NULL,
            snapshot_date        TEXT    NOT NULL,
            gross_margin         REAL,
            operating_margin     REAL,
            revenue_ttm          INTEGER,
            shares_outstanding   INTEGER,
            ev_revenue           REAL,
            pe_trailing          REAL,
            pe_forward           REAL,
            price                REAL,
            analyst_target_mean  REAL,
            analyst_target_high  REAL,
            analyst_target_low   REAL,
            analyst_target_count INTEGER,
            fetched_at           TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE (ticker, snapshot_date)
        );
        CREATE TABLE IF NOT EXISTS manual_fields (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker      TEXT    NOT NULL,
            field_name  TEXT    NOT NULL,
            value       TEXT,
            updated_at  TEXT NOT NULL DEFAULT (datetime('now')),
            source_note TEXT,
            UNIQUE (ticker, field_name)
        );
        CREATE TABLE IF NOT EXISTS consensus_coverage_observations (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker           TEXT    NOT NULL,
            observation_date TEXT    NOT NULL,
            analyst_count    INTEGER,
            source           TEXT    NOT NULL,
            data_status      TEXT    NOT NULL
                             CHECK (data_status IN ('observed', 'manual_required')),
            fetched_at       TEXT    NOT NULL DEFAULT (datetime('now')),
            UNIQUE (ticker, observation_date, source),
            CHECK (
                (data_status = 'observed' AND analyst_count IS NOT NULL AND analyst_count >= 0)
                OR (data_status = 'manual_required' AND analyst_count IS NULL)
            )
        );
        CREATE INDEX IF NOT EXISTS idx_coverage_ticker_date
            ON consensus_coverage_observations (ticker, observation_date DESC);
    """)
    conn.commit()


def get_conn():
    """
    回傳資料庫連線。
    - SQLite: sqlite3.Connection（thread_check 關閉，適合腳本用）
    - Postgres: psycopg2.connection
    """
    if _use_postgres():
        try:
            import psycopg2
        except ImportError:
            raise RuntimeError("psycopg2 未安裝。換 SQLite：不設 POSTGRES_HOST/DSN 即可。")
        try:
            connect_timeout = int(os.environ.get("POSTGRES_CONNECT_TIMEOUT", "5"))
        except ValueError as exc:
            raise RuntimeError("POSTGRES_CONNECT_TIMEOUT must be a positive integer") from exc
        if connect_timeout <= 0:
            raise RuntimeError("POSTGRES_CONNECT_TIMEOUT must be a positive integer")
        dsn = os.environ.get("POSTGRES_DSN")
        if dsn:
            return psycopg2.connect(dsn, connect_timeout=connect_timeout)
        return psycopg2.connect(
            host=os.environ.get("POSTGRES_HOST", "localhost"),
            port=int(os.environ.get("POSTGRES_PORT", 5432)),
            dbname=os.environ.get("POSTGRES_DB", "stockbot"),
            user=os.environ.get("POSTGRES_USER", "stockbot"),
            password=os.environ.get("POSTGRES_PASSWORD", ""),
            connect_timeout=connect_timeout,
        )

    conn = sqlite3.connect(str(_SQLITE_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    _ensure_sqlite_schema(conn)
    return conn


def placeholder(n: int = 1) -> str:
    """
    DB 參數佔位符：SQLite 用 '?', Postgres 用 '%s'。
    n=1 → single; n=3 → '?,?,?' or '%s,%s,%s'
    """
    p = "%s" if _use_postgres() else "?"
    return ",".join([p] * n)


def upsert_snapshot(conn, snap: dict, *, commit: bool = True) -> None:
    """INSERT OR REPLACE financial_snapshots（相容 SQLite + Postgres）。"""
    if _use_postgres():
        sql = """
        INSERT INTO financial_snapshots (
            ticker, snapshot_date,
            gross_margin, operating_margin, revenue_ttm, shares_outstanding,
            ev_revenue, pe_trailing, pe_forward, price,
            analyst_target_mean, analyst_target_high, analyst_target_low,
            analyst_target_count, fetched_at
        ) VALUES (
            %(ticker)s, %(snapshot_date)s,
            %(gross_margin)s, %(operating_margin)s, %(revenue_ttm)s,
            %(shares_outstanding)s, %(ev_revenue)s, %(pe_trailing)s,
            %(pe_forward)s, %(price)s,
            %(analyst_target_mean)s, %(analyst_target_high)s,
            %(analyst_target_low)s, %(analyst_target_count)s, %(fetched_at)s
        ) ON CONFLICT (ticker, snapshot_date) DO UPDATE SET
            gross_margin=EXCLUDED.gross_margin,
            operating_margin=EXCLUDED.operating_margin,
            revenue_ttm=EXCLUDED.revenue_ttm,
            shares_outstanding=EXCLUDED.shares_outstanding,
            ev_revenue=EXCLUDED.ev_revenue, pe_trailing=EXCLUDED.pe_trailing,
            pe_forward=EXCLUDED.pe_forward, price=EXCLUDED.price,
            analyst_target_mean=EXCLUDED.analyst_target_mean,
            analyst_target_high=EXCLUDED.analyst_target_high,
            analyst_target_low=EXCLUDED.analyst_target_low,
            analyst_target_count=EXCLUDED.analyst_target_count,
            fetched_at=EXCLUDED.fetched_at
        """
        with conn.cursor() as cur:
            cur.execute(sql, snap)
        if commit:
            conn.commit()
    else:
        # SQLite: INSERT OR REPLACE（UNIQUE 約束觸發替換）
        sql = """
        INSERT OR REPLACE INTO financial_snapshots (
            ticker, snapshot_date,
            gross_margin, operating_margin, revenue_ttm, shares_outstanding,
            ev_revenue, pe_trailing, pe_forward, price,
            analyst_target_mean, analyst_target_high, analyst_target_low,
            analyst_target_count, fetched_at
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """
        conn.execute(sql, (
            snap["ticker"], str(snap["snapshot_date"]),
            snap["gross_margin"], snap["operating_margin"], snap["revenue_ttm"],
            snap["shares_outstanding"], snap["ev_revenue"], snap["pe_trailing"],
            snap["pe_forward"], snap["price"],
            snap["analyst_target_mean"], snap["analyst_target_high"],
            snap["analyst_target_low"], snap["analyst_target_count"],
            str(snap["fetched_at"]),
        ))
        if commit:
            conn.commit()


def upsert_coverage_observation(
    conn, observation: dict, *, commit: bool = True
) -> None:
    """Idempotently store one objective analyst-coverage observation."""

    required = {
        "ticker",
        "observation_date",
        "analyst_count",
        "source",
        "data_status",
        "fetched_at",
    }
    missing = sorted(required - set(observation))
    if missing:
        raise ValueError(f"coverage observation missing keys: {', '.join(missing)}")
    if observation["data_status"] not in {"observed", "manual_required"}:
        raise ValueError("coverage data_status must be observed or manual_required")
    if observation["data_status"] == "observed" and observation["analyst_count"] is None:
        raise ValueError("observed coverage requires analyst_count")
    if (
        observation["data_status"] == "manual_required"
        and observation["analyst_count"] is not None
    ):
        raise ValueError("manual_required coverage must not include analyst_count")
    if (
        observation["analyst_count"] is not None
        and (
            isinstance(observation["analyst_count"], bool)
            or not isinstance(observation["analyst_count"], int)
            or observation["analyst_count"] < 0
        )
    ):
        raise ValueError("analyst_count must be a non-negative integer or null")

    if _use_postgres():
        sql = """
        INSERT INTO consensus_coverage_observations (
            ticker, observation_date, analyst_count, source, data_status, fetched_at
        ) VALUES (
            %(ticker)s, %(observation_date)s, %(analyst_count)s,
            %(source)s, %(data_status)s, %(fetched_at)s
        ) ON CONFLICT (ticker, observation_date, source) DO UPDATE SET
            analyst_count=EXCLUDED.analyst_count,
            data_status=EXCLUDED.data_status,
            fetched_at=EXCLUDED.fetched_at
        """
        with conn.cursor() as cur:
            cur.execute(sql, observation)
    else:
        conn.execute(
            """
            INSERT INTO consensus_coverage_observations (
                ticker, observation_date, analyst_count, source, data_status, fetched_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT (ticker, observation_date, source) DO UPDATE SET
                analyst_count=excluded.analyst_count,
                data_status=excluded.data_status,
                fetched_at=excluded.fetched_at
            """,
            (
                observation["ticker"],
                str(observation["observation_date"]),
                observation["analyst_count"],
                observation["source"],
                observation["data_status"],
                str(observation["fetched_at"]),
            ),
        )
    if commit:
        conn.commit()


def get_latest_coverage_observation(conn, ticker: str) -> dict | None:
    """Return the latest raw coverage row without a derived classification."""

    sql = """
        SELECT ticker, observation_date, analyst_count, source, data_status, fetched_at
        FROM consensus_coverage_observations
        WHERE ticker = %s
        ORDER BY observation_date DESC, fetched_at DESC
        LIMIT 1
    """ if _use_postgres() else """
        SELECT ticker, observation_date, analyst_count, source, data_status, fetched_at
        FROM consensus_coverage_observations
        WHERE ticker = ?
        ORDER BY observation_date DESC, fetched_at DESC
        LIMIT 1
    """
    if _use_postgres():
        with conn.cursor() as cur:
            cur.execute(sql, (ticker,))
            row = cur.fetchone()
            columns = [description[0] for description in cur.description] if row else []
        return dict(zip(columns, row)) if row else None
    row = conn.execute(sql, (ticker,)).fetchone()
    return dict(row) if row is not None else None
