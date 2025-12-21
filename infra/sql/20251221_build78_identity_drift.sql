-- Build 78: Identity Drift cache/state

BEGIN;

CREATE TABLE IF NOT EXISTS identity_drift_cache (
    person_id UUID PRIMARY KEY REFERENCES profiles(user_id) ON DELETE CASCADE,
    identity_state JSONB DEFAULT '{}'::jsonb,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE IF EXISTS personal_model
    ADD COLUMN IF NOT EXISTS identity_state JSONB DEFAULT '{}'::jsonb;

CREATE INDEX IF NOT EXISTS idx_identity_drift_cache_updated_at
    ON identity_drift_cache (updated_at DESC);

COMMIT;
