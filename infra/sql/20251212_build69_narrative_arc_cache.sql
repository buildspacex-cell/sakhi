-- Build 69: Narrative Arc Cache

BEGIN;

CREATE TABLE IF NOT EXISTS narrative_arc_cache (
    person_id UUID PRIMARY KEY REFERENCES profiles (user_id) ON DELETE CASCADE,
    life_arcs JSONB DEFAULT '{}'::jsonb,
    micro_arcs JSONB DEFAULT '{}'::jsonb,
    active_arcs JSONB DEFAULT '{}'::jsonb,
    arc_states JSONB DEFAULT '{}'::jsonb,
    arc_progress JSONB DEFAULT '{}'::jsonb,
    arc_conflicts JSONB DEFAULT '{}'::jsonb,
    arc_breakthroughs JSONB DEFAULT '{}'::jsonb,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_narrative_arc_cache_updated_at
    ON narrative_arc_cache (updated_at DESC);

COMMIT;

