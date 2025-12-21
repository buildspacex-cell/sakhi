-- Build 74: Multi-Lens Coherence report

BEGIN;

ALTER TABLE IF EXISTS personal_model
    ADD COLUMN IF NOT EXISTS coherence_report JSONB DEFAULT '{}'::jsonb;

COMMIT;

