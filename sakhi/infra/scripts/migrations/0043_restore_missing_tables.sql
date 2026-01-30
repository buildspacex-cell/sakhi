-- Migration 0043: Restore missing tables needed by code
-- Date: 2026-01-28
--
-- These tables are referenced in code but were either never created
-- or were dropped prematurely.

-- =============================================================================
-- FACTS TABLE (used by knowledge_gap.py and consolidate.py)
-- =============================================================================
CREATE TABLE IF NOT EXISTS facts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id UUID NOT NULL ,
    scope TEXT NOT NULL,
    key TEXT NOT NULL,
    value JSONB NOT NULL DEFAULT '{}',
    confidence FLOAT DEFAULT 0.5,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    embedding vector(1536),
    UNIQUE (person_id, scope, key)
);

CREATE INDEX IF NOT EXISTS idx_facts_person_id ON facts(person_id);
CREATE INDEX IF NOT EXISTS idx_facts_scope ON facts(scope);

COMMENT ON TABLE facts IS 'Extracted facts/knowledge about a person derived from their conversations';

-- =============================================================================
-- CONTEXT_RECALLS TABLE (used by deep_context.py)
-- =============================================================================
CREATE TABLE IF NOT EXISTS context_recalls (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id UUID NOT NULL ,
    turn_id UUID,
    thread_id UUID,
    stitched_summary TEXT,
    compact JSONB DEFAULT '{}',
    vectors JSONB DEFAULT '{}',
    signals JSONB DEFAULT '{}',
    confidence FLOAT DEFAULT 0.5,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_context_recalls_person_id ON context_recalls(person_id);
CREATE INDEX IF NOT EXISTS idx_context_recalls_created_at ON context_recalls(person_id, created_at DESC);

COMMENT ON TABLE context_recalls IS 'Cached deep context recall results for conversations';

-- =============================================================================
-- ELEMENTAL_SUMMARY_WEEKLY (used by ayurvedic_pipeline and lab routes)
-- =============================================================================
CREATE TABLE IF NOT EXISTS elemental_summary_weekly (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id UUID NOT NULL ,
    week_start DATE NOT NULL,
    elements JSONB DEFAULT '{}',
    dosha_balance JSONB DEFAULT '{}',
    signals_count INT DEFAULT 0,
    confidence FLOAT DEFAULT 0.5,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (person_id, week_start)
);

CREATE INDEX IF NOT EXISTS idx_elemental_summary_weekly_person_id ON elemental_summary_weekly(person_id);

COMMENT ON TABLE elemental_summary_weekly IS 'Weekly summary of elemental/dosha balance from Ayurvedic pipeline';
