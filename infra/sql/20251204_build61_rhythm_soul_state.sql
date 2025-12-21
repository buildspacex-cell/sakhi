-- Build 61: Rhythm × Soul state storage

ALTER TABLE IF EXISTS personal_model
    ADD COLUMN IF NOT EXISTS rhythm_soul_state JSONB DEFAULT '{}'::jsonb;

