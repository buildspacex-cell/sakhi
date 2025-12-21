# Build 44 — Relationship Model (Trust / Attunement / Safety / Closeness)

Goal: Persist and evolve Sakhi’s relational state (trust, attunement, emotional safety, closeness stage) and feed it into tone/companionship behaviors.

## Schema
- `infra/sql/20251124_build44_relationship.sql`
  - `relationship_state`: person_id PK, trust_score, attunement_score, emotional_safety, closeness_stage, preference_profile, interaction_patterns, updated_at.
  - `personal_model.relationship_state` (jsonb cache for fast reads).
- Optional emotion helper: `infra/sql/20251123_add_personal_model_emotion.sql` adds `personal_model.emotion` for baseline pulls.

Run migrations:
```
psql "$DATABASE_URL" -f infra/sql/20251124_build44_relationship.sql
psql "$DATABASE_URL" -f infra/sql/20251123_add_personal_model_emotion.sql   # optional helper column
```

## Engine & Hooks
- Module: `sakhi/apps/logic/relationship_engine.py`
  - `update_from_turn(payload, sentiment, pushback, person_id)`
  - `update_from_focus(person_id, completion_score, wins, friction, mood)`
  - Safely casts decimals → float; updates relationship_state row.
- Turn pipeline hook: `sakhi/apps/worker/pipelines/turn_updates/runner.py` calls `update_from_turn` after persona/soul/narrative. Reads sentiment/mood from turn payload facets and detects pushback from text.
- Focus hook: `sakhi/apps/api/services/focus/engine.py` calls `update_from_focus` after session end summary.
- Cache backfill (one-time, manual) if you want personal_model cache populated:
```
UPDATE personal_model pm
SET relationship_state = to_jsonb(rs.*) - 'person_id'
FROM relationship_state rs
WHERE pm.person_id = rs.person_id
  AND pm.relationship_state IS DISTINCT FROM to_jsonb(rs.*) - 'person_id';
```

## Test Script
- `scripts/relationship_check.py`
  - Env: `API_BASE`, `PERSON_ID`, `DATABASE_URL`, `TURN_TIMEOUT`, `REQUEST_TIMEOUT`.
  - Flow: sends a warm turn → waits → reads `relationship_state` from DB → prints cache.
  - If DB access is unwanted, you can instead run the SQL above in your editor to view state.

## Guardrails / Behavior
- Slow stage transitions: Warm → Supportive → Deepening → Strong Bond based on trust+attunement thresholds.
- No new emotion models; uses existing signals (personal_model.emotion, memory_short_term sentiment/tags).
- Tone influence only; no romantic/friendship role-play.
- Decimal-safe JSON; no heavy LLM calls (micro-tone only).

## TODO / Future Enhancements
- Auto-write `personal_model.relationship_state` cache inside the relationship hook (currently manual backfill).
- Better interaction_patterns (time-of-day, topic domains) sourced from memory summaries without new detectors.
- Integrate relationship deltas into tone engine weights more explicitly (keep within Build 36 rules).
