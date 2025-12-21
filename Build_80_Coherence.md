# Build 80 — Coherence Engine v1

This build adds a deterministic coherence engine that blends signals from intent trends, behavior, emotion loop, identity drift, conflicts, alignment, and narrative stability. Results are cached in `coherence_cache` and mirrored into `personal_model.coherence_state`, with a public API for clients.

## What changed
- Migration `infra/sql/20251223_build80_coherence_engine.sql` creates `coherence_cache`, `personal_model.coherence_state`, and index.
- Engine `sakhi/apps/engine/coherence/engine.py` now computes:
  - `coherence_score`
  - `fragmentation_index`
  - `coherence_map` (thought, emotion, behavior, identity, alignment, narrative)
  - issues/adjustments/summary/confidence (backwards compatible)
- Worker `sakhi/apps/worker/tasks/coherence.py` writes cache + personal_model; scheduler runs daily (config `COHERENCE_STATE_HOUR`).
- API `/v1/coherence/report` now returns the new coherence_state (personal_model fallback to cache).
- Tests `tests/test_build80_coherence_engine.py` cover computation and API smoke.

## Data contract (`coherence_state`)
```json
{
  "coherence_score": 0.0,
  "fragmentation_index": 0.0,
  "coherence_map": {
    "thought": 0.0,
    "emotion": 0.0,
    "behavior": 0.0,
    "identity": 0.0,
    "alignment": 0.0,
    "narrative": 0.0
  },
  "issues": [],
  "adjustments": [],
  "summary": "Coherence stable",
  "confidence": 1.0,
  "updated_at": "ISO8601"
}
```

## Triggers
- Scheduled daily (default 12 UTC via `COHERENCE_STATE_HOUR`).
- Can be manually queued with `run_coherence`.

## Notes
- No ingestion or embedding changes.
- Logic is deterministic (no LLM).
- Backward compatibility kept: issues/adjustments/summary/confidence remain in output.
