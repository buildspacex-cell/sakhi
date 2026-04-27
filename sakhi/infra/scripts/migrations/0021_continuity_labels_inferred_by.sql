-- Migration 0021: Add enrichment columns to continuity_labels
-- Adds inferred_by, decision_state, epistemic_state, affective_scalar columns
-- required by the LLM enrichment pipeline (personal_taxonomy, adapters services).

ALTER TABLE continuity_labels
    ADD COLUMN IF NOT EXISTS inferred_by       TEXT             DEFAULT 'rule',
    ADD COLUMN IF NOT EXISTS decision_state    TEXT             DEFAULT NULL,
    ADD COLUMN IF NOT EXISTS epistemic_state   TEXT             DEFAULT NULL,
    ADD COLUMN IF NOT EXISTS affective_scalar  DOUBLE PRECISION DEFAULT NULL;
