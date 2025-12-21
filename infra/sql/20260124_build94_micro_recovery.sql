-- Build 94: Micro-Recovery cache/state

BEGIN;

CREATE TABLE IF NOT EXISTS micro_recovery_cache (
    id BIGSERIAL PRIMARY KEY,
    person_id UUID REFERENCES profiles(user_id) ON DELETE CASCADE,
    recovery_date DATE NOT NULL,
    nudge TEXT DEFAULT '',
    reason TEXT DEFAULT '',
    generated_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT micro_recovery_person_date UNIQUE (person_id, recovery_date)
);

ALTER TABLE IF EXISTS personal_model
    ADD COLUMN IF NOT EXISTS micro_recovery_state JSONB DEFAULT '{}'::jsonb;

COMMIT;
