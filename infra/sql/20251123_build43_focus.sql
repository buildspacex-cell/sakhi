-- Build 43 – Focus + Flow Mode tables
-- focus_sessions: a row per active/ended session
-- focus_events: per-tick nudges/breaks/updates tied to a session

CREATE TABLE IF NOT EXISTS focus_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id UUID NOT NULL REFERENCES profiles (user_id) ON DELETE CASCADE,
    task_id UUID REFERENCES planned_items (id) ON DELETE SET NULL,
    mode TEXT DEFAULT 'deep',
    start_time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    end_time TIMESTAMPTZ,
    estimated_duration INTEGER, -- minutes
    actual_duration INTEGER,
    completion_score NUMERIC,
    session_quality JSONB NOT NULL DEFAULT '{}'::jsonb,
    session_start_state JSONB NOT NULL DEFAULT '{}'::jsonb,
    status TEXT NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS focus_sessions_person_idx
    ON focus_sessions (person_id, start_time DESC);

CREATE INDEX IF NOT EXISTS focus_sessions_status_idx
    ON focus_sessions (status);

CREATE TABLE IF NOT EXISTS focus_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES focus_sessions (id) ON DELETE CASCADE,
    ts TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    event_type TEXT NOT NULL,
    content JSONB NOT NULL DEFAULT '{}'::jsonb,
    rhythm_state JSONB NOT NULL DEFAULT '{}'::jsonb,
    task_state JSONB NOT NULL DEFAULT '{}'::jsonb,
    emotion_state JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS focus_events_session_idx
    ON focus_events (session_id, ts DESC);
