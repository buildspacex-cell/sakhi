-- Migration: 0032_episodic_state_vectors
-- Purpose: Add state_vector and guna_vector columns to memory_episodic for Friction Framework
-- Date: 2026-01-23

-- =============================================================================
-- STATE VECTOR (Dosha current state)
-- =============================================================================
-- Structure:
-- {
--   "dosha": {"vata": 0.35, "pitta": 0.40, "kapha": 0.25},
--   "elements": {"earth": 0.2, "water": 0.3, "fire": 0.3, "air": 0.15, "ether": 0.05},
--   "notes": ["Pitta elevated from stress indicators"],
--   "confidence": 0.75,
--   "computed_at": "2026-01-23T10:00:00Z"
-- }

ALTER TABLE memory_episodic
ADD COLUMN IF NOT EXISTS state_vector JSONB DEFAULT NULL;

COMMENT ON COLUMN memory_episodic.state_vector IS
'Dosha state vector computed from this entry. Contains vata/pitta/kapha scores for friction state calculation.';


-- =============================================================================
-- GUNA VECTOR (Operating Mode indicators)
-- =============================================================================
-- Structure:
-- {
--   "sattva": 0.45,
--   "rajas": 0.35,
--   "tamas": 0.20,
--   "computed_at": "2026-01-23T10:00:00Z"
-- }

ALTER TABLE memory_episodic
ADD COLUMN IF NOT EXISTS guna_vector JSONB DEFAULT NULL;

COMMENT ON COLUMN memory_episodic.guna_vector IS
'Guna state vector for Operating Mode (Clarity/Activation/Recovery) calculation.';


-- =============================================================================
-- INDEX for efficient friction state queries
-- =============================================================================
CREATE INDEX IF NOT EXISTS idx_memory_episodic_state_queries
ON memory_episodic (person_id, created_at DESC)
WHERE state_vector IS NOT NULL;
