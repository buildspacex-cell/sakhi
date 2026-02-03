-- Intervention Plan Tracking Tables
-- A.4.1: Track long-term interventions with recurring schedules

-- Intervention plans (the recurring routine to track)
CREATE TABLE IF NOT EXISTS intervention_plans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id UUID NOT NULL REFERENCES persons(id),

    -- What to do
    intervention_type TEXT NOT NULL,  -- activity, food, mindfulness, sleep, social, avoidance, custom
    intervention_name TEXT NOT NULL,
    description TEXT,

    -- Schedule
    schedule_type TEXT NOT NULL DEFAULT 'daily',  -- daily, alternate_days, weekly, specific_days, as_needed
    schedule_days INT[],  -- For specific_days: 0=Mon, 6=Sun
    target_per_day INT DEFAULT 1,

    -- Duration
    start_date DATE NOT NULL DEFAULT CURRENT_DATE,
    end_date DATE,
    duration_days INT,

    -- Target symptom/dosha to correlate
    target_symptom TEXT,
    target_dosha TEXT,
    baseline_severity FLOAT,

    -- Tracking
    status TEXT DEFAULT 'active',  -- active, paused, completed, abandoned
    total_scheduled INT DEFAULT 0,
    total_completed INT DEFAULT 0,
    current_streak INT DEFAULT 0,
    longest_streak INT DEFAULT 0,
    notes TEXT,

    -- Source
    recommendation_id UUID,
    conversation_id UUID,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_intervention_plans_person ON intervention_plans(person_id);
CREATE INDEX IF NOT EXISTS idx_intervention_plans_active ON intervention_plans(person_id, status) WHERE status = 'active';
CREATE INDEX IF NOT EXISTS idx_intervention_plans_symptom ON intervention_plans(person_id, target_symptom);

-- Daily check-ins for each scheduled day
CREATE TABLE IF NOT EXISTS intervention_checkins (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    plan_id UUID NOT NULL REFERENCES intervention_plans(id) ON DELETE CASCADE,
    scheduled_date DATE NOT NULL,

    -- Status
    status TEXT DEFAULT 'pending',  -- pending, done, skipped, missed, partial
    completed_count INT DEFAULT 0,
    notes TEXT,

    -- Mood tracking (optional)
    mood_before FLOAT,  -- 0-1 scale
    mood_after FLOAT,

    -- Timestamps
    checked_in_at TIMESTAMPTZ,

    -- Nudge tracking
    nudge_sent BOOLEAN DEFAULT FALSE,
    nudge_sent_at TIMESTAMPTZ,

    created_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(plan_id, scheduled_date)
);

CREATE INDEX IF NOT EXISTS idx_checkins_plan ON intervention_checkins(plan_id);
CREATE INDEX IF NOT EXISTS idx_checkins_date ON intervention_checkins(scheduled_date);
CREATE INDEX IF NOT EXISTS idx_checkins_pending ON intervention_checkins(plan_id, scheduled_date)
    WHERE status = 'pending';

-- Nudges sent for interventions
CREATE TABLE IF NOT EXISTS intervention_nudges (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id UUID NOT NULL REFERENCES persons(id),
    plan_id UUID REFERENCES intervention_plans(id) ON DELETE CASCADE,
    checkin_id UUID REFERENCES intervention_checkins(id) ON DELETE CASCADE,

    nudge_type TEXT NOT NULL,  -- reminder, encouragement, streak, milestone, missed
    message TEXT NOT NULL,
    channel TEXT DEFAULT 'chat',  -- chat, push, email

    sent_at TIMESTAMPTZ DEFAULT NOW(),
    read_at TIMESTAMPTZ,
    acted_on BOOLEAN DEFAULT FALSE,
    acted_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_nudges_person ON intervention_nudges(person_id);
CREATE INDEX IF NOT EXISTS idx_nudges_plan ON intervention_nudges(plan_id);

-- Trigger to update updated_at
CREATE OR REPLACE FUNCTION update_intervention_plans_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS intervention_plans_timestamp ON intervention_plans;
CREATE TRIGGER intervention_plans_timestamp
    BEFORE UPDATE ON intervention_plans
    FOR EACH ROW
    EXECUTE FUNCTION update_intervention_plans_timestamp();
