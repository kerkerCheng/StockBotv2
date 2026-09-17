-- 台股每月營收（ROADMAP Phase 6 / D15）。
-- 可重建的 ETL 觀測，不是 append-only judgment ledger（L10 的判準：今天重取一次拿得回來）。
-- published_at 永遠 NULL：MOPS 的「出表日期」是產表日不是公告日，
-- 不得用 ingest／retrieval 日期冒充 published_at（AGENTS.md）。
CREATE TABLE IF NOT EXISTS monthly_revenue_observations (
    observation_id VARCHAR(64) PRIMARY KEY,
    ticker VARCHAR(32) NOT NULL,
    market VARCHAR(8) NOT NULL CHECK (market IN ('twse', 'tpex')),
    company_code VARCHAR(16) NOT NULL,
    company_name TEXT,
    data_month VARCHAR(7) NOT NULL,
    revenue_current BIGINT,
    revenue_prev_month BIGINT,
    revenue_year_ago BIGINT,
    change_mom_pct NUMERIC(18,10),
    change_yoy_pct NUMERIC(18,10),
    cumulative_current BIGINT,
    cumulative_year_ago BIGINT,
    change_cumulative_pct NUMERIC(18,10),
    note TEXT,
    currency VARCHAR(8) NOT NULL,
    unit_scale INTEGER NOT NULL CHECK (unit_scale > 0),
    disclosure_deadline DATE NOT NULL,
    published_at TIMESTAMPTZ,
    published_at_basis VARCHAR(64) NOT NULL,
    report_date DATE,
    source TEXT NOT NULL,
    fetched_at TIMESTAMPTZ NOT NULL,
    payload_digest VARCHAR(64) NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_monthly_revenue_ticker_month
    ON monthly_revenue_observations (ticker, data_month DESC, fetched_at DESC);
