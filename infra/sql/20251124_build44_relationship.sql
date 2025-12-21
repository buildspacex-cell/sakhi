-- Build 44 – Relationship Model
-- Stores evolving trust/attunement/safety and optional preference patterns.

CREATE TABLE IF NOT EXISTS relationship_state (
    person_id UUID PRIMARY KEY REFERENCES profiles (user_id) ON DELETE CASCADE,
    trust_score NUMERIC NOT NULL DEFAULT 0.4,
    attunement_score NUMERIC NOT NULL DEFAULT 0.4,
    emotional_safety NUMERIC NOT NULL DEFAULT 0.5,
    closeness_stage TEXT NOT NULL DEFAULT 'Warm',
    preference_profile JSONB NOT NULL DEFAULT '{}'::jsonb,
    interaction_patterns JSONB NOT NULL DEFAULT '{}'::jsonb,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Optional cache on personal_model for quick reads.
ALTER TABLE personal_model
    ADD COLUMN IF NOT EXISTS relationship_state JSONB;

