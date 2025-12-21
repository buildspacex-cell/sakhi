# Build 73 — Daily Alignment Engine (Alignment Map v1)

## Summary
Generates a daily alignment map that blends wellness state, emotional loop, intent evolution, and today’s tasks to recommend/avoid actions and self-care steps. Results are cached in `daily_alignment_cache`, exposed via API, and rendered in web/mobile stubs. Deterministic, no LLM.

## What Changed
- **Schema**: `infra/sql/20251216_build73_daily_alignment.sql` adds `daily_alignment_cache` with `alignment_map`.
- **Engine**: `sakhi/apps/engine/alignment/engine.py` computes `alignment_map` from:
  - wellness scores (body/mind/emotion/energy)
  - emotion_loop (trend/drift/volatility/inertia/mode)
  - intent_evolution (strength/alignment/trend)
  - today’s tasks (energy_cost/auto_priority/anchor links)
- **Worker**: `sakhi/apps/worker/tasks/alignment_refresh.py` writes cache and syncs to personal_model.alignment_state; scheduled daily (env `ALIGNMENT_REFRESH_HOUR`, default 05:00 UTC) via scheduler.
- **API**: `GET /v1/alignment/today?person_id=` returns `alignment_map`.
- **UI stubs**: Web (`apps/web/app/alignment/page.tsx`) and mobile (`apps/mobile/app/alignment/index.tsx`) render energy/focus profiles and recommended/self-care lists.

## How It Works
1. Engine fetches wellness, emotion loop, intents, and today’s tasks.
2. Profiles:
   - energy_profile: low/medium/high (energy score thresholds)
   - focus_profile: clear/scattered/overloaded (mind score)
3. Task suitability score = intent_strength*0.4 + emotional_alignment*0.2 + (1-energy_cost)*0.2 + urgency*0.2; tasks above threshold become `recommended_actions`, others `avoid_actions`.
4. Intent alignment suggestions for strong intents (>0.5).
5. Emotional safeguards/self-care from low energy/falling modes or high body/emotion strain.
6. alignment_refresh stores map in `daily_alignment_cache` and personal_model alignment_state.

## Scheduler
- `schedule_alignment_refresh_daily()` in `scheduler.py`; uses `DEFAULT_USER_ID/DEMO_USER_ID`.
- Env: `ALIGNMENT_REFRESH_HOUR` (default 5 UTC).

## Tests
- `tests/test_build73_alignment_engine.py` (pass): profiles, recommendations, worker refresh path.

Run:
```bash
poetry run pytest tests/test_build73_alignment_engine.py
```

## Apply Migration
```sql
\i infra/sql/20251216_build73_daily_alignment.sql
```

## Notes
- Purely deterministic; no LLM.
- Uses existing caches (wellness_state_cache, intent_evolution, emotion_loop, tasks).
- Today’s tasks filtered by inferred_time_horizon NULL/today.
