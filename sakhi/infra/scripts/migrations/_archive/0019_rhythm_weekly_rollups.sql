-- Rhythm weekly rollups: structured, deterministic capacity patterns (no prose).

CREATE TABLE IF NOT EXISTS rhythm_weekly_rollups (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id UUID NOT NULL REFERENCES profiles (user_id) ON DELETE CASCADE,
    week_start DATE NOT NULL,
    week_end DATE NOT NULL,
    rollup JSONB NOT NULL,
    confidence NUMERIC DEFAULT 0.0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS rhythm_weekly_rollups_person_week_idx
    ON rhythm_weekly_rollups (person_id, week_start);
