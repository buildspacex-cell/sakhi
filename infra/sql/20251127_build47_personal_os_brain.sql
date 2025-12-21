-- Build 47 – Personal OS Brain
-- Unified, constantly-updated snapshot of the user's current state.

CREATE TABLE IF NOT EXISTS personal_os_brain (
    person_id UUID PRIMARY KEY REFERENCES profiles (user_id) ON DELETE CASCADE,
    goals_state JSONB NOT NULL DEFAULT '{}'::jsonb,
    rhythm_state JSONB NOT NULL DEFAULT '{}'::jsonb,
    emotional_state JSONB NOT NULL DEFAULT '{}'::jsonb,
    identity_state JSONB NOT NULL DEFAULT '{}'::jsonb,
    relationship_state JSONB NOT NULL DEFAULT '{}'::jsonb,
    environment_state JSONB NOT NULL DEFAULT '{}'::jsonb,
    habits_state JSONB NOT NULL DEFAULT '{}'::jsonb,
    focus_state JSONB NOT NULL DEFAULT '{}'::jsonb,
    friction_points JSONB NOT NULL DEFAULT '[]'::jsonb,
    top_priorities JSONB NOT NULL DEFAULT '[]'::jsonb,
    life_chapter JSONB NOT NULL DEFAULT '{}'::jsonb,
    working_memory JSONB NOT NULL DEFAULT '{}'::jsonb,
    last_updated TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS personal_os_brain_updated_idx
    ON personal_os_brain (last_updated DESC);
