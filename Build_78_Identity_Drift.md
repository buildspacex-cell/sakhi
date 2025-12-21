# Build 78 — Identity Drift Engine v1 (Self-Concept Mapping)

This build adds a deterministic identity drift layer that maps self-concept signals to stable anchors, computes drift, and surfaces warnings/opportunities. Data is cached in `identity_drift_cache` and mirrored into `personal_model.identity_state`.

## Scope
- New cache table and `personal_model.identity_state` field (migration `infra/sql/20251221_build78_identity_drift.sql`).
- Engine `sakhi/apps/engine/identity_drift/engine.py` (planned): derives anchors, alignment, drift, warnings, and opportunities from intents, narrative arcs, pattern sense, emotion loop, coherence, alignment map, inner dialogue, and wellness baselines.
- Worker `identity_drift_refresh` (planned): runs after related refreshes and daily at 10 AM to write cache + personal_model.
- API endpoint `/v1/identity/state?person_id=` (planned): returns the latest identity state.
- Tests `tests/test_build78_identity_drift.py` (planned): cover anchor extraction, alignment scoring, drift calc, warnings/opportunities, cache + personal_model sync.

## Data Contract (`identity_state`)
```json
{
  "anchors": ["creative", "learning-driven", "..."],
  "drift_score": 0.0,
  "anchor_alignment": { "creative": 0.6 },
  "identity_movement": "upward|downward|stable",
  "warnings": [],
  "opportunities": [],
  "updated_at": "ISO8601"
}
```

## Triggers
- narrative_arc_refresh
- pattern_sense_refresh
- alignment_refresh
- coherence_refresh
- inner_dialogue_refresh
- daily 10 AM cron

## Notes
- No ingestion or embedding changes.
- No LLM usage in turn; worker-only logic is deterministic.
- Keep Build 52 hashing/vector reuse untouched.
