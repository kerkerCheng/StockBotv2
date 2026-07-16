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
    CHECK (analyst_count IS NULL OR analyst_count >= 0)
);

CREATE INDEX IF NOT EXISTS idx_coverage_ticker_date
    ON consensus_coverage_observations (ticker, observation_date DESC);
