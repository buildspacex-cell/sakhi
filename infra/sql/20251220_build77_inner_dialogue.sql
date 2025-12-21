-- Build 77: Inner Dialogue cache/state

BEGIN;

CREATE TABLE IF NOT EXISTS inner_dialogue_cache (
    person_id UUID PRIMARY KEY REFERENCES profiles(user_id) ON DELETE CASCADE,
    dialogue JSONB DEFAULT '{}'::jsonb,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE IF EXISTS personal_model
    ADD COLUMN IF NOT EXISTS inner_dialogue_state JSONB DEFAULT '{}'::jsonb;

COMMIT;

