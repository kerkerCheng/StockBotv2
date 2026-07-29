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
