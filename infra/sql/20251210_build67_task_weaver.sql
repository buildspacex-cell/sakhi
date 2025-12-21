-- Build 67: Task & Timeline Auto-Weaving fields

ALTER TABLE IF EXISTS tasks
    ADD COLUMN IF NOT EXISTS canonical_intent TEXT,
    ADD COLUMN IF NOT EXISTS inferred_time_horizon TEXT,
    ADD COLUMN IF NOT EXISTS energy_cost DOUBLE PRECISION,
    ADD COLUMN IF NOT EXISTS emotional_fit TEXT,
    ADD COLUMN IF NOT EXISTS auto_priority DOUBLE PRECISION,
    ADD COLUMN IF NOT EXISTS parent_task_id UUID,
    ADD COLUMN IF NOT EXISTS anchor_goal_id UUID REFERENCES planner_goals(id);

-- parent_task_id is intentionally nullable; keep existing relationships if present

