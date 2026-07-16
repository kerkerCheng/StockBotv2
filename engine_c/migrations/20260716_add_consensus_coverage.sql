-- Add raw analyst-coverage observations to an existing Engine C Postgres database.
-- Safe to rerun: every DDL operation is idempotent.

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
