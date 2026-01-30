-- Add created_at to micro_journey_cache for compatibility with callers that order by created_at.
-- Backfill from generated_at to preserve chronology.

ALTER TABLE micro_journey_cache
    ADD COLUMN IF NOT EXISTS created_at timestamptz;

UPDATE micro_journey_cache
SET created_at = COALESCE(created_at, generated_at, NOW())
WHERE created_at IS NULL;

ALTER TABLE micro_journey_cache
    ALTER COLUMN created_at SET NOT NULL,
    ALTER COLUMN created_at SET DEFAULT NOW();

CREATE INDEX IF NOT EXISTS micro_journey_cache_created_idx
    ON micro_journey_cache (created_at DESC);
