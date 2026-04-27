-- Migration 0018: Continuity personal taxonomy + enrichment columns
-- Adds user-specific anchor discovery table and enrichment columns on continuity_labels.
-- Part of: continuity engine gap-closing plan (Phase 1 + 2.2)

-- ── Personal taxonomy ──────────────────────────────────────────────────────────
-- Stores anchors discovered via LLM enrichment for topics outside the hardcoded
-- taxonomy. Grows per-user as they discuss topics the lexical classifier cannot
-- confidently anchor.
CREATE TABLE IF NOT EXISTS continuity_personal_taxonomy (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id       TEXT NOT NULL,
    anchor          TEXT NOT NULL,              -- canonicalised anchor key
    label           TEXT NOT NULL,              -- human-readable label
    entry_count     INTEGER NOT NULL DEFAULT 1, -- number of entries that contributed
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT continuity_personal_taxonomy_person_anchor_uq
        UNIQUE (person_id, anchor)
);

CREATE INDEX IF NOT EXISTS idx_cont_personal_taxonomy_person
    ON continuity_personal_taxonomy (person_id);

-- ── New columns on continuity_labels ──────────────────────────────────────────
-- epistemic_state: tracks belief/certainty state alongside decision state
ALTER TABLE continuity_labels
    ADD COLUMN IF NOT EXISTS epistemic_state TEXT DEFAULT NULL;

-- affective_scalar: emotion-derived numeric signal (-1.0 to +1.0)
ALTER TABLE continuity_labels
    ADD COLUMN IF NOT EXISTS affective_scalar FLOAT DEFAULT NULL;

-- inferred_by: 'lexical' (default) or 'llm' — how the anchor was determined
ALTER TABLE continuity_labels
    ADD COLUMN IF NOT EXISTS inferred_by TEXT NOT NULL DEFAULT 'lexical';
