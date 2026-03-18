# Turn v2 Conversation Audit (Rerun)
Date: 2026-02-16  
Scope: `POST /v2/turn` deterministic intelligence loading, intent/module routing, metadata assembly, prompt construction, LLM call, and post-reply persistence.

Commit observed: `02ede6a`

## What I Re-Validated
- Static trace of live path:
  - `sakhi/apps/api/routes/turn_v2.py`
  - `sakhi/apps/api/services/turn/deterministic_context_loader.py`
  - `sakhi/apps/api/services/context_router.py`
  - `sakhi/apps/api/services/conversation_v2/conversation_engine.py`
  - `sakhi/apps/api/services/conversation_v2/conversation_reasoner.py`
  - `sakhi/apps/api/core/llm.py`
- Checks executed:
  - `poetry run ruff check` (targeted files)
  - `poetry run pytest -q sakhi/tests/unit/services/test_context_router.py sakhi/tests/unit/services/test_conversation_reasoner.py`
  - `poetry run pytest -q sakhi/tests/unit/services/test_response_quality.py sakhi/tests/unit/services/test_response_sensing.py`

## Current Flow (Now)
1. Session and history load in `sakhi/apps/api/routes/turn_v2.py:540`.
2. Optional vision processing in `sakhi/apps/api/routes/turn_v2.py:566`.
3. Orchestrator write/lightweight NLP with `skip_llm=True` in `sakhi/apps/api/routes/turn_v2.py:672`.
4. Deterministic context load + brain state load in parallel in `sakhi/apps/api/routes/turn_v2.py:790`.
5. Pending agent task + intent evolution fetched pre-router in `sakhi/apps/api/routes/turn_v2.py:809`.
6. Intent-based module routing in `sakhi/apps/api/routes/turn_v2.py:830`.
7. Tier 2 enrichments gated by active modules (moment/scheduling/body/email/etc.) across `sakhi/apps/api/routes/turn_v2.py:990` onward.
8. Metadata payload assembled in `sakhi/apps/api/routes/turn_v2.py:1638`.
9. Prompt built in `sakhi/apps/api/services/conversation_v2/conversation_reasoner.py:506`, LLM called in `sakhi/apps/api/services/conversation_v2/conversation_engine.py:208`.
10. Response returned, post-reply tasks run fire-and-forget in `sakhi/apps/api/routes/turn_v2.py:1801`.

## Improvements Since Prior Audit
1. Shared deterministic loader is now used in live path:
   - `sakhi/apps/api/routes/turn_v2.py:792`.
2. Pending task routing signal ordering is fixed:
   - task fetch before router in `sakhi/apps/api/routes/turn_v2.py:809`
   - `has_pending_task` passed at `sakhi/apps/api/routes/turn_v2.py:837`.
3. Vision context is now consumed in prompt:
   - `sakhi/apps/api/services/conversation_v2/conversation_reasoner.py:833`.
4. Duplicate meta-context pattern build was disabled in `call_llm`:
   - `sakhi/apps/api/core/llm.py:58`.
5. Agentic pre-LLM search was intentionally disabled (avoids wasted cost):
   - `sakhi/apps/api/routes/turn_v2.py:661`.

## Findings (Severity-Ordered)

### P0: Session compression enqueue references undefined `entry_id`
- In session setup, compression enqueue uses `entry_id` before it exists:
  - `sakhi/apps/api/routes/turn_v2.py:551`.
- This throws and gets swallowed by the surrounding `except`, so compression enqueue is effectively broken.
- Confirmed by lint: `F821 Undefined name entry_id`.

### P0: Reflection trace persistence still references undefined `turn_id`
- Reflection trace payload uses `turn_id` with no definition in `turn_v2` scope:
  - `sakhi/apps/api/routes/turn_v2.py:1012`.
- Error is swallowed and reflection trace silently drops.
- Confirmed by lint: `F821 Undefined name turn_id`.

### P1: `skip_llm=True` still suppresses intents/triggers used for tone/metadata
- Route uses `orchestrate_turn(..., skip_llm=True)`:
  - `sakhi/apps/api/routes/turn_v2.py:677`.
- Orchestrator returns before intents/rhythm/meta trigger derivation in skip mode:
  - `sakhi/apps/api/services/conversation/orchestrator.py:123`.
- Yet metadata still relies on those fields:
  - `sakhi/apps/api/routes/turn_v2.py:1643`
  - `sakhi/apps/api/routes/turn_v2.py:1645`.
- Net: routing is improved by triage/evolution intents, but intent-driven tone and trigger-specific shaping remain underpowered.
- **2026-03-19 update:** Moot for continuity MVP. The tone/metadata fields this was underpowering (microreg, empathy) are now backgrounded and no longer on the hot path. Continuity pack drives response quality, not intent-derived tone shaping. Revisit when rebuilding tone/empathy modules over the continuity foundation.

### P1: Deterministic context is integrated but still partially duplicated
- Turn loads brain state directly:
  - `sakhi/apps/api/routes/turn_v2.py:231`.
- Turn also loads deterministic context, which loads brain state again:
  - `sakhi/apps/api/services/turn/deterministic_context_loader.py:362`.
- Deterministic friction/body are loaded:
  - `sakhi/apps/api/services/turn/deterministic_context_loader.py:883`.
- But route recomputes friction/body separately for prompt payload:
  - friction recompute `sakhi/apps/api/routes/turn_v2.py:1035`
  - body state recompute `sakhi/apps/api/routes/turn_v2.py:1200`.
- Impact: avoidable DB/compute overhead and potential drift between similar fields.
- **2026-03-19 update:** Fully resolved. `load_deterministic_context()` replaced with `DeterministicContext()` empty stub — zero DB reads, zero duplication. All consuming modules (moment_model, Tier 1 fast compute, friction/body) were parked for the continuity MVP, making the entire loader dead weight.

### P2: Post-reply persistence remains non-durable
- Critical post-reply work is launched with `asyncio.create_task`:
  - `sakhi/apps/api/routes/turn_v2.py:1801`.
- Process restarts or cancellation can drop updates (unless jobs were already enqueued to durable workers).
- **2026-03-19 update:** Accepted for continuity MVP. The post-reply tasks (microreg, tone, empathy refresh) are low-stakes state updates — losing one on a process restart doesn't break continuity or corrupt user data. The continuity pack reads from `conversation_turns` which is persisted synchronously via `append_turn` before the fire-and-forget block. Address when moving to production hardening.

### P2: Coverage still misses route-level contract failures
- Unit tests for router/reasoner are good and currently passing.
- Route-level tests still do not assert:
  - reflection trace path validity,
  - session compression enqueue path,
  - metadata contract from `turn_v2` to `build_prompt`.
- **2026-03-19 update:** Accepted for continuity MVP. Reflection trace is parked. Session compression enqueue is the one live gap — worth a smoke test before investor demo to confirm sessions accumulate and compress correctly after 16 turns. Full route-level contract tests are post-MVP work.

## Test/Check Result Snapshot
- `pytest` status: passing for selected service suites.
- `ruff` status: failing, with two correctness-critical `F821` issues and many hygiene/typing warnings.

## Evaluation (Current State)
- Correctness: improved, but blocked by two hot-path undefined-name bugs (P0).
- Deterministic intelligence usage: materially better than prior audit (loader + router + prompt consumption alignment improved).
- Efficiency: still mixed due duplicated state loading/recomputation.
- Reliability: still medium because post-reply path is best-effort fire-and-forget.

Overall: **strongly improved architecture fit, but not production-clean until the two P0 defects are fixed.**

## Priority Remediation
1. Hotfix correctness:
   - Replace undefined `entry_id` at session compression enqueue.
   - Define/use a valid `turn_id` for reflection trace.
2. Signal integrity:
   - Either compute lightweight intents/triggers inline (without full LLM path) or stop wiring empty fields into tone/metadata.
3. Converge deterministic path:
   - Use one source for brain/friction/body in the route to avoid duplicated computation and drift.
4. Hardening:
   - Move critical post-reply writes to guaranteed durable queue handoff.

---

## MVP Pipeline Simplification (2026-03-19)

To focus the pipeline on continuity for the investor MVP, the following modules were parked in `turn_v2.py`. All code is preserved in git — restore from history when building these features over the continuity foundation.

### Parked (stubbed to empty, no runtime cost)

| Module | What it did | Where to restore |
|---|---|---|
| `ALL_MODULES` routing | Every turn ran all modules unconditionally | `active_modules = ALL_MODULES` at line ~929 |
| Tier 1 fast compute | `compute_fast_narrative`, `compute_alignment`, `compute_fast_rhythm_soul_frame`, `compute_fast_esr_frame`, `compute_fast_identity_momentum`, `compute_fast_identity_timeline_frame` — wrote to DB each turn | Restore block after `active_modules` assignment |
| Inner dialogue + nudge state | `inner_dialogue_engine.compute_inner_dialogue` + nudge_state DB read | Gated by `SAKHI_ENABLE_INNER_DIALOGUE=1` flag |
| Micro goals | Background task triggered by intent phrases ("I want", "I need to", etc.) | Restore `asyncio.create_task(micro_goals_service.create_micro_goals(...))` |
| Moment model + evidence pack | `compute_moment_model`, `select_evidence_anchors` (DB query), `compute_deliberation_scaffold`, reflection trace persistence | Restore `"moment" in active_modules` block |
| Recommendations | `build_recommendation_context` + `generate_personalized_recommendations` (LLM call when reactive) | Restore recommendations block |
| Causal reasoning | `explain_friction` (LLM call when drift > 15%), `explain_symptom` (LLM call on symptom keywords) | Restore `"causal" in active_modules` block |
| Health trends | `compute_health_trends` (14-day DB query, body module) | Restore `"body" in active_modules` block |
| Email context | `get_email_context_for_conversation`, `get_contact_preferences` | Restore `"email" in active_modules` block |
| Scheduling | Full scheduling pipeline: confirmation detection, intent parsing, availability lookup, mesh coordination, relationship nudges, calendar query | Restore from git — largest block, search `# scheduling logic removed` |

| `load_deterministic_context()` | 5 DB reads: personal_model row, memory_context_cache check, get_full_friction_state + memory_episodic.state_vector, session_continuity, conversation_turns gap-hours | All output fed parked modules — replaced with `DeterministicContext()` empty stub |
| Governance gate | 3 DB reads (constraints, objectives, 14-day event ledger) + Kala `gate.evaluate()` — produces constraint/contradiction/objective guard injected into prompt | MVP user has no constraints set up → always returns `action="allow"`, `governance_guard=""` — stubbed to empty. Restore when onboarding surfaces constraint/objective setup |
| `load_recent_intent_evolution()` | 1 DB read from `intent_evolution` table — returns recent intent evolution records, merged into `combined_intents` → metadata payload | `build_prompt()` never consumed `combined_intents` → dead weight on every turn. Stubbed to `evolution_intents = []`. Restore when rebuilding intent-driven tone/metadata shaping over the continuity foundation |

### Still active (continuity MVP path)

- Session + conversation history load
- Continuity pack (`build_continuity_pack` — topic arc, anchors, phase path, decision ledger)
- Recall + patterns (when no topic active)
- Post-reply fire-and-forget (microreg, tone, empathy refresh)
