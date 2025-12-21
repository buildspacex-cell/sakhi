-- Ensure optional metadata columns exist for the view
ALTER TABLE journal_entries
  ADD COLUMN IF NOT EXISTS title text;

-- View to adapt journal_* tables to the HybridRetriever interface
CREATE OR REPLACE VIEW journal_documents AS
SELECT
  je.id,
  je.user_id,
  je.content AS content,
  je.created_at,
  je.facets,
  je.title,
  emb.embedding
FROM journal_entries je
JOIN journal_embeddings emb ON emb.entry_id = je.id;

-- Helpful indexes for FTS part (if you want generated tsvector)
ALTER TABLE journal_entries
  ADD COLUMN IF NOT EXISTS fts tsvector
  GENERATED ALWAYS AS (to_tsvector('english', coalesce(content, ''))) STORED;

CREATE INDEX IF NOT EXISTS journal_entries_fts_gin ON journal_entries USING GIN (fts);
