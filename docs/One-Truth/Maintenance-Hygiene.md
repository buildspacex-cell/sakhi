Maintenance & System Hygiene Workers

(State Coherence, Performance, and Alignment)

Purpose of this layer

This layer exists to keep Sakhi’s internal systems consistent, performant, and aligned as activity accumulates.

These workers:

do not introduce new intelligence

do not interact with users directly

do not run in the turn path

They ensure that derived state stays fresh and expensive recomputation is avoided.

Intelligence compounds only if maintenance keeps pace.

When these workers run

Scheduled periodically or invoked after specific background commits

Never block a live turn

Operate on already-persisted state

They are pure maintenance, not inference.

task_weaver_refresh

(Aggregated Task Structure Maintenance)

Why

To keep the task-weaver’s aggregated view of tasks and plans current.

What / How

Runs task-weaver refresh logic

Recomputes weaver state from:

tasks

plans

planner structure

Writes refreshed state into:

task-weaver cache / table

Use

Task-weaver UI and logic read the cached state

Avoids recomputing complex task relationships inline

This keeps task orchestration responsive without reprocessing plans repeatedly.

update_system_tempo

(Operational Tempo Tracking)

Why

To monitor and maintain system-level tempo — how fast and how heavily the system is operating.

What / How

Computes tempo metrics (exact fields depend on implementation)

Writes metrics into the system tempo store

Runs on a schedule

Use

Operational dashboards

Auto-throttling or load-shedding logic

System health monitoring

This worker is purely operational.

sync_analytics_cache

(Analytics Cache Refresh)

Why

To ensure analytics endpoints can respond quickly without heavy live queries.

What / How

Periodically refreshes:

counts

trends

summary statistics

Writes into analytics cache tables

Use

Analytics APIs and dashboards read cached data

Prevents expensive aggregation on demand

Reporting should never compete with reflection or conversation.

Growth sync

(sync_growth_from_planner)

Why

To keep growth state aligned with what the user is actually planning and doing.

What / How

Invoked after planner_commit

Translates planner outputs (goals, tasks, milestones) into:

growth-related records

progression state

Use

Growth views

Growth logic and alignment features

Ensures growth does not drift from planner reality

This avoids requiring explicit user actions to keep growth in sync.

What this layer does not do

Does not generate insights

Does not infer identity

Does not create plans or tasks

Does not interact with the user

Does not run in real time

It exists purely to maintain coherence and performance.

How this fits the overall storyline
Intelligence layers produce state
        ↓
Maintenance workers keep state fresh
        ↓
Live experiences remain fast and consistent


This layer ensures that:

higher-level intelligence stays usable

caches stay accurate

the system scales without degradation

One-line anchor (keep this)

Maintenance keeps intelligence usable.