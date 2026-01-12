-- Ensure memory_context_cache supports per-window upserts.

ALTER TABLE IF EXISTS memory_context_cache
    ADD COLUMN IF NOT EXISTS window_kind TEXT NOT NULL DEFAULT 'default';

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'memory_context_cache_person_window_uk'
    ) THEN
        ALTER TABLE memory_context_cache
            ADD CONSTRAINT memory_context_cache_person_window_uk UNIQUE (person_id, window_kind);
    END IF;
END$$;

