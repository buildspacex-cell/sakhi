-- =============================================================================
-- Migration 0009: Agent Task Recurring Schedules
-- =============================================================================
--
-- Adds durable recurring schedule storage and run logs for Stage 2 recurring
-- task automation (e.g., monthly subscription audits).
--
-- =============================================================================
-- 1. Recurring Schedules
-- =============================================================================

CREATE TABLE IF NOT EXISTS agent_task_schedules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id TEXT NOT NULL,
    task_description TEXT NOT NULL,
    goal_hint TEXT,

    cadence TEXT NOT NULL DEFAULT 'monthly',
    cadence_interval INTEGER NOT NULL DEFAULT 1 CHECK (cadence_interval > 0),
    run_timezone TEXT NOT NULL DEFAULT 'UTC',
    day_of_month INTEGER NOT NULL DEFAULT 1 CHECK (day_of_month >= 1 AND day_of_month <= 31),
    run_hour INTEGER NOT NULL DEFAULT 9 CHECK (run_hour >= 0 AND run_hour <= 23),
    run_minute INTEGER NOT NULL DEFAULT 0 CHECK (run_minute >= 0 AND run_minute <= 59),

    status TEXT NOT NULL DEFAULT 'pending_approval'
        CHECK (status IN ('pending_approval', 'active', 'paused', 'cancelled')),
    is_running BOOLEAN NOT NULL DEFAULT FALSE,

    next_run_at TIMESTAMPTZ,
    last_run_at TIMESTAMPTZ,
    last_run_status TEXT,
    consecutive_failures INTEGER NOT NULL DEFAULT 0,

    created_plan_id TEXT,
    latest_plan_id TEXT,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_agent_task_schedules_person_status
    ON agent_task_schedules(person_id, status);

CREATE INDEX IF NOT EXISTS idx_agent_task_schedules_due
    ON agent_task_schedules(status, is_running, next_run_at);

CREATE INDEX IF NOT EXISTS idx_agent_task_schedules_person_created
    ON agent_task_schedules(person_id, created_at DESC);

-- =============================================================================
-- 2. Recurring Run Logs
-- =============================================================================

CREATE TABLE IF NOT EXISTS agent_task_schedule_runs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    schedule_id UUID NOT NULL REFERENCES agent_task_schedules(id) ON DELETE CASCADE,
    person_id TEXT NOT NULL,
    plan_id TEXT,
    trigger_source TEXT NOT NULL DEFAULT 'scheduler',
    status TEXT NOT NULL DEFAULT 'started'
        CHECK (status IN ('started', 'completed', 'failed', 'cancelled')),
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    summary TEXT,
    error TEXT,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_agent_task_schedule_runs_schedule_created
    ON agent_task_schedule_runs(schedule_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_agent_task_schedule_runs_person_created
    ON agent_task_schedule_runs(person_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_agent_task_schedule_runs_plan
    ON agent_task_schedule_runs(plan_id);
