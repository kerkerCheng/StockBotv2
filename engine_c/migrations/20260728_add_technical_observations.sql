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
