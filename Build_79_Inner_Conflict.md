# Build 79 — Inner Conflict Engine v1

This build adds a deterministic inner-conflict layer that detects anchor collisions, intent contradictions, emotional divergence, task avoidance, and coherence-related tensions. Results are cached in `inner_conflict_cache` and mirrored into `personal_model.conflict_state`, with API access for clients.

## What changed
- Migration `infra/sql/20251222_build79_inner_conflict.sql` adds `inner_conflict_cache`, `personal_model.conflict_state`, and an updated_at index.
- Engine `sakhi/apps/engine/inner_conflict/engine.py` computes conflicts from intents, tasks, emotion trends, identity anchors, alignment, coherence, and pattern signals.
- Worker `sakhi/apps/worker/tasks/inner_conflict.py` writes cache + personal_model.
- Scheduler hooks a daily run (env-configurable hour) alongside other analytics jobs.
- API route `/v1/identity/conflict` returns the latest conflict state (personal_model fallback to cache).
- Tests `tests/test_build79_inner_conflict.py` cover conflict detection rules and API smoke.

## Data contract (`conflict_state`)
```json
{
  "conflict_score": 0.0,
  "conflicts": [
    {"a": "anchor_or_intent_A", "b": "anchor_or_intent_B", "force": 0.2, "evidence": ["..."]}
  ],
  "dominant_conflict": "anchor_or_intent",
  "updated_at": "ISO8601"
}
```

## Triggers
- Identity state, intent evolution, emotion loop, coherence refresh events
- Daily cron (INNER_CONFLICT_HOUR env, default 11 UTC)

## Notes
- No ingestion or embedding changes.
- Deterministic logic only; no LLM calls.
- Personal_model sync happens in the worker to keep reads fast.
