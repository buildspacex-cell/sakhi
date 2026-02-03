-- Long-Running Mission Tables
-- Phase H: Life Missions that span weeks or months (Twitter brand, learning, fitness, etc.)
-- Architecture: See docs/LONG_RUNNING_TASKS.md for full specification

-- ============================================================================
-- 1. MISSIONS - Top-level goals that span months
-- ============================================================================
CREATE TABLE IF NOT EXISTS long_running_missions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id UUID NOT NULL REFERENCES persons(id),

    -- Mission definition
    title TEXT NOT NULL,                    -- "Build Twitter personal brand"
    description TEXT,                       -- Detailed goal description
    category TEXT,                          -- career, health, learning, creative, relationships
    success_criteria JSONB,                 -- Measurable outcomes

    -- Plan document (markdown, human-readable)
    plan_document TEXT,                     -- Full markdown plan

    -- Timeline
    target_end_date DATE,                   -- When to achieve by
    actual_end_date DATE,                   -- When actually completed

    -- Status
    status TEXT DEFAULT 'active',           -- active, paused, completed, abandoned
    health TEXT DEFAULT 'on_track',         -- on_track, at_risk, behind, ahead

    -- Learning
    strategy_notes TEXT,                    -- High-level approach
    lessons_learned JSONB,                  -- What we've learned

    -- Metrics
    progress_pct INTEGER DEFAULT 0,         -- 0-100
    metrics JSONB,                          -- Domain-specific KPIs (followers, weight, lessons, etc.)

    -- Source
    conversation_id UUID,                   -- Which conversation created this

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_missions_person ON long_running_missions(person_id);
CREATE INDEX IF NOT EXISTS idx_missions_active ON long_running_missions(person_id, status) WHERE status = 'active';
CREATE INDEX IF NOT EXISTS idx_missions_category ON long_running_missions(person_id, category);

-- ============================================================================
-- 2. PHASES - Multi-week chunks within a mission (Foundation, Growth, etc.)
-- ============================================================================
CREATE TABLE IF NOT EXISTS mission_phases (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    mission_id UUID NOT NULL REFERENCES long_running_missions(id) ON DELETE CASCADE,

    -- Phase definition
    phase_number INTEGER NOT NULL,          -- 1, 2, 3...
    name TEXT NOT NULL,                     -- "Foundation Phase"
    objective TEXT,                         -- What this phase achieves

    -- Timeline
    start_date DATE NOT NULL,
    target_end_date DATE NOT NULL,
    actual_end_date DATE,

    -- Status
    status TEXT DEFAULT 'pending',          -- pending, active, completed, skipped

    -- Deliverables
    expected_outcomes JSONB,                -- What success looks like
    actual_outcomes JSONB,                  -- What actually happened

    -- Human approval
    requires_approval BOOLEAN DEFAULT TRUE, -- Needs user OK before starting
    approved_at TIMESTAMPTZ,
    approved_by TEXT,                       -- 'user' or 'auto'

    -- Adaptation
    adjustments_made TEXT[],                -- Changes from original plan

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_phases_mission ON mission_phases(mission_id);
CREATE INDEX IF NOT EXISTS idx_phases_active ON mission_phases(mission_id, status) WHERE status = 'active';

-- ============================================================================
-- 3. WEEKLY PLANS - Concrete plan for each 7-day period
-- ============================================================================
CREATE TABLE IF NOT EXISTS mission_weekly_plans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    mission_id UUID NOT NULL REFERENCES long_running_missions(id) ON DELETE CASCADE,
    phase_id UUID REFERENCES mission_phases(id) ON DELETE SET NULL,

    -- Week identification
    week_number INTEGER NOT NULL,           -- Week 1, 2, 3...
    week_start DATE NOT NULL,
    week_end DATE NOT NULL,

    -- Planning
    objectives TEXT[],                      -- This week's goals
    tasks JSONB,                            -- Structured task list

    -- Status
    status TEXT DEFAULT 'planned',          -- planned, active, completed, adjusted

    -- Review
    review_completed BOOLEAN DEFAULT FALSE,
    review_notes TEXT,                      -- End-of-week reflection
    what_worked TEXT[],
    what_didnt TEXT[],
    adjustments_for_next TEXT[],

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_weekly_mission ON mission_weekly_plans(mission_id);
CREATE INDEX IF NOT EXISTS idx_weekly_phase ON mission_weekly_plans(phase_id);
CREATE INDEX IF NOT EXISTS idx_weekly_dates ON mission_weekly_plans(week_start, week_end);

-- ============================================================================
-- 4. SCHEDULED ACTIONS - Individual tasks to execute
-- ============================================================================
CREATE TABLE IF NOT EXISTS mission_scheduled_actions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    mission_id UUID NOT NULL REFERENCES long_running_missions(id) ON DELETE CASCADE,
    weekly_plan_id UUID REFERENCES mission_weekly_plans(id) ON DELETE SET NULL,
    person_id UUID NOT NULL REFERENCES persons(id),

    -- Action definition
    action_type TEXT NOT NULL,              -- post, engage, analyze, research, exercise, learn
    description TEXT NOT NULL,
    instructions JSONB,                     -- Detailed execution steps for vision loop

    -- Scheduling
    scheduled_date DATE NOT NULL,
    scheduled_time TIME,                    -- NULL = anytime that day
    deadline TIMESTAMPTZ,                   -- Must complete by

    -- Trigger type
    trigger_type TEXT DEFAULT 'scheduled',  -- scheduled, recurring, condition, event, manual
    cron_expression TEXT,                   -- For recurring: "0 9 * * MON" = Monday 9am
    trigger_condition TEXT,                 -- For condition-based: SQL or expression

    -- Execution
    status TEXT DEFAULT 'scheduled',        -- scheduled, triggered, running, completed, failed, skipped
    agent_session_id UUID,                  -- Links to vision loop session
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,

    -- Results
    outcome JSONB,                          -- What happened
    success BOOLEAN,
    error_message TEXT,

    -- Learning
    effectiveness_score DECIMAL(3,2),       -- 0-1, did this help the mission?
    notes TEXT,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_actions_mission ON mission_scheduled_actions(mission_id);
CREATE INDEX IF NOT EXISTS idx_actions_weekly ON mission_scheduled_actions(weekly_plan_id);
CREATE INDEX IF NOT EXISTS idx_actions_person ON mission_scheduled_actions(person_id);
CREATE INDEX IF NOT EXISTS idx_actions_scheduled ON mission_scheduled_actions(scheduled_date, scheduled_time);
CREATE INDEX IF NOT EXISTS idx_actions_status ON mission_scheduled_actions(status) WHERE status IN ('scheduled', 'triggered');
CREATE INDEX IF NOT EXISTS idx_actions_due ON mission_scheduled_actions(scheduled_date, status)
    WHERE status = 'scheduled';

-- ============================================================================
-- 5. CHECKPOINTS - Progress snapshots for tracking and analysis
-- ============================================================================
CREATE TABLE IF NOT EXISTS mission_checkpoints (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    mission_id UUID NOT NULL REFERENCES long_running_missions(id) ON DELETE CASCADE,

    -- Timing
    checkpoint_date DATE NOT NULL,
    checkpoint_type TEXT NOT NULL,          -- daily, weekly, monthly, milestone

    -- State snapshot
    metrics_snapshot JSONB,                 -- All metrics at this point
    progress_pct INTEGER,
    health TEXT,

    -- Analysis
    analysis TEXT,                          -- AI-generated analysis
    recommendations TEXT[],                 -- Suggested adjustments
    risks TEXT[],                           -- Identified risks

    -- Decisions
    adjustments_approved JSONB,             -- User-approved changes
    user_feedback TEXT,

    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_checkpoints_mission ON mission_checkpoints(mission_id);
CREATE INDEX IF NOT EXISTS idx_checkpoints_date ON mission_checkpoints(checkpoint_date);
CREATE INDEX IF NOT EXISTS idx_checkpoints_type ON mission_checkpoints(mission_id, checkpoint_type);

-- ============================================================================
-- 6. MISSION DATA - Generic table for any mission-generated data
-- ============================================================================
-- Design: One table handles all data types (expenses, tweets, workouts, etc.)
-- See docs/LONG_RUNNING_TASKS.md "Generic Mission Data" section

CREATE TABLE IF NOT EXISTS mission_data (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    mission_id UUID REFERENCES long_running_missions(id) ON DELETE CASCADE,
    person_id UUID NOT NULL REFERENCES persons(id),

    -- Flexible typing
    record_type TEXT NOT NULL,              -- 'expense', 'tweet', 'workout', 'lesson', anything

    -- The actual data (schema-free)
    data JSONB NOT NULL,                    -- {vendor: "Vercel", amount: 49.99, category: "Cloud"}

    -- Common fields
    record_date DATE,                       -- When this record is for (not created_at)
    source TEXT,                            -- 'email', 'manual', 'api', 'vision_loop'

    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_mission_data_lookup ON mission_data(mission_id, record_type);
CREATE INDEX IF NOT EXISTS idx_mission_data_person ON mission_data(person_id, record_type);
CREATE INDEX IF NOT EXISTS idx_mission_data_date ON mission_data(record_date);

-- ============================================================================
-- 7. MISSION PLAN HISTORY - Optional versioning of plan documents
-- ============================================================================
CREATE TABLE IF NOT EXISTS mission_plan_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    mission_id UUID NOT NULL REFERENCES long_running_missions(id) ON DELETE CASCADE,

    plan_document TEXT,
    changed_at TIMESTAMPTZ DEFAULT NOW(),
    change_summary TEXT,
    changed_by TEXT                         -- 'user' or 'sakhi'
);

CREATE INDEX IF NOT EXISTS idx_plan_history_mission ON mission_plan_history(mission_id);

-- ============================================================================
-- TRIGGERS - Auto-update timestamps
-- ============================================================================

-- Mission timestamp
CREATE OR REPLACE FUNCTION update_mission_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS mission_timestamp ON long_running_missions;
CREATE TRIGGER mission_timestamp
    BEFORE UPDATE ON long_running_missions
    FOR EACH ROW
    EXECUTE FUNCTION update_mission_timestamp();

-- Phase timestamp
DROP TRIGGER IF EXISTS phase_timestamp ON mission_phases;
CREATE TRIGGER phase_timestamp
    BEFORE UPDATE ON mission_phases
    FOR EACH ROW
    EXECUTE FUNCTION update_mission_timestamp();

-- Weekly plan timestamp
DROP TRIGGER IF EXISTS weekly_plan_timestamp ON mission_weekly_plans;
CREATE TRIGGER weekly_plan_timestamp
    BEFORE UPDATE ON mission_weekly_plans
    FOR EACH ROW
    EXECUTE FUNCTION update_mission_timestamp();

-- Action timestamp
DROP TRIGGER IF EXISTS action_timestamp ON mission_scheduled_actions;
CREATE TRIGGER action_timestamp
    BEFORE UPDATE ON mission_scheduled_actions
    FOR EACH ROW
    EXECUTE FUNCTION update_mission_timestamp();

-- ============================================================================
-- HELPER FUNCTIONS
-- ============================================================================

-- Get active missions for a person
CREATE OR REPLACE FUNCTION get_active_missions(p_person_id UUID)
RETURNS TABLE (
    id UUID,
    title TEXT,
    category TEXT,
    progress_pct INTEGER,
    health TEXT,
    current_phase TEXT,
    next_action TEXT,
    next_action_date DATE
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        m.id,
        m.title,
        m.category,
        m.progress_pct,
        m.health,
        (SELECT name FROM mission_phases WHERE mission_id = m.id AND status = 'active' LIMIT 1) as current_phase,
        (SELECT description FROM mission_scheduled_actions
         WHERE mission_id = m.id AND status = 'scheduled'
         ORDER BY scheduled_date, scheduled_time LIMIT 1) as next_action,
        (SELECT scheduled_date FROM mission_scheduled_actions
         WHERE mission_id = m.id AND status = 'scheduled'
         ORDER BY scheduled_date, scheduled_time LIMIT 1) as next_action_date
    FROM long_running_missions m
    WHERE m.person_id = p_person_id
    AND m.status = 'active'
    ORDER BY m.created_at DESC;
END;
$$ LANGUAGE plpgsql;

-- Get today's actions across all missions
CREATE OR REPLACE FUNCTION get_todays_mission_actions(p_person_id UUID)
RETURNS TABLE (
    action_id UUID,
    mission_id UUID,
    mission_title TEXT,
    action_type TEXT,
    description TEXT,
    scheduled_time TIME,
    status TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        a.id as action_id,
        a.mission_id,
        m.title as mission_title,
        a.action_type,
        a.description,
        a.scheduled_time,
        a.status
    FROM mission_scheduled_actions a
    JOIN long_running_missions m ON a.mission_id = m.id
    WHERE a.person_id = p_person_id
    AND a.scheduled_date = CURRENT_DATE
    AND a.status IN ('scheduled', 'triggered', 'running')
    ORDER BY a.scheduled_time NULLS LAST;
END;
$$ LANGUAGE plpgsql;
