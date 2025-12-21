-- Build 45 – Environmental Context Integration
-- Lightweight, user-controlled context for planning/rhythm/tone.

CREATE TABLE IF NOT EXISTS environment_context (
    person_id UUID PRIMARY KEY REFERENCES profiles (user_id) ON DELETE CASCADE,
    weather JSONB NOT NULL DEFAULT '{}'::jsonb,          -- e.g., {"temp_c": 30, "condition": "Rain"}
    calendar_blocks JSONB NOT NULL DEFAULT '[]'::jsonb,  -- summarized events for today
    day_cycle TEXT,                                      -- morning | afternoon | evening | night
    weekend_flag BOOLEAN NOT NULL DEFAULT FALSE,
    holiday_flag BOOLEAN NOT NULL DEFAULT FALSE,
    travel_flag BOOLEAN NOT NULL DEFAULT FALSE,
    environment_tags JSONB NOT NULL DEFAULT '[]'::jsonb, -- e.g., ["rain", "busy_week"]
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS environment_context_updated_idx
    ON environment_context (updated_at DESC);
