-- Build 95: Focus Path cache/state

BEGIN;

CREATE TABLE IF NOT EXISTS focus_path_cache (
    id BIGSERIAL PRIMARY KEY,
    person_id UUID REFERENCES profiles(user_id) ON DELETE CASCADE,
    path_date DATE NOT NULL,
    anchor_step TEXT DEFAULT '',
    progress_step TEXT DEFAULT '',
    closure_step TEXT DEFAULT '',
    intent_source TEXT DEFAULT '',
    generated_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT focus_path_person_date UNIQUE (person_id, path_date)
);

ALTER TABLE IF EXISTS personal_model
    ADD COLUMN IF NOT EXISTS focus_path_state JSONB DEFAULT '{}'::jsonb;

COMMIT;
