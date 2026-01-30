-- Enforce immutability of raw evidence text in journal_entries.
-- journal_entries is an immutable evidence table.
-- Raw user-authored text must never be mutated after insertion.
-- All interpretation belongs in downstream inference layers.

CREATE OR REPLACE FUNCTION prevent_journal_content_update()
RETURNS trigger AS $$
BEGIN
  IF NEW.content IS DISTINCT FROM OLD.content THEN
    RAISE EXCEPTION 'journal_entries.content is immutable after insert';
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_journal_content_immutable ON journal_entries;
CREATE TRIGGER trg_journal_content_immutable
BEFORE UPDATE ON journal_entries
FOR EACH ROW
EXECUTE FUNCTION prevent_journal_content_update();
