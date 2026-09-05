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

import json
import os
import sqlite3
from pathlib import Path

from storage.relational import (
    connect_sqlite,
    initialize_private_root,
    validate_private_destination,
)

_ROOT = Path(__file__).resolve().parent.parent

_PG_ENVS = ("POSTGRES_DSN", "POSTGRES_HOST")


def _use_postgres() -> bool:
    return any(os.environ.get(k) for k in _PG_ENVS)


DB_TYPE: str = "postgres" if _use_postgres() else "sqlite"


def sqlite_path(
    *,
    repo_root: Path | None = None,
    private_root: Path | None = None,
) -> Path:
    """Resolve the active ignored Engine C authority without trusting broad paths。"""

    repo = (repo_root or _ROOT).resolve()
    private = initialize_private_root(
        (private_root or repo / "library" / "private").resolve(),
        repo_root=repo,
    )
    pointer = private / "runtime_pointer.json"
    destination = private / "engine_c" / "stockbot.db"
    if pointer.is_file():
        try:
            payload = json.loads(pointer.read_text(encoding="utf-8"))
            relative = payload["engine_c"]
        except (KeyError, OSError, json.JSONDecodeError, TypeError) as exc:
            raise RuntimeError("Engine C runtime pointer is invalid") from exc
        if not isinstance(relative, str) or Path(relative).is_absolute():
            raise RuntimeError("Engine C runtime pointer must be a relative path")
        destination = private / relative
        destination = validate_private_destination(
            destination,
            private_root=private,
            repo_root=repo,
        )
        if not destination.is_file():
            raise RuntimeError("Engine C runtime pointer target is missing")
        check_conn = sqlite3.connect(
            f"file:{destination.as_posix()}?mode=ro", uri=True
        )
        try:
            if check_conn.execute("PRAGMA quick_check").fetchone() != ("ok",):
                raise RuntimeError("Engine C runtime pointer target is corrupt")
        finally:
            check_conn.close()
        return destination
    legacy = repo / "engine_c" / "stockbot.db"
    if legacy.is_file():
        return legacy.resolve()
    versioned = list((private / "engine_c").glob("stockbot-engine-c-private-v*.db"))
    if versioned:
        raise RuntimeError("Engine C versioned runtime exists without an authority pointer")
    return validate_private_destination(
        destination,
        private_root=private,
        repo_root=repo,
    )


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
            cash_and_equivalents REAL,
            total_debt           REAL,
            free_cash_flow_ttm   REAL,
            ev_revenue           REAL,
            pe_trailing          REAL,
            pe_forward           REAL,
            price                REAL,
            analyst_target_mean  REAL,
            analyst_target_high  REAL,
            analyst_target_low   REAL,
            analyst_target_count INTEGER,
            fetched_at           TEXT NOT NULL DEFAULT (datetime('now')),
            -- bar_date／price_kind 是 2026-08-14 從 snapshot_date 拆出來的兩種語意。
            -- snapshot_date 一直是「跑 ETL 的當地日期」，不是行情交易日：收盤後跑的
            -- 批次被標成隔天（fetched_at 07-28 22:34 取到 07-28 收盤，卻標 07-29），
            -- 盤中跑的存的是盤中價。任何拿它當 as-of 的消費者都系統性差一天。
            -- NULL 表示「這列早於本次修正，as-of 未知」——不得猜測補值。
            bar_date             TEXT,
            price_kind           TEXT,
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
        -- 會計年度別的分析師共識（Phase 2 Causal Fundamental Model，2026-09-05）。
        -- 身分是 fiscal_period_end（絕對日期），在抓取當下由 provider 的
        -- lastFiscalYearEnd／nextFiscalYearEnd 解析；relative_label 只留作 provenance。
        -- 取不到的期間不寫列——缺料是「沒有列」，不是 0。
        CREATE TABLE IF NOT EXISTS consensus_estimates (
            id                 INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker             TEXT    NOT NULL,
            snapshot_date      TEXT    NOT NULL,
            bar_date           TEXT,
            metric             TEXT    NOT NULL CHECK (metric IN ('eps', 'revenue')),
            period_kind        TEXT    NOT NULL CHECK (period_kind IN ('fiscal_year')),
            relative_label     TEXT    NOT NULL,
            fiscal_period_end  TEXT    NOT NULL,
            fiscal_label       TEXT    NOT NULL,
            estimate_avg       REAL,
            estimate_low       REAL,
            estimate_high      REAL,
            analyst_count      INTEGER,
            year_ago_actual    REAL,
            growth             REAL,
            currency           TEXT,
            source             TEXT    NOT NULL,
            fetched_at         TEXT    NOT NULL,
            UNIQUE (ticker, snapshot_date, metric, fiscal_period_end, source)
        );
        CREATE INDEX IF NOT EXISTS idx_consensus_estimates_ticker_date
            ON consensus_estimates (ticker, snapshot_date DESC);
    """)
    columns = {
        row[1] for row in conn.execute("PRAGMA table_info(financial_snapshots)")
    }
    for name in (
        "cash_and_equivalents",
        "total_debt",
        "free_cash_flow_ttm",
    ):
        if name not in columns:
            conn.execute(f"ALTER TABLE financial_snapshots ADD COLUMN {name} REAL")
    for name in ("bar_date", "price_kind"):
        # 既有列一律留 NULL：它們的 as-of 真的不可知，補值等於用猜測冒充事實。
        if name not in columns:
            conn.execute(f"ALTER TABLE financial_snapshots ADD COLUMN {name} TEXT")
    # 下一會計年度營收共識（Phase 4c，2026-09-04）。既有列留 NULL——共識是每天變的
    # 觀測，回填等於把今天的共識冒充成當時的（同 bar_date 的理由）。
    for name in ("revenue_estimate_next_fy", "revenue_estimate_next_fy_growth"):
        if name not in columns:
            conn.execute(f"ALTER TABLE financial_snapshots ADD COLUMN {name} REAL")
    if "revenue_estimate_next_fy_analysts" not in columns:
        conn.execute(
            "ALTER TABLE financial_snapshots "
            "ADD COLUMN revenue_estimate_next_fy_analysts INTEGER")
    from engine_c.manual_observations import ensure_manual_observation_schema
    from engine_c.technical import ensure_technical_schema

    ensure_manual_observation_schema(conn)
    ensure_technical_schema(conn)
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

    path = sqlite_path()
    legacy = (_ROOT / "engine_c" / "stockbot.db").resolve()
    if path.resolve() == legacy:
        conn = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn
    conn = connect_sqlite(path, create=not path.exists())
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
    snapshot = dict(snap)
    for key in (
        "cash_and_equivalents",
        "total_debt",
        "free_cash_flow_ttm",
        "bar_date",
        "price_kind",
        "revenue_estimate_next_fy",
        "revenue_estimate_next_fy_growth",
        "revenue_estimate_next_fy_analysts",
    ):
        snapshot.setdefault(key, None)
    if _use_postgres():
        sql = """
        INSERT INTO financial_snapshots (
            ticker, snapshot_date,
            gross_margin, operating_margin, revenue_ttm, shares_outstanding,
            cash_and_equivalents, total_debt, free_cash_flow_ttm,
            ev_revenue, pe_trailing, pe_forward, price,
            analyst_target_mean, analyst_target_high, analyst_target_low,
            analyst_target_count, fetched_at, bar_date, price_kind,
            revenue_estimate_next_fy, revenue_estimate_next_fy_growth,
            revenue_estimate_next_fy_analysts
        ) VALUES (
            %(ticker)s, %(snapshot_date)s,
            %(gross_margin)s, %(operating_margin)s, %(revenue_ttm)s,
            %(shares_outstanding)s, %(cash_and_equivalents)s,
            %(total_debt)s, %(free_cash_flow_ttm)s,
            %(ev_revenue)s, %(pe_trailing)s,
            %(pe_forward)s, %(price)s,
            %(analyst_target_mean)s, %(analyst_target_high)s,
            %(analyst_target_low)s, %(analyst_target_count)s, %(fetched_at)s,
            %(bar_date)s, %(price_kind)s,
            %(revenue_estimate_next_fy)s, %(revenue_estimate_next_fy_growth)s,
            %(revenue_estimate_next_fy_analysts)s
        ) ON CONFLICT (ticker, snapshot_date) DO UPDATE SET
            gross_margin=EXCLUDED.gross_margin,
            operating_margin=EXCLUDED.operating_margin,
            revenue_ttm=EXCLUDED.revenue_ttm,
            shares_outstanding=EXCLUDED.shares_outstanding,
            cash_and_equivalents=EXCLUDED.cash_and_equivalents,
            total_debt=EXCLUDED.total_debt,
            free_cash_flow_ttm=EXCLUDED.free_cash_flow_ttm,
            ev_revenue=EXCLUDED.ev_revenue, pe_trailing=EXCLUDED.pe_trailing,
            pe_forward=EXCLUDED.pe_forward, price=EXCLUDED.price,
            analyst_target_mean=EXCLUDED.analyst_target_mean,
            analyst_target_high=EXCLUDED.analyst_target_high,
            analyst_target_low=EXCLUDED.analyst_target_low,
            analyst_target_count=EXCLUDED.analyst_target_count,
            fetched_at=EXCLUDED.fetched_at,
            bar_date=EXCLUDED.bar_date, price_kind=EXCLUDED.price_kind,
            revenue_estimate_next_fy=EXCLUDED.revenue_estimate_next_fy,
            revenue_estimate_next_fy_growth=EXCLUDED.revenue_estimate_next_fy_growth,
            revenue_estimate_next_fy_analysts=EXCLUDED.revenue_estimate_next_fy_analysts
        """
        with conn.cursor() as cur:
            cur.execute(sql, snapshot)
        if commit:
            conn.commit()
    else:
        # SQLite: INSERT OR REPLACE（UNIQUE 約束觸發替換）
        sql = """
        INSERT OR REPLACE INTO financial_snapshots (
            ticker, snapshot_date,
            gross_margin, operating_margin, revenue_ttm, shares_outstanding,
            cash_and_equivalents, total_debt, free_cash_flow_ttm,
            ev_revenue, pe_trailing, pe_forward, price,
            analyst_target_mean, analyst_target_high, analyst_target_low,
            analyst_target_count, fetched_at, bar_date, price_kind,
            revenue_estimate_next_fy, revenue_estimate_next_fy_growth,
            revenue_estimate_next_fy_analysts
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """
        conn.execute(sql, (
            snapshot["ticker"], str(snapshot["snapshot_date"]),
            snapshot["gross_margin"], snapshot["operating_margin"], snapshot["revenue_ttm"],
            snapshot["shares_outstanding"], snapshot["cash_and_equivalents"],
            snapshot["total_debt"], snapshot["free_cash_flow_ttm"],
            snapshot["ev_revenue"], snapshot["pe_trailing"],
            snapshot["pe_forward"], snapshot["price"],
            snapshot["analyst_target_mean"], snapshot["analyst_target_high"],
            snapshot["analyst_target_low"], snapshot["analyst_target_count"],
            str(snapshot["fetched_at"]),
            snapshot.get("bar_date"), snapshot.get("price_kind"),
            snapshot.get("revenue_estimate_next_fy"),
            snapshot.get("revenue_estimate_next_fy_growth"),
            snapshot.get("revenue_estimate_next_fy_analysts"),
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


#: `consensus_estimates` 一列的必要欄位。缺一即拒收——「不知道是哪個會計期間」的共識
#: 沒有身分，寫進去只會在比較時被誤當成別的年度。
CONSENSUS_ESTIMATE_COLUMNS: tuple[str, ...] = (
    "ticker", "snapshot_date", "bar_date", "metric", "period_kind", "relative_label",
    "fiscal_period_end", "fiscal_label", "estimate_avg", "estimate_low", "estimate_high",
    "analyst_count", "year_ago_actual", "growth", "currency", "source", "fetched_at",
)
_CONSENSUS_ESTIMATE_REQUIRED: frozenset[str] = frozenset({
    "ticker", "snapshot_date", "metric", "period_kind", "relative_label",
    "fiscal_period_end", "fiscal_label", "source", "fetched_at",
})


def upsert_consensus_estimate(conn, row: dict, *, commit: bool = True) -> None:
    """Idempotently store one fiscal-period-identified consensus estimate。

    ⚠ `fiscal_period_end` 是身分：呼叫端必須已在抓取當下把 `0y`／`+1y` 解析成絕對日期
    （`engine_c.fiscal.resolve_fiscal_year_end`）；解析不出來就**不要呼叫本函式**，
    缺料是沒有列，不是一列 0。
    """
    missing = sorted(k for k in _CONSENSUS_ESTIMATE_REQUIRED if not row.get(k))
    if missing:
        raise ValueError(f"consensus estimate missing keys: {', '.join(missing)}")
    if row["metric"] not in ("eps", "revenue"):
        raise ValueError("consensus estimate metric must be eps or revenue")
    if row["period_kind"] != "fiscal_year":
        raise ValueError("consensus estimate period_kind must be fiscal_year (v1)")
    count = row.get("analyst_count")
    if count is not None and (isinstance(count, bool) or not isinstance(count, int) or count < 0):
        raise ValueError("analyst_count must be a non-negative integer or null")
    payload = {key: row.get(key) for key in CONSENSUS_ESTIMATE_COLUMNS}
    for key in ("snapshot_date", "bar_date", "fiscal_period_end", "fetched_at"):
        if payload[key] is not None:
            payload[key] = str(payload[key])
    if _use_postgres():
        sql = """
        INSERT INTO consensus_estimates (
            ticker, snapshot_date, bar_date, metric, period_kind, relative_label,
            fiscal_period_end, fiscal_label, estimate_avg, estimate_low, estimate_high,
            analyst_count, year_ago_actual, growth, currency, source, fetched_at
        ) VALUES (
            %(ticker)s, %(snapshot_date)s, %(bar_date)s, %(metric)s, %(period_kind)s,
            %(relative_label)s, %(fiscal_period_end)s, %(fiscal_label)s, %(estimate_avg)s,
            %(estimate_low)s, %(estimate_high)s, %(analyst_count)s, %(year_ago_actual)s,
            %(growth)s, %(currency)s, %(source)s, %(fetched_at)s
        ) ON CONFLICT (ticker, snapshot_date, metric, fiscal_period_end, source) DO UPDATE SET
            bar_date=EXCLUDED.bar_date, relative_label=EXCLUDED.relative_label,
            fiscal_label=EXCLUDED.fiscal_label, estimate_avg=EXCLUDED.estimate_avg,
            estimate_low=EXCLUDED.estimate_low, estimate_high=EXCLUDED.estimate_high,
            analyst_count=EXCLUDED.analyst_count, year_ago_actual=EXCLUDED.year_ago_actual,
            growth=EXCLUDED.growth, currency=EXCLUDED.currency, fetched_at=EXCLUDED.fetched_at
        """
        with conn.cursor() as cur:
            cur.execute(sql, payload)
    else:
        conn.execute(
            """
            INSERT INTO consensus_estimates (
                ticker, snapshot_date, bar_date, metric, period_kind, relative_label,
                fiscal_period_end, fiscal_label, estimate_avg, estimate_low, estimate_high,
                analyst_count, year_ago_actual, growth, currency, source, fetched_at
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT (ticker, snapshot_date, metric, fiscal_period_end, source) DO UPDATE SET
                bar_date=excluded.bar_date, relative_label=excluded.relative_label,
                fiscal_label=excluded.fiscal_label, estimate_avg=excluded.estimate_avg,
                estimate_low=excluded.estimate_low, estimate_high=excluded.estimate_high,
                analyst_count=excluded.analyst_count, year_ago_actual=excluded.year_ago_actual,
                growth=excluded.growth, currency=excluded.currency, fetched_at=excluded.fetched_at
            """,
            tuple(payload[key] for key in CONSENSUS_ESTIMATE_COLUMNS),
        )
    if commit:
        conn.commit()


def upsert_manual_field(
    conn,
    ticker: str,
    field_name: str,
    value: str,
    *,
    source_note: str | None = None,
    commit: bool = True,
) -> None:
    """Idempotently store one human-reviewed checklist field (customer_concentration, backlog…).

    These are the checklist items yfinance cannot supply; they must be hand-entered
    from the primary filing. UNIQUE(ticker, field_name) makes re-entry an update.
    `source_note` records the filing the value came from (traceability is a hard rule).
    """
    ticker = ticker.upper().strip()
    field_name = field_name.strip()
    if not ticker or not field_name:
        raise ValueError("ticker and field_name are required")
    if value is None or not str(value).strip():
        raise ValueError("value must be a non-empty string (use a note, never blank)")

    if _use_postgres():
        sql = """
        INSERT INTO manual_fields (ticker, field_name, value, source_note, updated_at)
        VALUES (%(ticker)s, %(field_name)s, %(value)s, %(source_note)s, NOW())
        ON CONFLICT (ticker, field_name) DO UPDATE SET
            value=EXCLUDED.value,
            source_note=EXCLUDED.source_note,
            updated_at=EXCLUDED.updated_at
        """
        with conn.cursor() as cur:
            cur.execute(sql, {
                "ticker": ticker, "field_name": field_name,
                "value": str(value), "source_note": source_note,
            })
    else:
        conn.execute(
            """
            INSERT INTO manual_fields (ticker, field_name, value, source_note, updated_at)
            VALUES (?, ?, ?, ?, datetime('now'))
            ON CONFLICT (ticker, field_name) DO UPDATE SET
                value=excluded.value,
                source_note=excluded.source_note,
                updated_at=excluded.updated_at
            """,
            (ticker, field_name, str(value), source_note),
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
