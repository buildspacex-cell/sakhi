-- Build 33 – Planner Engine Core schema changes
-- Task → Milestone → Goal decomposition plus cached summaries.

-- Goals capture the highest-level intent within a horizon.
CREATE TABLE IF NOT EXISTS planner_goals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id UUID NOT NULL REFERENCES profiles (user_id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    details TEXT DEFAULT '',
    horizon TEXT NOT NULL DEFAULT 'week',
    priority INTEGER NOT NULL DEFAULT 1,
    status TEXT NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS planner_goals_person_idx
    ON planner_goals (person_id, horizon);

-- Milestones are mid-tier checkpoints that belong to a goal.
CREATE TABLE IF NOT EXISTS planner_milestones (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id UUID NOT NULL REFERENCES profiles (user_id) ON DELETE CASCADE,
    goal_id UUID NOT NULL REFERENCES planner_goals (id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    details TEXT DEFAULT '',
    due_ts TIMESTAMPTZ,
    horizon TEXT NOT NULL DEFAULT 'week',
    status TEXT NOT NULL DEFAULT 'active',
    sequence INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS planner_milestones_goal_idx
    ON planner_milestones (goal_id);

-- Planned items evolve into structured tasks.
ALTER TABLE planned_items
    ADD COLUMN IF NOT EXISTS goal_id UUID REFERENCES planner_goals (id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS milestone_id UUID REFERENCES planner_milestones (id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS status TEXT NOT NULL DEFAULT 'pending',
    ADD COLUMN IF NOT EXISTS priority INTEGER NOT NULL DEFAULT 1,
    ADD COLUMN IF NOT EXISTS energy TEXT,
    ADD COLUMN IF NOT EXISTS ease INTEGER,
    ADD COLUMN IF NOT EXISTS recurrence JSONB,
    ADD COLUMN IF NOT EXISTS horizon TEXT,
    ADD COLUMN IF NOT EXISTS origin_id TEXT,
    ADD COLUMN IF NOT EXISTS meta JSONB DEFAULT '{}'::jsonb;

CREATE UNIQUE INDEX IF NOT EXISTS planned_items_origin_idx
    ON planned_items (person_id, origin_id)
    WHERE origin_id IS NOT NULL;

-- Cached planner summary payload, mirroring memory_context_cache.
CREATE TABLE IF NOT EXISTS planner_context_cache (
    person_id UUID PRIMARY KEY REFERENCES profiles (user_id) ON DELETE CASCADE,
    payload JSONB NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
