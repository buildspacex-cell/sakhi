-- facets v2: store sentiment/emotion/intent/entities/tags
ALTER TABLE journal_entries
  ADD COLUMN IF NOT EXISTS facets_v2 JSONB DEFAULT '{}'::jsonb;

-- link related entries (threads)
CREATE TABLE IF NOT EXISTS journal_links (
  src_id UUID REFERENCES journal_entries(id) ON DELETE CASCADE,
  dst_id UUID REFERENCES journal_entries(id) ON DELETE CASCADE,
  strength NUMERIC DEFAULT 0.0,
  PRIMARY KEY (src_id, dst_id)
);

-- theme aggregates (rollups)
CREATE TABLE IF NOT EXISTS journal_themes (
  id BIGSERIAL PRIMARY KEY,
  user_id UUID NOT NULL,
  theme TEXT NOT NULL,
  window TEXT NOT NULL,
  metrics JSONB NOT NULL,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- helpful indices
CREATE INDEX IF NOT EXISTS journal_entries_facets_v2_gin ON journal_entries USING GIN (facets_v2);
CREATE INDEX IF NOT EXISTS journal_links_src_idx ON journal_links(src_id);
CREATE INDEX IF NOT EXISTS journal_links_dst_idx ON journal_links(dst_id);
