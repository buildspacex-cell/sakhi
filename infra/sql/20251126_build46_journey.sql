-- Build 46 – Journey Renderer cache
-- Stores rendered journey snapshots (today/week/month) per person for quick reads.

CREATE TABLE IF NOT EXISTS journey_cache (
    person_id UUID NOT NULL REFERENCES profiles (user_id) ON DELETE CASCADE,
    scope TEXT NOT NULL, -- today | week | month | life
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (person_id, scope)
);

CREATE INDEX IF NOT EXISTS journey_cache_updated_idx
    ON journey_cache (updated_at DESC);
