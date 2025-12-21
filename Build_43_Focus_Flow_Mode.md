# Build 43 — Focus + Flow Mode

Goal: Real-time focus companion for active work sessions: session activation, periodic nudges/breaks, logging, and end-of-session summaries.

## Schema
- `infra/sql/20251123_build43_focus.sql`
  - `focus_sessions`: person_id, task_id (planner), mode, start/end, estimated/actual duration, completion_score, session_quality, start_state.
  - `focus_events`: per-tick events (nudge/break/etc.) with rhythm/task/emotion snapshots.

Run migration:
```
psql "$DATABASE_URL" -f infra/sql/20251123_build43_focus.sql
```

## API
- Routes: `sakhi/apps/api/routes/focus.py`
  - `POST /focus/start` → creates session, enqueues first tick on queue `focus`.
  - `POST /focus/ping` → optional biomarkers log.
  - `POST /focus/end` → closes session, logs session_end event.
- Service: `sakhi/apps/api/services/focus/engine.py` (start/ping/end logic, Redis enqueue).

## Worker
- Task: `sakhi/apps/worker/tasks/focus_session.py`
  - `run_focus_tick(session_id)` → logs a nudge/break event, updates duration, uses rhythm/task snapshots. Queue: `FOCUS_QUEUE` (default `focus`).
- Worker listens to `focus` queue (`sakhi/apps/worker/main.py`).

## Minimal Test Flow
1) Start session:
```
curl -X POST http://localhost:8000/focus/start \
  -H "Content-Type: application/json" \
  -d '{"person_id":"565bdb63-124b-4692-a039-846fddceff90","task_id":null,"estimated_duration":45,"mode":"deep"}'
```
2) Tick (already enqueued) — inspect events:
```
psql "$DATABASE_URL" -c "SELECT event_type, ts, content FROM focus_events WHERE session_id='REPLACE' ORDER BY ts DESC LIMIT 10;"
```
3) End session:
```
curl -X POST http://localhost:8000/focus/end \
  -H "Content-Type: application/json" \
  -d '{"session_id":"REPLACE","completion_score":0.8,"session_quality":{"note":"test"},"early_end":false}'
```

## Integration Notes
- Uses planner tasks (Build 33) via task_id.
- Uses rhythm state (Build 34) for nudges; sanitized JSON to avoid Decimal/datetime issues.
- Enqueue uses Redis queue `focus`; ensure worker runs with `FOCUS_QUEUE` available.
- Emotion baseline sources are limited to existing signals (personal_model.emotion, memory_short_term sentiment/emotion_tags); no new detectors added. Helper migration `infra/sql/20251123_add_personal_model_emotion.sql` adds the `personal_model.emotion` column; optional backfill:
  ```
  UPDATE personal_model pm
  SET emotion = CASE
    WHEN ls.sentiment::float > 0.25 THEN 'positive'
    WHEN ls.sentiment::float < -0.25 THEN 'negative'
    ELSE 'neutral'
  END
  FROM (
    SELECT user_id::uuid AS user_id, sentiment
    FROM memory_short_term mst
    WHERE sentiment IS NOT NULL
      AND mst.created_at = (
        SELECT MAX(created_at) FROM memory_short_term WHERE user_id = mst.user_id AND sentiment IS NOT NULL
      )
  ) ls
  WHERE pm.person_id = ls.user_id
    AND pm.emotion IS DISTINCT FROM CASE
      WHEN ls.sentiment::float > 0.25 THEN 'positive'
      WHEN ls.sentiment::float < -0.25 THEN 'negative'
      ELSE 'neutral'
    END;
  ```
- Nudges obey guardrails: allowed types only, 1/5m backoff, max 8 per session, micro-tone only.
- Session end writes a single summary record into `memory_short_term` (best-effort habit increment on `personal_model` if column exists).

## TODO / Enhancements
- Add distraction/flow-window detection and map to the allowed nudge types without exceeding guardrails.
- Hook a scheduler to trigger `run_focus_tick` every 5 minutes (single worker instance per session) instead of manual enqueue only.
- Improve end-of-session summary quality (energy curve, friction points) and wire habit strength updates once the column schema is confirmed.
- Add recovery break recommendations when stress/fatigue rises using existing rhythm state only.
- Auto-populate `personal_model.emotion` during persona/rhythm updates (or a nightly backfill) so focus baselines never read NULL.
