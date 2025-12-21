-- Build 73: Daily Alignment cache

BEGIN;

CREATE TABLE IF NOT EXISTS daily_alignment_cache (
    person_id UUID PRIMARY KEY REFERENCES profiles(user_id) ON DELETE CASCADE,
    alignment_map JSONB DEFAULT '{}'::jsonb,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_daily_alignment_cache_updated_at
    ON daily_alignment_cache (updated_at DESC);

COMMIT;

