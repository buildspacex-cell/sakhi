BEGIN;

-- Backfill legacy journal rows that only populated user_id.
-- Continuity loaders already read (person_id OR user_id), but keeping both
-- columns aligned prevents future surface/compiler paths from depending on
-- that legacy fallback forever.
UPDATE journal_entries
SET person_id = user_id
WHERE person_id IS NULL
  AND user_id IS NOT NULL;

COMMIT;
