-- Build 68: Goals + Life Themes semantic model

CREATE TABLE IF NOT EXISTS brain_goals_themes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id UUID REFERENCES profiles(user_id) ON DELETE CASCADE,
    cluster_title TEXT,
    cluster_vector vector(1536),
    supporting_entry_ids UUID[],
    confidence DOUBLE PRECISION,
    time_window TEXT,
    emotional_tone JSONB,
    value_mapping JSONB,
    identity_alignment DOUBLE PRECISION,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_brain_goals_themes_person ON brain_goals_themes(person_id);
CREATE INDEX IF NOT EXISTS idx_brain_goals_themes_vector ON brain_goals_themes USING ivfflat (cluster_vector vector_cosine_ops) WITH (lists = 100);

