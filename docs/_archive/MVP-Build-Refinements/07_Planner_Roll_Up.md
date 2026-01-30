STEP 6 — Planner Pressure Rollup

(Deterministic External Load Modeling)

Purpose

STEP 6 introduces a task-safe pressure abstraction over the planner system.

The goal is to capture how much external obligation pressure a user is under —
without ever storing or exposing task text.

This enables weekly reflection and trend learning to reference pressure
without leaking content.

Source Tables (Read-Only)
planned_items

Fields used (numeric / categorical only):

status

due_ts

priority

horizon

energy

ease

created_at

updated_at

❌ Explicitly not used

label

payload

meta

any free text

Target Table
planner_weekly_pressure
CREATE TABLE planner_weekly_pressure (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  person_id UUID NOT NULL REFERENCES profiles(user_id),
  week_start DATE NOT NULL,
  week_end DATE NOT NULL,

  open_count INTEGER NOT NULL,
  overdue_count INTEGER NOT NULL,
  due_this_week INTEGER NOT NULL,

  carryover_rate NUMERIC NOT NULL,
  fragmentation_score NUMERIC NOT NULL,
  overload_flag BOOLEAN NOT NULL,

  horizon_mix JSONB NOT NULL,
  priority_mix JSONB NOT NULL,

  confidence NUMERIC NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

  UNIQUE (person_id, week_start)
);

Computed Metrics
Metric	Meaning
open_count	Total open obligations
overdue_count	Past-due items
carryover_rate	Unresolved work spilling forward
fragmentation_score	Horizon + priority dispersion
overload_flag	Derived threshold crossing
confidence	Data sufficiency + stability

All metrics are deterministic and idempotent.

Safety Guarantees

No task titles stored

No planner cache read

No LLM usage

No prose

Rebuildable from planner tables