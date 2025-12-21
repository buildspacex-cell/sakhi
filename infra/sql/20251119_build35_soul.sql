-- Build 35 – Soul Layer Engine schema
-- Values, identity signatures, purpose themes, life arcs, conflicts, persona evolution.

CREATE TABLE IF NOT EXISTS soul_values (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id UUID NOT NULL REFERENCES profiles (user_id) ON DELETE CASCADE,
    value_name TEXT NOT NULL,
    description TEXT,
    confidence NUMERIC NOT NULL DEFAULT 0.0,
    anchors JSONB NOT NULL DEFAULT '{}'::jsonb,
    evidence JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS soul_values_person_idx
    ON soul_values (person_id, value_name);

CREATE TABLE IF NOT EXISTS identity_signatures (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id UUID NOT NULL REFERENCES profiles (user_id) ON DELETE CASCADE,
    label TEXT NOT NULL,
    narrative TEXT,
    coherence NUMERIC NOT NULL DEFAULT 0.0,
    supporting_memories JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS identity_signatures_person_idx
    ON identity_signatures (person_id);

CREATE TABLE IF NOT EXISTS purpose_themes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id UUID NOT NULL REFERENCES profiles (user_id) ON DELETE CASCADE,
    theme TEXT NOT NULL,
    description TEXT,
    anchors JSONB NOT NULL DEFAULT '[]'::jsonb,
    momentum NUMERIC NOT NULL DEFAULT 0.0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS life_arcs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id UUID NOT NULL REFERENCES profiles (user_id) ON DELETE CASCADE,
    arc_name TEXT NOT NULL,
    start_scope TIMESTAMPTZ,
    end_scope TIMESTAMPTZ,
    summary TEXT,
    sentiment NUMERIC NOT NULL DEFAULT 0.0,
    tags TEXT[] DEFAULT '{}',
    narrative JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS life_arcs_person_idx
    ON life_arcs (person_id, start_scope);

CREATE TABLE IF NOT EXISTS conflict_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id UUID NOT NULL REFERENCES profiles (user_id) ON DELETE CASCADE,
    conflict_type TEXT NOT NULL,
    description TEXT,
    impact NUMERIC NOT NULL DEFAULT 0.0,
    tension_between JSONB NOT NULL DEFAULT '{}'::jsonb,
    resolution_hint TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS conflict_records_person_idx
    ON conflict_records (person_id, created_at DESC);

CREATE TABLE IF NOT EXISTS persona_evolution (
    person_id UUID PRIMARY KEY REFERENCES profiles (user_id) ON DELETE CASCADE,
    current_mode TEXT,
    drift_score NUMERIC NOT NULL DEFAULT 0.0,
    evolution_path JSONB NOT NULL DEFAULT '[]'::jsonb,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
