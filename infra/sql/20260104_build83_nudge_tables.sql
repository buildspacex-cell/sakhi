-- Build 83: Preventive Nudge Engine v1

BEGIN;

CREATE TABLE IF NOT EXISTS nudge_log (
    id BIGSERIAL PRIMARY KEY,
    person_id UUID REFERENCES profiles(user_id) ON DELETE CASCADE,
    category TEXT NOT NULL,
    message TEXT NOT NULL,
    forecast_snapshot JSONB NOT NULL,
    sent_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE IF EXISTS personal_model
    ADD COLUMN IF NOT EXISTS nudge_state JSONB DEFAULT '{}'::jsonb;

COMMIT;
