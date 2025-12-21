-- Build 64: Internal Decision Graph state

ALTER TABLE IF EXISTS personal_model
    ADD COLUMN IF NOT EXISTS internal_decision_graph JSONB DEFAULT '{}'::jsonb;

