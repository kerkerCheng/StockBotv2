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
