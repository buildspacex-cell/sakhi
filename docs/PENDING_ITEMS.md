# Pending Items

Last updated: 2026-03-07

This document captures intentionally deferred work found during simulation hardening.
These items are real gaps, but they are not current investor-demo blockers.

## 1. Table-Backed Rhythm Infrastructure

### Status

- `rhythm_daily_curve` is missing in the live database.
- `rhythm_state` is missing in the live database.
- `rhythm_events` is missing in the live database.
- `rhythm_weekly_rollups` exists, but `weekly_rhythm_rollup` currently skips because `rhythm_daily_curve` is absent.
- As of 2026-03-07, turn-time `rhythm_planner_alignment` loading is removed from the default path and gated behind `SAKHI_ENABLE_RHYTHM_PLANNER_ALIGNMENT=1`.
- As of 2026-03-07, weekly rhythm rollups are disabled by default (`SAKHI_ENABLE_WEEKLY_RHYTHM_ROLLUP=0`) to keep missing rhythm tables out of default production/simulation paths.

### Current Impact

- `weekly_rhythm_rollup` does not produce weekly rollups.
- `weekly_signals` still runs, but without rhythm rollup input.
- `/rhythm/{person_id}/state` and `/rhythm/{person_id}/curve` are not backed by live data.
- Planner-side rhythm helpers that read `rhythm_daily_curve` remain deferred and are no longer part of the default turn path.
- Scheduled weekly rollup enqueue is skipped unless explicitly enabled.

### Why This Is Deferred

- Main conversation turns do not depend on these tables.
- The core deterministic turn path uses `personal_model.rhythm_state`, not `rhythm_daily_curve`.
- Simulation is still producing rhythm-aware downstream states through `personal_model.rhythm_state`.
- This weakens the analytics stack, but it does not block the current demo story.

### What This Subsystem Is For

- Persisting daily slot-by-slot rhythm curves.
- Building weekly rhythm rollups (`avg_level`, `slope`, `volatility`, `peak_windows`, `dip_windows`).
- Supporting rhythm API endpoints and richer planner-time rhythm analysis.

### Fix Path

1. Add a migration for:
   - `rhythm_state`
   - `rhythm_daily_curve`
   - `rhythm_events`
2. Confirm constraints and indexes match the write/read patterns in:
   - `sakhi/apps/api/services/rhythm/engine.py`
   - `sakhi/apps/api/routes/rhythm.py`
   - `sakhi/apps/worker/tasks/weekly_rhythm_rollup_worker.py`
3. Verify the writer path is actually invoked in production and simulation where intended:
   - `sakhi/apps/worker/tasks/rhythm_forecast.py`
4. Decide whether simulation parity should include table-backed rhythm writes, or whether `personal_model.rhythm_state` remains the only required rhythm artifact for demo runs.
5. Re-run weekly rhythm rollup and verify it writes `rhythm_weekly_rollups` rows instead of skipping.

### Acceptance Criteria

- `weekly_rhythm_rollup` no longer returns `skipped: rhythm_daily_curve_missing`.
- `/rhythm` routes return live data.
- Weekly analytics gain real rhythm rollup input.
- No regression in the existing `personal_model.rhythm_state` path.

## 2. Agentic Execution

### Status

- Mainline chat execution is intentionally disabled by default.
- `turn_v2` gates agent-task planning/execution behind `SAKHI_ENABLE_AGENT_EXECUTION`.
- Default behavior is off.
- Dedicated agent planning and execution code still exists in the repo.

### Current Impact

- The investor demo and normal chat do not auto-enter agent planning.
- Sakhi will not offer to start autonomous tasks in the main conversation path.
- The agent layer remains available for later enablement, but it is not part of the current demo dependency chain.

### Why This Is Deferred

- Autonomous execution is not required for the current Sakhi + Kala investor demo.
- The current value story is personalized understanding, deterministic intelligence, simulation, and governance on responses.
- Agent execution adds operational and safety complexity without increasing the current demo's core clarity.

### Current Risks / Gaps

- Agent orchestration is not the primary Kala governance integration point today.
- There is no clear end-to-end governance gate at:
   - task plan creation
   - risky step execution
   - external side-effect boundaries
- Desktop-agent execution adds additional runtime and failure surfaces that are not needed for the present demo.

### Fix Path Before Re-Enable

1. Define the exact investor/product scope for agentic execution:
   - task planning only
   - simulated execution
   - real desktop execution
2. Add Kala governance hooks to the agent path:
   - plan-time review
   - pre-execution gating
   - explicit confirmation for external side effects
3. Define a minimal safe task set for early enablement.
4. Add route and integration tests for:
   - disabled-by-default behavior
   - confirmation flow
   - blocked / require-confirmation governance outcomes
5. Re-enable only by explicit env flag after the above is validated.

### Acceptance Criteria

- Agent execution is opt-in and explicitly governed.
- The planner path is safe to demo without bypassing Kala controls.
- Mainline chat remains stable when the agent layer is disabled.

## 3. User-Facing Journal Entry Deletion

### Status

- No user-facing deletion exists in mobile or web.
- Deletion is currently only possible via dev endpoints (`POST /memory/dev/reset`, `POST /dev/reset-user-data`).
- Cache invalidation on deletion is already implemented in `invalidate_person_cross_topic_cache()` — it just has no user-facing trigger yet.

### Current Impact

- Users cannot remove a journal entry they regret sharing.
- This creates a trust and self-censorship risk: users may share less honestly if they know they cannot undo it.
- GDPR right to erasure requires deletion capability before any EU user exposure.

### Why This Is Deferred

- Not a demo blocker — current users are internal (co-founders, TestFlight QA).
- Single-thread design makes deletion more consequential than in a typical chat app; the UX framing needs care.
- Backend cascade infrastructure (embeddings, episodic memory, continuity cache) is already correct and tested.

### Fix Path

1. Add a backend route: `DELETE /journal/entries/{entry_id}` scoped to `person_id`.
   - Cascade: `journal_embeddings`, `memory_episodic` (rows referencing the entry), call `invalidate_person_cross_topic_cache()`.
   - Return `204 No Content`.
2. Mobile UI: long-press on a message bubble → "Remove from my story" → confirm sheet → call route.
3. Web UI: hover menu on message → same flow.
4. Frame as "remove from story" not "delete message" — sets correct expectation that Sakhi's memory is updated, not that a chat log is being edited.
5. Add unit test for cascade correctness; integration test for the route.

### Acceptance Criteria

- User can remove a journal entry from mobile and web.
- Embeddings, episodic memory rows, and continuity cache are cleaned up atomically.
- Confirmation UI makes clear what "remove from story" means.
- No entry surfaces again in continuity, memory recall, or cross-topic signals after removal.

## Current Demo Guidance

- Keep both items deferred for the investor demo.
- Continue prioritizing:
  - stable full-length simulation runs
  - strong journal-driven personalization
  - visible governance behavior
  - differentiated pattern and theme intelligence
