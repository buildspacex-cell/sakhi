CREATE TABLE IF NOT EXISTS mental_impression (
    id TEXT PRIMARY KEY,
    person_id UUID NOT NULL REFERENCES persons(id) ON DELETE CASCADE,
    source_event_ids TEXT[] NOT NULL,
    intents JSONB,
    beliefs JSONB,
    open_loops JSONB,
    version TEXT NOT NULL DEFAULT 'intel_1',
    ts TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS emotional_signature (
    id TEXT PRIMARY KEY,
    person_id UUID NOT NULL REFERENCES persons(id) ON DELETE CASCADE,
    from_mental_ids TEXT[] NOT NULL,
    affect JSONB,
    primary_emotions TEXT[],
    needs TEXT[],
    version TEXT NOT NULL DEFAULT 'intel_1',
    ts TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS energetic_state (
    id TEXT PRIMARY KEY,
    person_id UUID NOT NULL REFERENCES persons(id) ON DELETE CASCADE,
    from_emotional_ids TEXT[] NOT NULL,
    quality TEXT CHECK (quality IN ('expansive', 'contracted', 'scattered', 'grounded')),
    rhythm_tags TEXT[],
    stability NUMERIC,
    version TEXT NOT NULL DEFAULT 'intel_1',
    ts TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS insight (
    id TEXT PRIMARY KEY,
    person_id UUID NOT NULL REFERENCES persons(id) ON DELETE CASCADE,
    from_ids TEXT[] NOT NULL,
    kind TEXT NOT NULL CHECK (kind IN ('reflection', 'nudge', 'plan', 'risk')),
    message TEXT NOT NULL,
    why JSONB,
    actions JSONB,
    confidence NUMERIC DEFAULT 0.6,
    ts TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_aw_edge_src ON aw_edge(src_id);
CREATE INDEX IF NOT EXISTS idx_aw_edge_dst ON aw_edge(dst_id);
