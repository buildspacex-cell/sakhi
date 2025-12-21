-- Build 70: Unified Wellness Engine v1 cache

BEGIN;

CREATE TABLE IF NOT EXISTS wellness_state_cache (
    person_id UUID PRIMARY KEY REFERENCES profiles (user_id) ON DELETE CASCADE,
    body JSONB DEFAULT '{}'::jsonb,
    mind JSONB DEFAULT '{}'::jsonb,
    emotion JSONB DEFAULT '{}'::jsonb,
    energy JSONB DEFAULT '{}'::jsonb,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_wellness_state_cache_updated_at
    ON wellness_state_cache (updated_at DESC);

COMMIT;

