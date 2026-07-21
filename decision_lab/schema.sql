PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS decision_store_meta (
    key         TEXT PRIMARY KEY,
    value       TEXT NOT NULL,
    updated_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS decision_cohorts (
    cohort_id        TEXT PRIMARY KEY,
    dedupe_key       TEXT NOT NULL UNIQUE,
    company_id       TEXT,
    research_ticker  TEXT,
    created_at       TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS decision_events (
    event_id        TEXT PRIMARY KEY,
    cohort_id       TEXT NOT NULL REFERENCES decision_cohorts(cohort_id),
    event_type      TEXT NOT NULL,
    payload_json    TEXT NOT NULL,
    payload_digest  TEXT NOT NULL,
    observed_at     TEXT NOT NULL,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (cohort_id, event_type, payload_digest, observed_at)
);

CREATE TABLE IF NOT EXISTS paper_events (
    paper_event_id   TEXT PRIMARY KEY,
    cohort_id        TEXT NOT NULL REFERENCES decision_cohorts(cohort_id),
    decision_event_id TEXT REFERENCES decision_events(event_id),
    event_type       TEXT NOT NULL,
    payload_json     TEXT NOT NULL,
    payload_digest   TEXT NOT NULL,
    effective_at     TEXT NOT NULL,
    created_at       TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (decision_event_id, payload_digest)
);

CREATE TABLE IF NOT EXISTS paper_position_projection (
    company_id       TEXT PRIMARY KEY,
    weight           REAL NOT NULL DEFAULT 0,
    source_event_id  TEXT REFERENCES paper_events(paper_event_id),
    updated_at       TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS shadow_observations (
    shadow_id   TEXT PRIMARY KEY,
    cohort_id   TEXT NOT NULL UNIQUE REFERENCES decision_cohorts(cohort_id),
    status      TEXT NOT NULL CHECK (status IN ('observed', 'missing', 'unavailable')),
    price       REAL,
    currency    TEXT,
    source      TEXT,
    as_of       TEXT,
    fetched_at  TEXT,
    created_at  TEXT NOT NULL DEFAULT (datetime('now')),
    CHECK (
        (status = 'observed' AND price IS NOT NULL AND price > 0
         AND currency IS NOT NULL AND source IS NOT NULL
         AND as_of IS NOT NULL AND fetched_at IS NOT NULL)
        OR (status IN ('missing', 'unavailable') AND price IS NULL)
    )
);

CREATE TABLE IF NOT EXISTS probe_projection (
    cohort_id                   TEXT PRIMARY KEY REFERENCES decision_cohorts(cohort_id),
    status                      TEXT NOT NULL CHECK (status IN ('active', 'promoted', 'rejected', 'expired')),
    evidence_admission_status   TEXT NOT NULL,
    source_registry_status      TEXT NOT NULL,
    research_priority           INTEGER NOT NULL DEFAULT 0,
    updated_at                  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_decision_events_cohort_time
    ON decision_events (cohort_id, observed_at, event_id);
CREATE INDEX IF NOT EXISTS idx_paper_events_cohort_time
    ON paper_events (cohort_id, effective_at, paper_event_id);

INSERT INTO decision_store_meta (key, value)
VALUES ('schema_version', '2')
ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = datetime('now');
