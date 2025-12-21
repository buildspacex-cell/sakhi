# Build 77 — Inner Dialogue Engine v1

This build introduces a private, deterministic inner-dialogue layer that synthesizes guidance intent, tone, and signals from existing alignment/coherence/narrative/pattern/emotion data. It stores the result in `inner_dialogue_cache` and `personal_model.inner_dialogue_state`, exposes it via API, and injects it into turn responses.

## What changed
- Migration `infra/sql/20251220_build77_inner_dialogue.sql` creates `inner_dialogue_cache` and `personal_model.inner_dialogue_state`.
- Engine `sakhi/apps/engine/inner_dialogue/engine.py` computes reflections, guidance intention, tone, and signals using alignment, coherence, narrative arcs, pattern sense, emotion loop, and wellness snapshots (deterministic, no LLM).
- Worker `sakhi/apps/worker/tasks/inner_dialogue_refresh.py` writes cache + personal_model; scheduled daily and on ingestion via `scheduler.py`.
- Turn pipeline (`turn_v2`) now computes an inner-dialogue frame per turn and passes it into reply metadata.
- New API route `/v1/inner_dialogue` returns the latest dialogue for a person.
- Tests `tests/test_build77_inner_dialogue.py` cover rule paths and API response.

## How to use
- Call `GET /v1/inner_dialogue?person_id=<uuid>` to fetch the latest inner-dialogue state.
- Turn responses now include `inner_dialogue` metadata (`guidance_intention`, `tone`, `signals`, `reflections`).

## Notes
- No ingestion or embedding changes.
- All computation is deterministic and runs in workers or lightweight turn-time logic (no LLM calls).
