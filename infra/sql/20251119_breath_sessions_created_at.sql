-- Ensure breath_sessions rows carry timestamps for rhythm ingestion
ALTER TABLE breath_sessions
    ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT NOW();

CREATE INDEX IF NOT EXISTS breath_sessions_person_created_idx
    ON breath_sessions (person_id, created_at DESC);

