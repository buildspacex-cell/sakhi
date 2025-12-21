-- Build 86: Empathy Engine state

BEGIN;

ALTER TABLE IF EXISTS personal_model
    ADD COLUMN IF NOT EXISTS empathy_state JSONB DEFAULT '{}'::jsonb;

COMMIT;
