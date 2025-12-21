-- Build 34 – Rhythm Engine foundation schema
-- Adds daily energy curves, chronotype, rhythm state, planner alignment, and raw rhythm events.

CREATE TABLE IF NOT EXISTS rhythm_daily_curve (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id UUID NOT NULL REFERENCES profiles (user_id) ON DELETE CASCADE,
    day_scope DATE NOT NULL DEFAULT CURRENT_DATE,
    slots JSONB NOT NULL,          -- 96 × 15-min windows with energy estimates
    confidence NUMERIC NOT NULL DEFAULT 0.0,
    source TEXT NOT NULL DEFAULT 'worker',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX IF NOT EXISTS rhythm_daily_curve_person_day_idx
    ON rhythm_daily_curve (person_id, day_scope);

CREATE TABLE IF NOT EXISTS rhythm_chronotype (
    person_id UUID PRIMARY KEY REFERENCES profiles (user_id) ON DELETE CASCADE,
    chronotype TEXT NOT NULL DEFAULT 'intermediate',
    score NUMERIC NOT NULL DEFAULT 0.0,
    evidence JSONB NOT NULL DEFAULT '{}'::jsonb,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS rhythm_state (
    person_id UUID PRIMARY KEY REFERENCES profiles (user_id) ON DELETE CASCADE,
    body_energy NUMERIC NOT NULL DEFAULT 0.5,
    mind_focus NUMERIC NOT NULL DEFAULT 0.5,
    emotion_tone TEXT NOT NULL DEFAULT 'neutral',
    fatigue_level NUMERIC NOT NULL DEFAULT 0.0,
    stress_level NUMERIC NOT NULL DEFAULT 0.0,
    next_peak TIMESTAMPTZ,
    next_lull TIMESTAMPTZ,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS rhythm_planner_alignment (
    person_id UUID NOT NULL REFERENCES profiles (user_id) ON DELETE CASCADE,
    horizon TEXT NOT NULL,                -- today | week | month
    recommendations JSONB NOT NULL,
    generated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (person_id, horizon)
);

CREATE TABLE IF NOT EXISTS rhythm_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id UUID NOT NULL REFERENCES profiles (user_id) ON DELETE CASCADE,
    event_ts TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    kind TEXT NOT NULL,
    payload JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS rhythm_events_person_ts_idx
    ON rhythm_events (person_id, event_ts DESC);
