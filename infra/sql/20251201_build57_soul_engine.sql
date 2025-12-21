-- Build 57: Soul Engine Schema Expansion

-- 1. Add soul fields to memory_short_term
ALTER TABLE IF EXISTS memory_short_term
    ADD COLUMN IF NOT EXISTS soul JSONB DEFAULT '{}'::jsonb;

-- 2. Add soul fields to memory_episodic
ALTER TABLE IF EXISTS memory_episodic
    ADD COLUMN IF NOT EXISTS soul JSONB DEFAULT '{}'::jsonb;

-- 3. Expand personal_model with soul_state
ALTER TABLE IF EXISTS personal_model
    ADD COLUMN IF NOT EXISTS soul_state JSONB DEFAULT '{
      "core_values": [],
      "longing": [],
      "aversions": [],
      "identity_themes": [],
      "commitments": [],
      "shadow_patterns": [],
      "light_patterns": [],
      "confidence": 0.0,
      "updated_at": null
    }'::jsonb;

-- 4. Optional: soul embedding vector (1536-dim)
ALTER TABLE IF EXISTS personal_model
    ADD COLUMN IF NOT EXISTS soul_vector vector(1536);

-- 5. Indexes for soul access/performance
CREATE INDEX IF NOT EXISTS idx_memory_short_term_soul
    ON memory_short_term USING GIN (soul);

CREATE INDEX IF NOT EXISTS idx_memory_episodic_soul
    ON memory_episodic USING GIN (soul);

CREATE INDEX IF NOT EXISTS idx_personal_model_soul_state
    ON personal_model USING GIN (soul_state);
