-- Build 92: Morning Momentum cache/state

BEGIN;

CREATE TABLE IF NOT EXISTS morning_momentum_cache (
    id BIGSERIAL PRIMARY KEY,
    person_id UUID REFERENCES profiles(user_id) ON DELETE CASCADE,
    momentum_date DATE NOT NULL,
    momentum_hint TEXT DEFAULT '',
    suggested_start TEXT DEFAULT '',
    reason TEXT DEFAULT '',
    generated_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT morning_momentum_person_date UNIQUE (person_id, momentum_date)
);

ALTER TABLE IF EXISTS personal_model
    ADD COLUMN IF NOT EXISTS morning_momentum_state JSONB DEFAULT '{}'::jsonb;

COMMIT;
