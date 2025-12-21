-- Build 88: Daily Reflection cache + personal_model state

BEGIN;

CREATE TABLE IF NOT EXISTS daily_reflection_cache (
    person_id UUID REFERENCES profiles(user_id) ON DELETE CASCADE,
    reflection_date DATE NOT NULL,
    summary JSONB NOT NULL,
    generated_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (person_id, reflection_date)
);

ALTER TABLE IF EXISTS personal_model
    ADD COLUMN IF NOT EXISTS daily_reflection_state JSONB DEFAULT '{}'::jsonb;

COMMIT;
