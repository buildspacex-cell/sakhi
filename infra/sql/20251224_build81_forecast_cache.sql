-- Build 81: Forecast cache/state

BEGIN;

CREATE TABLE IF NOT EXISTS forecast_cache (
    person_id UUID PRIMARY KEY REFERENCES profiles(user_id) ON DELETE CASCADE,
    forecast_state JSONB DEFAULT '{}'::jsonb,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE IF EXISTS personal_model
    ADD COLUMN IF NOT EXISTS forecast_state JSONB DEFAULT '{}'::jsonb;

CREATE INDEX IF NOT EXISTS idx_forecast_cache_updated_at
    ON forecast_cache (updated_at DESC);

COMMIT;
