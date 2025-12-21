-- Build 52: Memory Context Cache foundation and content_hash support

-- Add content_hash and vector columns where missing
ALTER TABLE IF EXISTS journal_embeddings
    ADD COLUMN IF NOT EXISTS content_hash text,
    ADD COLUMN IF NOT EXISTS embedding_vec vector(1536);

ALTER TABLE IF EXISTS memory_short_term
    ADD COLUMN IF NOT EXISTS content_hash text,
    ADD COLUMN IF NOT EXISTS vector_vec vector(1536);

ALTER TABLE IF EXISTS memory_episodic
    ADD COLUMN IF NOT EXISTS content_hash text,
    ADD COLUMN IF NOT EXISTS vector_vec vector(1536);

-- Context cache table (empty row per person, merged_context_vector filled in Build 53)
CREATE TABLE IF NOT EXISTS memory_context_cache (
    person_id UUID PRIMARY KEY REFERENCES profiles(user_id) ON DELETE CASCADE,
    merged_context_vector vector(1536),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_memory_short_term_content_hash
    ON memory_short_term (person_id, content_hash);

CREATE INDEX IF NOT EXISTS idx_memory_episodic_content_hash
    ON memory_episodic (person_id, content_hash);

CREATE INDEX IF NOT EXISTS idx_journal_embeddings_content_hash
    ON journal_embeddings (content_hash);
