-- Build 57: Soul Engine Phase 3 schema support

ALTER TABLE IF EXISTS personal_model
    ADD COLUMN IF NOT EXISTS soul_state JSONB NOT NULL DEFAULT '{}'::jsonb;

ALTER TABLE IF EXISTS memory_short_term
    ADD COLUMN IF NOT EXISTS soul JSONB NOT NULL DEFAULT '{}'::jsonb;

ALTER TABLE IF EXISTS memory_episodic
    ADD COLUMN IF NOT EXISTS soul JSONB NOT NULL DEFAULT '{}'::jsonb;

-- Optional embedding slot for soul direction vectors
ALTER TABLE IF EXISTS memory_episodic
    ADD COLUMN IF NOT EXISTS soul_vector vector(1536);

-- Indexes to speed soul lookups
CREATE INDEX IF NOT EXISTS idx_personal_model_soul_state ON personal_model USING GIN (soul_state);
CREATE INDEX IF NOT EXISTS idx_memory_short_term_soul ON memory_short_term USING GIN (soul);
CREATE INDEX IF NOT EXISTS idx_memory_episodic_soul ON memory_episodic USING GIN (soul);
