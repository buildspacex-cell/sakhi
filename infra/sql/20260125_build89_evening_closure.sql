-- Build 89: Evening Closure cache/state

BEGIN;

CREATE TABLE IF NOT EXISTS daily_closure_cache (
    id BIGSERIAL PRIMARY KEY,
    person_id UUID REFERENCES profiles(user_id) ON DELETE CASCADE,
    closure_date DATE NOT NULL,
    completed JSONB DEFAULT '[]'::jsonb,
    pending JSONB DEFAULT '[]'::jsonb,
    signals JSONB DEFAULT '{}'::jsonb,
    summary TEXT DEFAULT '',
    generated_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT daily_closure_cache_person_date UNIQUE (person_id, closure_date)
);

ALTER TABLE IF EXISTS personal_model
    ADD COLUMN IF NOT EXISTS closure_state JSONB DEFAULT '{}'::jsonb;

COMMIT;
