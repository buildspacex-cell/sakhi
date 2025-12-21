# Build 61 — Rhythm × Soul Integration (Codex Ready)

Status: implemented (read-only, additive)

## Scope
- Add `personal_model.rhythm_soul_state` (migration `infra/sql/20251204_build61_rhythm_soul_state.sql`).
- Fast turn-time frame (no LLM): `compute_fast_rhythm_soul_frame`.
- Deep worker sync (LLM allowed): `compute_deep_rhythm_soul`.
- Worker: `sakhi/apps/worker/rhythm_soul_deep.py`.
- Scheduler: daily + weekly enqueues in `sakhi/apps/worker/scheduler.py`.
- API: `GET /rhythm_soul/{person_id}` (fast + deep).
- turn_v2: returns `rhythm_soul_frame` in metadata/response.

## Key Files
- Migration: `infra/sql/20251204_build61_rhythm_soul_state.sql`
- Engine: `sakhi/core/rhythm/rhythm_soul_engine.py`
- Worker: `sakhi/apps/worker/rhythm_soul_deep.py`
- Scheduler hooks: `sakhi/apps/worker/scheduler.py`
- turn integration: `sakhi/apps/api/routes/turn_v2.py`
- API route: `sakhi/apps/api/routes/rhythm_soul.py`
- Tests: `tests/test_build61_rhythm_soul.py`

## Behavior
- Fast frame computes coherence, identity momentum, shadow disruption, rhythm tone adjust (<3ms).
- Deep sync writes a structured `rhythm_soul_state` to `personal_model` (LLM via worker only).
- Scheduler runs daily (default 6am) + weekly (Monday 8am) for `DEFAULT_USER_ID/DEMO_USER_ID`.
- `/v2/turn` exposes `rhythm_soul_frame`; no LLM in turn.
- `/rhythm_soul/{person_id}` returns `{ fast, deep }`.

## Ops Notes
- Ensure `DEMO_USER_ID`/`DEFAULT_USER_ID` is a valid `profiles.user_id`.
- Deep worker uses the LLM router; fast path is deterministic.
- No ingestion or embedding changes; Build 52 hashing untouched.

## Tests
- `poetry run pytest tests/test_build61_rhythm_soul.py`

## Out of Scope
- No ingestion/pipeline rewrites.
- No embeddings/hashing changes.
- No planner/rhythm base logic changes.
