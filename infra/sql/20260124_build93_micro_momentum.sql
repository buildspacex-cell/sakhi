-- Build 93: Micro-Momentum cache/state

BEGIN;

CREATE TABLE IF NOT EXISTS micro_momentum_cache (
    id BIGSERIAL PRIMARY KEY,
    person_id UUID REFERENCES profiles(user_id) ON DELETE CASCADE,
    nudge_date DATE NOT NULL,
    nudge TEXT DEFAULT '',
    reason TEXT DEFAULT '',
    generated_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT micro_momentum_person_date UNIQUE (person_id, nudge_date)
);

ALTER TABLE IF EXISTS personal_model
    ADD COLUMN IF NOT EXISTS micro_momentum_state JSONB DEFAULT '{}'::jsonb;

COMMIT;
