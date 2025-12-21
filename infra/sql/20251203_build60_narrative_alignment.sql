-- Build 60: Narrative & Alignment state storage

ALTER TABLE IF EXISTS personal_model
    ADD COLUMN IF NOT EXISTS soul_narrative JSONB DEFAULT '{}'::jsonb,
    ADD COLUMN IF NOT EXISTS alignment_state JSONB DEFAULT '{}'::jsonb;

