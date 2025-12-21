-- Build 82: Tone state cache in personal_model

BEGIN;

ALTER TABLE IF EXISTS personal_model
    ADD COLUMN IF NOT EXISTS tone_state JSONB DEFAULT '{}'::jsonb;

COMMIT;
