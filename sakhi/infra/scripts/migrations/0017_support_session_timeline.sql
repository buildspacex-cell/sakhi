-- 0017_support_session_timeline.sql
-- Time-bounded, user-consented support timeline telemetry (metadata-only).

CREATE TABLE IF NOT EXISTS support_debug_sessions (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    report_id          UUID NOT NULL REFERENCES support_debug_reports(id) ON DELETE CASCADE,
    person_id          UUID NOT NULL,
    support_code       TEXT NOT NULL,
    status             TEXT NOT NULL DEFAULT 'active',
    started_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_event_at      TIMESTAMPTZ,
    stopped_at         TIMESTAMPTZ,
    expires_at         TIMESTAMPTZ NOT NULL,
    event_count        INTEGER NOT NULL DEFAULT 0,
    client_context     JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT support_debug_sessions_status_check
        CHECK (status IN ('active', 'stopped', 'revoked', 'expired')),
    CONSTRAINT support_debug_sessions_event_count_check
        CHECK (event_count >= 0)
);

CREATE INDEX IF NOT EXISTS idx_support_debug_sessions_report_started
    ON support_debug_sessions (report_id, started_at DESC);

CREATE INDEX IF NOT EXISTS idx_support_debug_sessions_person_started
    ON support_debug_sessions (person_id, started_at DESC);

CREATE INDEX IF NOT EXISTS idx_support_debug_sessions_status_expires
    ON support_debug_sessions (status, expires_at DESC);

CREATE TABLE IF NOT EXISTS support_debug_events (
    id                 BIGSERIAL PRIMARY KEY,
    session_id         UUID NOT NULL REFERENCES support_debug_sessions(id) ON DELETE CASCADE,
    report_id          UUID NOT NULL REFERENCES support_debug_reports(id) ON DELETE CASCADE,
    person_id          UUID NOT NULL,
    support_code       TEXT NOT NULL,
    event_type         TEXT NOT NULL,
    event_name         TEXT NOT NULL,
    event_seq          INTEGER,
    event_at           TIMESTAMPTZ NOT NULL,
    screen             TEXT,
    route              TEXT,
    http_method        TEXT,
    http_status        INTEGER,
    request_id         TEXT,
    latency_ms         INTEGER,
    payload            JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT support_debug_events_type_check
        CHECK (event_type IN ('screen_view', 'action', 'api_start', 'api_end', 'ui_error')),
    CONSTRAINT support_debug_events_latency_check
        CHECK (latency_ms IS NULL OR latency_ms >= 0)
);

CREATE INDEX IF NOT EXISTS idx_support_debug_events_session_at
    ON support_debug_events (session_id, event_at DESC, id DESC);

CREATE INDEX IF NOT EXISTS idx_support_debug_events_report_at
    ON support_debug_events (report_id, event_at DESC, id DESC);

CREATE INDEX IF NOT EXISTS idx_support_debug_events_person_at
    ON support_debug_events (person_id, event_at DESC, id DESC);
