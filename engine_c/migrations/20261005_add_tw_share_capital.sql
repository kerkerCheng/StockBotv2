-- 台股季報股數（Phase 7 旁支開發「台股歷史股數」，2026-10-05）。
-- 可重建的 ETL 觀測，不是 append-only judgment ledger（L10：MOPS 按季永久可查，今天重取一次拿得回來）。
-- 股數＝股本×1000÷面額 10 元－庫藏股；以 權益÷每股參考淨值 交叉核對，差 >2% 的列 cross_check_status='mismatch'、讀取端不用。
-- available_on＝一般業法定期限（季後 45 日、年報 3 個月）的上界，不是實際公告日、更不是 fetched_at（INV-6）。
-- SQLite 對應的建表住 engine_c/tw_share_capital.py::ensure_share_capital_schema（兩邊欄位與約束一致）。
CREATE TABLE IF NOT EXISTS tw_share_capital_observations (
    observation_id VARCHAR(64) PRIMARY KEY,
    ticker VARCHAR(32) NOT NULL,
    market VARCHAR(8) NOT NULL CHECK (market IN ('twse', 'tpex')),
    company_code VARCHAR(16) NOT NULL,
    company_name TEXT,
    fiscal_year INTEGER NOT NULL,
    quarter INTEGER NOT NULL CHECK (quarter BETWEEN 1 AND 4),
    period_end DATE NOT NULL,
    template VARCHAR(32) NOT NULL,
    share_capital BIGINT,
    equity_parent BIGINT,
    equity_total BIGINT,
    non_controlling BIGINT,
    bvps NUMERIC(18,6),
    treasury_shares BIGINT,
    par_value INTEGER NOT NULL,
    shares_issued BIGINT,
    shares_outstanding BIGINT,
    shares_implied_by_equity BIGINT,
    cross_check_diff NUMERIC(18,10),
    cross_check_status VARCHAR(16) NOT NULL,
    cross_check_reason TEXT,
    currency VARCHAR(8) NOT NULL,
    unit_scale INTEGER NOT NULL CHECK (unit_scale > 0),
    available_on DATE NOT NULL,
    available_on_basis VARCHAR(64) NOT NULL,
    source TEXT NOT NULL,
    fetched_at TIMESTAMPTZ NOT NULL,
    payload_digest VARCHAR(64) NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_tw_share_capital_ticker_period
    ON tw_share_capital_observations (ticker, period_end DESC, fetched_at DESC);
