-- Build 75: Narrative arcs per intent

BEGIN;

ALTER TABLE IF EXISTS personal_model
    ADD COLUMN IF NOT EXISTS narrative_arcs JSONB DEFAULT '[]'::jsonb;

COMMIT;

