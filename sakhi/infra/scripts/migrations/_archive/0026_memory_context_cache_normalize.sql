-- Normalize memory_context_cache entries to avoid string payloads breaking readers.

-- For any rows where entries is not a JSON array (e.g., stored as a string), reset to empty array.
UPDATE memory_context_cache
SET entries = '[]'::jsonb
WHERE jsonb_typeof(entries) IS DISTINCT FROM 'array';

-- Optional: drop stale rows if you want a fully clean cache.
-- DELETE FROM memory_context_cache;

