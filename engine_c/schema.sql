-- Engine C — Postgres schema
-- 每次 schema 變更加 migration 而非重跑（v0 先跑一次，schema 穩定後補 Alembic）

-- 每日財務快照：時間序列，每天一筆（yfinance ETL 寫入）
CREATE TABLE IF NOT EXISTS financial_snapshots (
    id              SERIAL PRIMARY KEY,
    ticker          VARCHAR(20)  NOT NULL,
    snapshot_date   DATE         NOT NULL,

    -- 獲利能力
    gross_margin        NUMERIC(8,4),   -- 0.xx 小數（如 0.4523 = 45.23%）
    operating_margin    NUMERIC(8,4),
    revenue_ttm         BIGINT,         -- 最近 12 個月總收入（USD）

    -- 稀釋分析
    shares_outstanding  BIGINT,         -- 流通股數

    -- Probe 財務韌性 / runway（原始 scalar，公式在 Decision Lab）
    cash_and_equivalents NUMERIC(20,2),
    total_debt           NUMERIC(20,2),
    free_cash_flow_ttm   NUMERIC(20,2),

    -- 估值
    ev_revenue          NUMERIC(10,4),  -- EV/Revenue 倍數
    pe_trailing         NUMERIC(10,4),
    pe_forward          NUMERIC(10,4),
    price               NUMERIC(12,4),  -- 當日收盤價

    -- 分析師共識
    analyst_target_mean  NUMERIC(12,4),
    analyst_target_high  NUMERIC(12,4),
    analyst_target_low   NUMERIC(12,4),
    analyst_target_count INTEGER,

    -- Metadata
    fetched_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),

    UNIQUE (ticker, snapshot_date)
);

CREATE INDEX IF NOT EXISTS idx_snapshots_ticker_date
    ON financial_snapshots (ticker, snapshot_date DESC);

-- 人工填入欄位：backlog、客戶集中度文字描述等 yfinance 無法自動取得的項目
CREATE TABLE IF NOT EXISTS manual_fields (
    id          SERIAL PRIMARY KEY,
    ticker      VARCHAR(20)  NOT NULL,
    field_name  VARCHAR(100) NOT NULL,
    value       TEXT,
    updated_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    source_note TEXT,                   -- 填入依據（如「COHR FY26Q3 法說會」）

    UNIQUE (ticker, field_name)
);

CREATE TABLE IF NOT EXISTS manual_observations (
    observation_id VARCHAR(64) PRIMARY KEY,
    ticker VARCHAR(32) NOT NULL,
    field_name VARCHAR(128) NOT NULL,
    value TEXT NOT NULL,
    source_ref TEXT NOT NULL,
    as_of TIMESTAMPTZ NOT NULL,
    author VARCHAR(255) NOT NULL,
    supersedes_id VARCHAR(64) REFERENCES manual_observations(observation_id),
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    payload_digest VARCHAR(64) NOT NULL UNIQUE
);

CREATE INDEX IF NOT EXISTS idx_manual_observation_field_time
    ON manual_observations (ticker, field_name, as_of, observation_id);

CREATE INDEX IF NOT EXISTS idx_manual_ticker
    ON manual_fields (ticker);

-- 客觀分析師覆蓋觀測。政策門檻與 crowding view 不落地，查詢時才套用。
CREATE TABLE IF NOT EXISTS consensus_coverage_observations (
    id               SERIAL PRIMARY KEY,
    ticker           VARCHAR(20)  NOT NULL,
    observation_date DATE         NOT NULL,
    analyst_count    INTEGER,
    source           VARCHAR(200) NOT NULL,
    data_status      VARCHAR(30)  NOT NULL,
    fetched_at       TIMESTAMPTZ  NOT NULL DEFAULT NOW(),

    UNIQUE (ticker, observation_date, source),
    CHECK (data_status IN ('observed', 'manual_required')),
    CHECK (
        (data_status = 'observed' AND analyst_count IS NOT NULL AND analyst_count >= 0)
        OR (data_status = 'manual_required' AND analyst_count IS NULL)
    )
);

CREATE INDEX IF NOT EXISTS idx_coverage_ticker_date
    ON consensus_coverage_observations (ticker, observation_date DESC);

-- 固定 beta universe 的 append-only point-in-time technical observations。
CREATE TABLE IF NOT EXISTS technical_observations (
    observation_id VARCHAR(64) PRIMARY KEY,
    benchmark_key VARCHAR(64) NOT NULL,
    provider_symbol VARCHAR(64) NOT NULL,
    session_date DATE,
    session_count INTEGER NOT NULL CHECK (session_count >= 0),
    data_status VARCHAR(32) NOT NULL CHECK (
        data_status IN ('observed', 'insufficient_history', 'unavailable', 'quarantined')
    ),
    close_raw NUMERIC(24,10),
    close_adjusted NUMERIC(24,10),
    return_1d NUMERIC(18,10),
    return_5d NUMERIC(18,10),
    return_20d NUMERIC(18,10),
    drawdown_252 NUMERIC(18,10),
    range_percentile_252 NUMERIC(18,10),
    -- rsi_14 / macd_* / sma_50_slope_5 是 2026-08-29 之前的 legacy 動能欄位：
    -- 隨 beta 技術訊號移除後新列不再寫入，既有列保留歷史值故不刪欄。
    rsi_14 NUMERIC(18,10),
    macd_line NUMERIC(24,10),
    macd_signal NUMERIC(24,10),
    macd_histogram NUMERIC(24,10),
    macd_histogram_slope NUMERIC(24,10),
    sma_20 NUMERIC(24,10),
    sma_50 NUMERIC(24,10),
    sma_200 NUMERIC(24,10),
    distance_sma_20 NUMERIC(18,10),
    distance_sma_50 NUMERIC(18,10),
    distance_sma_200 NUMERIC(18,10),
    sma_50_slope_5 NUMERIC(18,10),
    realized_vol_20 NUMERIC(18,10),
    realized_vol_60 NUMERIC(18,10),
    source TEXT NOT NULL,
    series_digest VARCHAR(64),
    fetched_at TIMESTAMPTZ NOT NULL,
    blockers_json TEXT NOT NULL,
    warnings_json TEXT NOT NULL,
    payload_digest VARCHAR(64) NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_technical_benchmark_session
    ON technical_observations (benchmark_key, session_date DESC, fetched_at DESC);
CREATE INDEX IF NOT EXISTS idx_technical_benchmark_fetched
    ON technical_observations (benchmark_key, fetched_at DESC);

-- 台股每月營收（ROADMAP Phase 6 / D15）。單位是新台幣**千元**，寫在 unit_scale 欄上
-- 而不是靠人記得；published_at 永遠 NULL（MOPS 的「出表日期」是產表日不是公告日），
-- 為什麼是 NULL 由 published_at_basis 自己宣告。
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

-- 台股季報股數（Phase 7 旁支開發，2026-10-05）：可重建 ETL 觀測；股數＝股本÷面額－庫藏股，以 權益÷每股淨值 交叉核對；
-- available_on＝一般業法定期限（上界）。SQLite 對應的建表住 engine_c/tw_share_capital.py（遷移 20261005_add_tw_share_capital.sql）。
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
        'cash', 'total_debt', 'shares_outstanding_cover',
        'equity_issued_value_quarter', 'equity_issued_value_annual')),
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

-- 募資文件清單（Phase 6 Step 6.6；migrations/20261003_add_equity_offering_filings.sql）
CREATE TABLE IF NOT EXISTS equity_offering_filings (
    accession VARCHAR(32) PRIMARY KEY,
    ticker VARCHAR(32) NOT NULL,
    cik VARCHAR(16) NOT NULL,
    form VARCHAR(16) NOT NULL,
    items TEXT,
    filed DATE NOT NULL,
    fetched_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_equity_offering_filings_ticker
    ON equity_offering_filings (ticker, filed);

CREATE TABLE IF NOT EXISTS equity_offering_checks (
    ticker VARCHAR(32) PRIMARY KEY,
    cik VARCHAR(16) NOT NULL,
    checked_at TIMESTAMPTZ NOT NULL,
    coverage_from DATE,
    recent_count INTEGER NOT NULL
);
