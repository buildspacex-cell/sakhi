# Build 71 — Continuous Intent Evolution (Intent Engine v2)

## Summary
Adds a longitudinal intent-evolution layer that clusters and tracks intent strength, emotional alignment, and trend over time. Intents are updated on every ingest via deterministic heuristics (no LLM). Daily decay keeps stale intents from dominating. personal_model now exposes an `intents` list with strength/trend/alignment for downstream engines and UI.

## What Changed
- **Schema**: `infra/sql/20251214_build71_intent_evolution.sql` adds `intent_evolution` table + index on `last_seen`.
- **Engine**: `sakhi/apps/intent_engine/evolution.py` with `evolve(person_id, intent, sentiment)` handling normalize, create/strengthen, emotional alignment moving average, trend, and timestamps.
- **Ingestion**: `unified_ingest.py` invokes intent evolution after triage/sentiment to keep intents fresh.
- **Decay worker**: `sakhi/apps/worker/tasks/intent_evolution_decay.py` reduces strength daily and updates trend; scheduled in `scheduler.py` (env `INTENT_DECAY_HOUR`, default 07:00 UTC).
- **personal_model**: syncs `intent_evolution` rows into `long_term["intents"]` (name, strength, trend, emotional_alignment, last_seen).

## How It Works
1. Ingest (unified_ingest) extracts intent from triage, sentiment from mood slots.
2. `evolve()` upserts intent row:
   - New: strength=0.2, emotional_alignment=sentiment, trend=stable.
   - Existing: +0.1 strength (cap 1.0), emotional_alignment EMA (70/30), trend up/down/stable, last_seen updated.
3. Daily decay worker lowers strength by 0.02 if not mentioned; trend set to down/stable.
4. personal_model readback adds intents list for downstream use.

## Scheduler
- `schedule_intent_decay_daily()` in `scheduler.py`; configurable via `INTENT_DECAY_HOUR` (default 7 UTC).
- Uses `DEFAULT_USER_ID/DEMO_USER_ID` same as other scheduled jobs.

## Tests
- `tests/test_build71_intent_evolution.py` (pass):
  - New intent creation
  - Strengthening + trend
  - Decay path
  - personal_model sync

Run:
```bash
poetry run pytest tests/test_build71_intent_evolution.py
```

## Apply Migration
```sql
-- in your DB
\i infra/sql/20251214_build71_intent_evolution.sql
```

## Notes / Safety
- No LLM usage in this build.
- Additive only; ingestion, hashing, embeddings unchanged.
- If `DATABASE_URL` is absent during tests, monkeypatch as in test suite.

