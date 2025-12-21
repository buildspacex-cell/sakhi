# Build 83 — Preventive Nudge Engine v1

## Purpose
Forecast-aware, deterministic micro-nudges that proactively help the user when short-term risks are detected (fatigue, irritability, confusion, procrastination, overwhelm). Nudges are sent by workers only; `/v2/turn` remains read-only for nudge state.

## Schema
- Migration: `infra/sql/20260104_build83_nudge_tables.sql`
  - `nudge_log(id, person_id, category, message, forecast_snapshot, sent_at)`
  - `personal_model.nudge_state JSONB DEFAULT '{}'::jsonb`

## Engine
- Module: `sakhi/apps/engine/nudge/engine.py`
- Function: `compute_nudge(person_id, forecast_state, tone_state)`
- Triggers: fatigue, irritability, confusion, procrastination, overwhelm window (from forecast_state)
- Cooldown: skip if `last_sent_at` < 3h (from `personal_model.nudge_state`)
- Tone-aware templates per category: energy, calming, clarity, focus, grounding
- Output: `{category, message, forecast_snapshot, should_send}`

## Worker
- Task: `sakhi/apps/worker/tasks/nudge_worker.py` → `run_nudge_check(person_id)`
  1) Load forecast_state (forecast_cache), tone_state + nudge_state (personal_model)  
  2) compute_nudge  
  3) If `should_send`: insert into `nudge_log`, update `personal_model.nudge_state`, best-effort `send_nudge_message`
- Scheduling: hourly via scheduler (`schedule_nudge_checks`), and after forecast refresh

## API
- Route: `GET /v1/nudge/log?person_id=` → last 20 nudges (category, message, snapshot, sent_at)

## /v2/turn Integration
- Nudges are NOT sent in-turn. `nudge_state` is included in turn metadata/response for transparency only.

## Tests
- `tests/test_build83_nudge_engine.py`
  - trigger detection (fatigue etc.)
  - cooldown enforcement
  - worker persistence to `nudge_log` + `personal_model.nudge_state`
  - API smoke test

## Safety/Constraints
- Deterministic (no LLM)
- No ingestion changes
- Uses existing forecast + tone signals
- Worker-only sending; respects cooldown
