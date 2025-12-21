-- Build 76: Pattern Sense cache

BEGIN;

CREATE TABLE IF NOT EXISTS pattern_sense_cache (
    person_id UUID PRIMARY KEY REFERENCES profiles(user_id) ON DELETE CASCADE,
    patterns JSONB DEFAULT '{}'::jsonb,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE IF EXISTS personal_model
    ADD COLUMN IF NOT EXISTS pattern_sense JSONB DEFAULT '{}'::jsonb;

CREATE INDEX IF NOT EXISTS idx_pattern_sense_cache_updated_at
    ON pattern_sense_cache (updated_at DESC);

COMMIT;

