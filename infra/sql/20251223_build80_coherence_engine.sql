-- Build 80: Coherence Engine cache/state

BEGIN;

CREATE TABLE IF NOT EXISTS coherence_cache (
    person_id UUID PRIMARY KEY REFERENCES profiles(user_id) ON DELETE CASCADE,
    coherence_state JSONB DEFAULT '{}'::jsonb,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE IF EXISTS personal_model
    ADD COLUMN IF NOT EXISTS coherence_state JSONB DEFAULT '{}'::jsonb;

CREATE INDEX IF NOT EXISTS idx_coherence_cache_updated_at
    ON coherence_cache (updated_at DESC);

COMMIT;
