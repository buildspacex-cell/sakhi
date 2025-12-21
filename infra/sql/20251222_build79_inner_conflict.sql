-- Build 79: Inner Conflict cache/state

BEGIN;

CREATE TABLE IF NOT EXISTS inner_conflict_cache (
    person_id UUID PRIMARY KEY REFERENCES profiles(user_id) ON DELETE CASCADE,
    conflict_state JSONB DEFAULT '{}'::jsonb,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE IF EXISTS personal_model
    ADD COLUMN IF NOT EXISTS conflict_state JSONB DEFAULT '{}'::jsonb;

CREATE INDEX IF NOT EXISTS idx_inner_conflict_cache_updated_at
    ON inner_conflict_cache (updated_at DESC);

COMMIT;
