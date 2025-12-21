-- Build 84: Energy-Aware Task Routing v1

BEGIN;

CREATE TABLE IF NOT EXISTS task_routing_cache (
    task_id UUID PRIMARY KEY,
    person_id UUID REFERENCES profiles(user_id) ON DELETE CASCADE,
    category TEXT NOT NULL,
    recommended_window TEXT,
    reason TEXT,
    forecast_snapshot JSONB,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE IF EXISTS tasks
    ADD COLUMN IF NOT EXISTS routing_state JSONB DEFAULT '{}'::jsonb;

COMMIT;
