-- Build 97: Mini-Flow rhythm slot extension

BEGIN;

ALTER TABLE IF EXISTS mini_flow_cache
    ADD COLUMN IF NOT EXISTS rhythm_slot TEXT;

ALTER TABLE IF EXISTS personal_model
    ADD COLUMN IF NOT EXISTS mini_flow_rhythm_slot TEXT;

COMMIT;
