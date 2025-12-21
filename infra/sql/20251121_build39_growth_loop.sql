-- Build 39 – Growth Loop schema (habit tracking, check-ins, task confidence)

CREATE TABLE IF NOT EXISTS growth_habits (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id UUID NOT NULL REFERENCES profiles (user_id) ON DELETE CASCADE,
    label TEXT NOT NULL,
    cadence JSONB NOT NULL DEFAULT '{}'::jsonb,
    intent_source TEXT,
    streak_count INTEGER NOT NULL DEFAULT 0,
    micro_progress NUMERIC NOT NULL DEFAULT 0.0,
    confidence NUMERIC NOT NULL DEFAULT 0.5,
    last_logged TIMESTAMPTZ,
    active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (person_id, label)
);

CREATE TABLE IF NOT EXISTS growth_habit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    habit_id UUID NOT NULL REFERENCES growth_habits (id) ON DELETE CASCADE,
    person_id UUID NOT NULL REFERENCES profiles (user_id) ON DELETE CASCADE,
    logged_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    micro_score NUMERIC NOT NULL DEFAULT 0.2,
    mood TEXT,
    note TEXT,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS growth_habit_logs_person_idx
    ON growth_habit_logs (person_id, logged_at DESC);

CREATE TABLE IF NOT EXISTS growth_daily_checkins (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id UUID NOT NULL REFERENCES profiles (user_id) ON DELETE CASCADE,
    checkin_date DATE NOT NULL DEFAULT CURRENT_DATE,
    energy NUMERIC,
    mood TEXT,
    reflection TEXT,
    plan_adjustment JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (person_id, checkin_date)
);

CREATE TABLE IF NOT EXISTS growth_task_confidence_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id UUID NOT NULL REFERENCES profiles (user_id) ON DELETE CASCADE,
    task_id UUID,
    task_label TEXT,
    confidence_before NUMERIC,
    confidence_after NUMERIC,
    delta NUMERIC,
    source TEXT,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS growth_task_confidence_person_idx
    ON growth_task_confidence_events (person_id, created_at DESC);
