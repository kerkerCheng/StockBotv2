-- 機械歷史表（Phase 3 Step 3.2）：價格 raw／adjusted＋分割事件、EDGAR 基本面（每份申報各一列）。
-- 可重建的 ETL 觀測，不是 append-only judgment ledger（L10：今天重取一次拿得回來）。
-- 財報數字的可用日是 filed（EDGAR 申報日），不是會計期末、更不是 fetched_at（INV-6）；
-- 讀取端 as-of T 對每個 period_end 取 filed <= T 的最新一列（engine_c/history.py）。
-- SQLite 對應的建表住 engine_c/history_backfill.py::ensure_history_schema（兩邊欄位與約束一致）。
CREATE TABLE IF NOT EXISTS price_history (
    ticker VARCHAR(32) NOT NULL,
    bar_date DATE NOT NULL,
    close_raw NUMERIC(24,8),
    close_adjusted NUMERIC(24,8),
    quote_unit VARCHAR(8),
    settlement_currency VARCHAR(8),
    source TEXT NOT NULL,
    fetched_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (ticker, bar_date)
);

CREATE TABLE IF NOT EXISTS corporate_actions (
    ticker VARCHAR(32) NOT NULL,
    action_date DATE NOT NULL,
    kind VARCHAR(16) NOT NULL CHECK (kind IN ('split')),
    ratio NUMERIC(24,10) NOT NULL CHECK (ratio > 0),
    source TEXT NOT NULL,
    fetched_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (ticker, action_date, kind)
);

CREATE TABLE IF NOT EXISTS fundamental_history (
    ticker VARCHAR(32) NOT NULL,
    metric VARCHAR(40) NOT NULL CHECK (metric IN (
        'revenue_quarter', 'revenue_annual', 'operating_income_quarter', 'operating_income_annual',
        'cash', 'total_debt', 'shares_outstanding_cover')),
    period_start DATE,
    period_end DATE NOT NULL,
    filed DATE NOT NULL,
    accession VARCHAR(32) NOT NULL,
    form VARCHAR(16) NOT NULL,
    value NUMERIC(28,6) NOT NULL,
    currency VARCHAR(16) NOT NULL,
    unit_scale INTEGER NOT NULL DEFAULT 1 CHECK (unit_scale > 0),
    derived TEXT,
    tag TEXT NOT NULL,
    source TEXT NOT NULL,
    fetched_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (ticker, metric, period_end, accession)
);

CREATE INDEX IF NOT EXISTS idx_fundamental_history_asof
    ON fundamental_history (ticker, metric, period_end, filed);
