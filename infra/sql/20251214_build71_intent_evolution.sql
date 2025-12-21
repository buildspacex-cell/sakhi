-- Build 71: Intent Evolution

BEGIN;

CREATE TABLE IF NOT EXISTS intent_evolution (
    person_id UUID REFERENCES profiles(user_id) ON DELETE CASCADE,
    intent_name TEXT,
    strength FLOAT DEFAULT 0,
    emotional_alignment FLOAT DEFAULT 0,
    trend TEXT DEFAULT 'stable',
    last_seen TIMESTAMPTZ DEFAULT NOW(),
    first_seen TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (person_id, intent_name)
);

CREATE INDEX IF NOT EXISTS idx_intent_evolution_last_seen
    ON intent_evolution (last_seen DESC);

COMMIT;

