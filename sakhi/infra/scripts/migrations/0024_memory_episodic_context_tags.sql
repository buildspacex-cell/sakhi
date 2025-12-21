-- Ensure memory_episodic has a context_tags column for weekly signals aggregation.

ALTER TABLE IF EXISTS memory_episodic
    ADD COLUMN IF NOT EXISTS context_tags JSONB DEFAULT '[]'::jsonb;

-- No backfill needed; leave existing rows as empty array when absent.
