# Build 72 — Emotion Loop Engine v2 (Drift + Recovery + Prediction)

## Summary
Adds a deterministic emotional evolution layer that tracks drift, volatility, inertia, recovery, and mode from recent sentiments. Tags episodic memory with an `emotion_loop` snapshot, rolls up into personal_model.emotion_state, and schedules a daily refresh worker. No LLM usage.

## What Changed
- **Schema**: `infra/sql/20251215_build72_emotion_loop.sql` adds `emotion_loop` (memory_episodic) and `emotion_state` (personal_model).
- **Engine**: `sakhi/apps/engine/emotion_loop/engine.py` computes trend/drift/volatility/inertia/recovery from last sentiments; helper to load last 20 sentiments for a person.
- **Ingestion**: `unified_ingest.py` computes emotion_loop on each heavy ingest, appends to episodic context_tags.
- **Worker**: `sakhi/apps/worker/tasks/emotion_loop_refresh.py` refreshes emotion_state and writes into personal_model; scheduled daily (config `EMOTION_LOOP_HOUR`, default 04:00 UTC).
- **personal_model**: preserves/syncs emotion_state alongside wellness_state and intents.

## How It Works
1. ingest_heavy fetches sentiment from triage (mood_affect.score).
2. emotion_loop_engine aggregates last 20 sentiments, computes slope (trend/drift), volatility (stddev), inertia (avg abs delta), recovery flag (trend > 0 after negative previous trend), and mode (volatile/rising/falling/recovery/stable).
3. Tags current episodic row with `{"emotion_loop": {...}}` in context_tags.
4. Daily worker recomputes and stores `long_term.emotion_state` in personal_model.

## Scheduler
- Added `schedule_emotion_loop_daily()` in `scheduler.py`; uses `DEFAULT_USER_ID/DEMO_USER_ID`.
- Env: `EMOTION_LOOP_HOUR` (default 4).

## Tests
- `tests/test_build72_emotion_loop.py` (pass):
  - Trend/mode calculation
  - Volatility/inertia
  - Worker refresh flow (mocked DB)

Run:
```bash
poetry run pytest tests/test_build72_emotion_loop.py
```

## Apply Migration
```sql
\i infra/sql/20251215_build72_emotion_loop.sql
```

## Notes
- Purely deterministic; no LLM calls.
- Sentiment source uses existing triage (mood_affect score).
- Small arrays (<=20) keep ingestion fast; O(20) math only.

