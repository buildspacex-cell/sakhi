-- Build 42 – Narrative Engine (Soul Story)
-- Goal: store evolving personal narratives, identity evolution events, and season-of-life labels.

CREATE TABLE IF NOT EXISTS narrative_stories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id UUID NOT NULL REFERENCES profiles (user_id) ON DELETE CASCADE,
    narrative TEXT NOT NULL,
    season TEXT,
    patterns_success JSONB NOT NULL DEFAULT '[]'::jsonb,
    patterns_struggle JSONB NOT NULL DEFAULT '[]'::jsonb,
    identity_snapshot JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS narrative_stories_person_idx
    ON narrative_stories (person_id, created_at DESC);

CREATE TABLE IF NOT EXISTS identity_evolution_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id UUID NOT NULL REFERENCES profiles (user_id) ON DELETE CASCADE,
    label TEXT NOT NULL,
    summary TEXT,
    evidence JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS identity_evolution_person_idx
    ON identity_evolution_events (person_id, created_at DESC);

CREATE TABLE IF NOT EXISTS narrative_seasons (
    person_id UUID PRIMARY KEY REFERENCES profiles (user_id) ON DELETE CASCADE,
    season TEXT NOT NULL,
    hints JSONB NOT NULL DEFAULT '{}'::jsonb,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

