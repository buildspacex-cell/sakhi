-- Build 66: Micro-Goals (Actionization Engine)

CREATE TABLE IF NOT EXISTS micro_goals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id UUID REFERENCES profiles(user_id) ON DELETE CASCADE,
    source TEXT NOT NULL,
    normalized TEXT NOT NULL,
    micro_steps JSONB NOT NULL,
    confidence DOUBLE PRECISION NOT NULL DEFAULT 0.7,
    blocked BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS micro_goals_person_idx ON micro_goals(person_id);
CREATE INDEX IF NOT EXISTS micro_goals_created_idx ON micro_goals(created_at);

