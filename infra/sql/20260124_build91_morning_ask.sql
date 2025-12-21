-- Build 91: Morning Ask cache/state

BEGIN;

CREATE TABLE IF NOT EXISTS morning_ask_cache (
    id BIGSERIAL PRIMARY KEY,
    person_id UUID REFERENCES profiles(user_id) ON DELETE CASCADE,
    ask_date DATE NOT NULL,
    question TEXT DEFAULT '',
    reason TEXT DEFAULT '',
    generated_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT morning_ask_person_date UNIQUE (person_id, ask_date)
);

ALTER TABLE IF EXISTS personal_model
    ADD COLUMN IF NOT EXISTS morning_ask_state JSONB DEFAULT '{}'::jsonb;

COMMIT;
