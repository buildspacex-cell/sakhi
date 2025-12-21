-- Planner weekly pressure rollup: numeric/categorical aggregates only (no task text).

CREATE TABLE IF NOT EXISTS planner_weekly_pressure (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id UUID NOT NULL REFERENCES profiles (user_id) ON DELETE CASCADE,
    week_start DATE NOT NULL,
    week_end DATE NOT NULL,
    pressure JSONB NOT NULL,
    confidence NUMERIC DEFAULT 0.0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS planner_weekly_pressure_person_week_idx
    ON planner_weekly_pressure (person_id, week_start);
