-- Build 90: Morning Preview cache/state

BEGIN;

CREATE TABLE IF NOT EXISTS morning_preview_cache (
    id BIGSERIAL PRIMARY KEY,
    person_id UUID REFERENCES profiles(user_id) ON DELETE CASCADE,
    preview_date DATE NOT NULL,
    focus_areas JSONB DEFAULT '[]'::jsonb,
    key_tasks JSONB DEFAULT '[]'::jsonb,
    reminders JSONB DEFAULT '[]'::jsonb,
    rhythm_hint TEXT DEFAULT '',
    summary TEXT DEFAULT '',
    generated_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT morning_preview_person_date UNIQUE (person_id, preview_date)
);

ALTER TABLE IF EXISTS personal_model
    ADD COLUMN IF NOT EXISTS morning_preview_state JSONB DEFAULT '{}'::jsonb;

COMMIT;
