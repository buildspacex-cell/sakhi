# Build 74 — Multi-Lens Consistency Engine (Coherence v1)

## Summary
Adds a deterministic coherence layer that evaluates cross-consistency across wellness, emotion loop, intent evolution, alignment, tasks, soul, and rhythm. Results are stored in `personal_model.coherence_report`, refreshed via the alignment worker, and exposed via API.

## What Changed
- **Schema**: `infra/sql/20251217_build74_coherence_report.sql` adds `coherence_report` to personal_model.
- **Engine**: `sakhi/apps/engine/coherence/engine.py` computes issues/adjustments/summary/confidence using rule-based checks:
  - Intent–emotion mismatch (strong intent + negative drift)
  - Wellness–task mismatch (low energy + high-energy tasks)
  - Planner–emotion mismatch (avoid_actions present)
  - Soul–mind mismatch (grounding vs overload)
  - Rhythm–task mismatch (offbeat + heavy tasks)
- **Worker**: `alignment_refresh` now also computes coherence_report and writes into personal_model during alignment cache refresh.
- **API**: `GET /v1/coherence/report?person_id=` returns coherence_report (wired in `api/main.py`).

## How It Works
1. Coherence engine gathers wellness_state_cache, emotion_state, intents, alignment_map, today’s tasks, and soul/rhythm hints from personal_model.
2. Applies rules to generate `issues` and `adjustments`; `confidence = max(0.5, 1 - len(issues)*0.05)`.
3. alignment_refresh worker stores coherence_report in personal_model (alongside alignment_state).

## Tests
- `tests/test_build74_coherence_engine.py` (pass): verifies mismatch detection and confidence bounds.
Run:
```bash
poetry run pytest tests/test_build74_coherence_engine.py
```

## Apply Migration
```sql
\i infra/sql/20251217_build74_coherence_report.sql
```

## Notes
- Fully deterministic, no LLM calls.
- Uses existing caches (wellness, alignment, intents, emotion loop, tasks).
- Confidence floors at 0.5 to avoid over-penalizing multiple issues.
