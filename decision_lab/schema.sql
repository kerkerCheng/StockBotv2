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
    decision_id      TEXT REFERENCES system_decisions(decision_id),
    event_type       TEXT NOT NULL,
    payload_json     TEXT NOT NULL,
    payload_digest   TEXT NOT NULL,
    effective_at     TEXT NOT NULL,
    corrects_paper_event_id TEXT REFERENCES paper_events(paper_event_id),
    approved_action_id TEXT,
    created_at       TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (decision_event_id, payload_digest)
);

CREATE TABLE IF NOT EXISTS system_decisions (
    decision_id       TEXT PRIMARY KEY,
    cohort_id         TEXT NOT NULL REFERENCES decision_cohorts(cohort_id),
    idempotency_key   TEXT NOT NULL UNIQUE,
    request_digest    TEXT NOT NULL,
    decision_digest   TEXT NOT NULL,
    context_digest    TEXT NOT NULL REFERENCES context_bundles(context_digest),
    coverage_assessment_id TEXT NOT NULL,
    policy_version    TEXT NOT NULL,
    calculator_version TEXT NOT NULL,
    payload_json      TEXT NOT NULL,
    effective_at      TEXT NOT NULL,
    created_at        TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (decision_id, decision_digest)
);

CREATE TABLE IF NOT EXISTS live_choices (
    choice_id          TEXT PRIMARY KEY,
    decision_id        TEXT NOT NULL REFERENCES system_decisions(decision_id),
    selected_weight    REAL NOT NULL CHECK (selected_weight >= 0),
    choice_type        TEXT NOT NULL CHECK (choice_type IN ('accepted', 'skipped', 'below_range', 'override')),
    reason             TEXT,
    approved_action_id TEXT,
    decided_at         TEXT NOT NULL,
    created_at         TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (decision_id, selected_weight, decided_at)
);

CREATE TABLE IF NOT EXISTS live_execution_reports (
    fill_id          TEXT PRIMARY KEY,
    decision_id      TEXT NOT NULL REFERENCES system_decisions(decision_id),
    execution_ref    TEXT NOT NULL UNIQUE,
    shares           REAL NOT NULL,
    price            REAL NOT NULL CHECK (price > 0),
    currency         TEXT NOT NULL,
    executed_at      TEXT NOT NULL,
    created_at       TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS prepared_actions (
    action_id        TEXT PRIMARY KEY,
    action_type      TEXT NOT NULL CHECK (action_type IN ('live_override', 'paper_correction', 'paper_reversal')),
    target_id        TEXT NOT NULL,
    payload_json     TEXT NOT NULL,
    action_digest    TEXT NOT NULL,
    prepared_at      TEXT NOT NULL,
    expires_at       TEXT NOT NULL,
    status           TEXT NOT NULL DEFAULT 'prepared' CHECK (status IN ('prepared', 'applied')),
    applied_at       TEXT,
    created_at       TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (action_type, target_id, action_digest)
);

CREATE TABLE IF NOT EXISTS probe_lifecycle_epochs (
    cohort_id        TEXT NOT NULL REFERENCES decision_cohorts(cohort_id),
    epoch            INTEGER NOT NULL CHECK (epoch > 0),
    status           TEXT NOT NULL CHECK (status IN ('active', 'review_required', 'promoted', 'rejected', 'expired', 'revised')),
    started_at       TEXT NOT NULL,
    review_due_at    TEXT,
    terminal_event_id TEXT,
    updated_at       TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (cohort_id, epoch)
);

CREATE TABLE IF NOT EXISTS probe_lifecycle_events (
    lifecycle_event_id TEXT PRIMARY KEY,
    cohort_id        TEXT NOT NULL,
    epoch            INTEGER NOT NULL,
    from_status      TEXT NOT NULL,
    to_status        TEXT NOT NULL,
    reason           TEXT NOT NULL,
    evidence_refs_json TEXT NOT NULL,
    event_digest     TEXT NOT NULL,
    effective_at     TEXT NOT NULL,
    created_at       TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (cohort_id, epoch) REFERENCES probe_lifecycle_epochs(cohort_id, epoch),
    UNIQUE (cohort_id, epoch, event_digest)
);

CREATE TABLE IF NOT EXISTS outcome_envelopes (
    outcome_id       TEXT PRIMARY KEY,
    cohort_id        TEXT NOT NULL,
    epoch            INTEGER NOT NULL,
    terminal_event_id TEXT NOT NULL UNIQUE REFERENCES probe_lifecycle_events(lifecycle_event_id),
    outcome_digest   TEXT NOT NULL,
    terminal_status  TEXT NOT NULL,
    claim_correctness TEXT NOT NULL CHECK (claim_correctness IN ('true', 'false', 'mixed', 'unknown')),
    market_return_status TEXT NOT NULL,
    absolute_return  REAL,
    benchmark_adjusted_return REAL,
    calculator_version TEXT,
    payload_json     TEXT NOT NULL,
    effective_at     TEXT NOT NULL,
    created_at       TEXT NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (cohort_id, epoch) REFERENCES probe_lifecycle_epochs(cohort_id, epoch),
    UNIQUE (cohort_id, epoch)
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
    coverage_status             TEXT NOT NULL DEFAULT 'not_assessed',
    updated_at                  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS holdings_confirmations (
    confirmation_id  TEXT PRIMARY KEY,
    sheet_digest     TEXT NOT NULL,
    confirmed_at     TEXT NOT NULL,
    created_at       TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (sheet_digest, confirmed_at)
);

CREATE TABLE IF NOT EXISTS context_bundles (
    context_id      TEXT PRIMARY KEY,
    cohort_id       TEXT NOT NULL REFERENCES decision_cohorts(cohort_id),
    context_digest  TEXT NOT NULL UNIQUE,
    evaluation_at   TEXT NOT NULL,
    payload_json    TEXT NOT NULL,
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS coverage_assessments (
    assessment_id       TEXT PRIMARY KEY,
    cohort_id           TEXT NOT NULL REFERENCES decision_cohorts(cohort_id),
    context_digest      TEXT NOT NULL REFERENCES context_bundles(context_digest),
    status              TEXT NOT NULL CHECK (status IN ('coverage_pending', 'analyzable')),
    blockers_json       TEXT NOT NULL,
    paper_blockers_json TEXT NOT NULL,
    live_blockers_json  TEXT NOT NULL,
    catalyst            TEXT NOT NULL,
    disproof            TEXT NOT NULL,
    expiry              TEXT NOT NULL,
    created_at          TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS research_work_orders (
    work_order_id       TEXT PRIMARY KEY,
    assessment_id       TEXT NOT NULL UNIQUE REFERENCES coverage_assessments(assessment_id),
    cohort_id           TEXT NOT NULL REFERENCES decision_cohorts(cohort_id),
    context_digest      TEXT NOT NULL REFERENCES context_bundles(context_digest),
    blockers_json       TEXT NOT NULL,
    expiry              TEXT NOT NULL,
    decision_relevance  INTEGER NOT NULL,
    falsifiability      INTEGER NOT NULL,
    information_value   INTEGER NOT NULL,
    status              TEXT NOT NULL DEFAULT 'queued',
    created_at          TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_decision_events_cohort_time
    ON decision_events (cohort_id, observed_at, event_id);
CREATE INDEX IF NOT EXISTS idx_paper_events_cohort_time
    ON paper_events (cohort_id, effective_at, paper_event_id);
INSERT INTO decision_store_meta (key, value)
VALUES ('schema_version', '5')
ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = datetime('now');
