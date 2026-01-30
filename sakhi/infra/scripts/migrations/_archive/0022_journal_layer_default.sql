-- Enforce journal_entries.layer has a deterministic value.
-- Any missing layers are backfilled to 'journal' and the column defaults to 'journal'.

UPDATE journal_entries
SET layer = 'journal'
WHERE layer IS NULL;

ALTER TABLE journal_entries
    ALTER COLUMN layer SET DEFAULT 'journal',
    ALTER COLUMN layer SET NOT NULL;
