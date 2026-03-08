# Continuity Arc Surface

Date: 2026-03-07  
Scope: Continuity policy, arc surfacing, deep reflection, and simulation continuity mirror.

## Summary

Sakhi now has a policy-gated continuity layer that can:
- Compile continuity topics from journal history.
- Surface deterministic continuity arcs for a selected anchor.
- Inject a compact continuity pack into `turn_v2` prompt metadata.
- Run deep reflection jobs over a selected continuity topic.
- Render precompiled continuity mirrors and spine explainability in simulation UI.

This layer is deterministic and auditable; it does not require LLM classification to build arc structure.

## Backend Surface

### Routes

`sakhi/apps/api/routes/continuity.py` registers:
- `GET /continuity/policy`
- `PUT /continuity/policy`
- `POST /continuity/policy/enable`
- `POST /continuity/policy/exclude`
- `POST /continuity/label`
- `GET /continuity/topics`
- `GET /continuity/arc`
- `POST /continuity/reflection/run`
- `GET /continuity/reflection/status`
- `GET /continuity/reflection/result`

`POST /continuity/reflection/run` now supports two explicit modes:
- `mode="deep_answer"` + optional `user_query` for question-led whole-history answers
- `mode="topic_reflection"` (default) for longitudinal reflection without requiring an active question

### Services

Core continuity services live in `sakhi/apps/api/services/continuity/`:
- `service.py`: policy checks, topic listing, arc retrieval, event logging.
- `chat.py`: continuity pack builder for `turn_v2`.
- `compiler.py`: deterministic continuity compilation.
- `reflection.py`: async deep reflection job lifecycle.
- `adapters.py`: DB adapters and policy/label persistence.

### Turn Integration

`sakhi/apps/api/routes/turn_v2.py` now calls `build_continuity_pack(...)` and attaches `metadata_payload["continuity_pack"]` when available.

`sakhi/apps/api/services/conversation_v2/conversation_reasoner.py` consumes this as a hidden prompt section (`LONGITUDINAL CONTINUITY`) to improve coherence without exposing historical snippets unless requested.

The turn-level continuity pack now includes richer compact history for normal chat:
- `history_compact.span_days`, `element_count`, `phase_count`
- `history_compact.phase_path` (sampled timeline across phases)
- `history_compact.anchor_points` (early/middle/recent historical anchors)
- `history_compact.qualitative_arc_summary` (deterministic whole-thread narrative)
- `history_compact.qualitative_mode` (`detailed` when `surface.detail_allowed=true`, `mirror_only` otherwise)
- `history_compact.decision_ledger` (chronological decisions from journal decision states + acknowledged Sakhi suggestions)

This keeps prompt context concise while giving the model more longitudinal structure than start/pivot/current alone.
Prompt rendering now uses natural chronology labels (`First/Then/Now`, `Early/Middle/Recent`) instead of timestamp-first bullet prefixes, so continuity reads as sequence narrative while preserving deterministic ordering.

The hidden continuity prompt section is now explicitly framed as:
- "This is the history on this topic"
- "This is what we know about the person on this topic"
- "Current query now"

Prompt language is intentionally narrative-first (history/person/query) and avoids score-heavy framing for turn-time continuity guidance.
Both prompt paths now explicitly prioritize the current query response, with history/person context used only as grounding for coherence.

## Data Model

Migrations:
- `sakhi/infra/scripts/migrations/0013_continuity_arc.sql`
  - `continuity_surface_policy`
  - `continuity_labels`
- `sakhi/infra/scripts/migrations/0014_continuity_deep_reflection.sql`
  - `deep_reflections`

## Web Surface

### API Proxies

`apps/web/app/api/continuity/**/route.ts` proxies continuity endpoints for the web client.

### Converse UI

`apps/web/app/experience/converse/page.tsx` adds:
- Continuity policy load/toggle.
- Active continuity topic chip from debug metadata.
- Deep reflection run + status polling + result insertion.

## Mobile Surface

`apps/mobile/app/experience/converse/index.tsx` now mirrors the production deep-reflection interaction from chat:
- Sends turns through standard `/v2/turn` and captures continuity topic metadata from product field `continuity` (`topic_key`, `topic_label`) instead of debug payloads.
- Exposes a `Run Deep` action that queues `/continuity/reflection/run` in `mode=deep_answer` with the current query.
- Polls `/continuity/reflection/status` + `/continuity/reflection/result` and renders a distinct premium deep-answer bubble in chat.
- Uses authenticated bearer headers for all continuity calls so auth-bound person resolution works in production runtime.

`apps/mobile/app/soul/topic-reflection.tsx` adds a profile-level longitudinal view:
- Fetches `/continuity/topics` for the person and visualizes topic occupancy as size-weighted bubbles.
- Loads `/continuity/arc` for the selected topic and renders included moments as relative-size arc bubbles.
- If continuity policy is disabled, it attempts one policy-enable call and retries topics before showing an error state.
- Uses a glass-style visual treatment so topic reflection feels clearly distinct from normal chat.

### Simulation Ask-Sakhi Debug Surface

`/demo/simulation/add-journal` now requests `debug=1` from `/v2/turn` and returns
`turn_debug` in the API payload.

`apps/web/app/lab/simulation/client.tsx` now renders a per-turn debug inspector after
"Ask Sakhi" submissions so we can verify:
- continuity topic selection
- continuity evidence count and snippets passed into prompt assembly
- raw prompt text (`base_prompt`) sent to the model
- one-click deep reflection run/status/result over the surfaced continuity topic
- always-visible deep reflection control with disabled-state reason when no topic was selected for the turn

### Deep Reflection Persistence Hardening

`sakhi/apps/api/services/continuity/reflection.py` now uses a resilient
done-write path:
- First attempts full persistence with `window_start`/`window_end`.
- Falls back to payload-only persistence (`status`, `inputs_hash`, `result_json`)
  if window timestamp writes fail due schema drift/type mismatch.

This keeps deep reflection test flows functional even when `deep_reflections`
window column shapes differ across local environments.

### Deep Reflection Chat Output Contract

Deep reflection result payloads now include a deterministic `chat_response`
string synthesized from origin, pivot, current stage, recurring tension, and
open question fields. This gives web clients a direct chat-ready response
without reformatting fallback fragments.

`apps/web/app/lab/simulation/client.tsx` and
`apps/web/app/experience/converse/page.tsx` now:
- poll `status` with no-store + cache-busting
- probe `result` during polling and once at timeout boundary
- render the final chat response as soon as `result.status=done`, even if
  status updates lag behind result persistence

### Deep Reflection LLM Packet Contract

When the app-level LLM router is available, deep reflection now sends a compact
LLM packet and stores both deterministic and LLM outputs:
- `surface`: continuity surface policy snapshot (`detail_allowed`, `mirror_allowed`, scores, blocked reason)
- `arc_compact_global`: topic-wide compaction (origin, pivots, current stage, recurring tensions, phase compaction)
- `recent_episode_compact`: top recent episodic summaries selected by topic overlap
- `evidence_anchors`: phase-distributed continuity evidence snippets
- `delta_since_last_reflection`: stage/tension/pivot delta versus prior completed reflection
- `latest_turn_context`: latest conversation turns + personal-model state hints
- `response_contract`: voice/length/question constraints plus surface-derived gating (`detail_allowed`, `mirror_allowed`, `nudge_policy`)
  - `deep_answer`: long-form (`180-280` words) with required labeled sections:
    `Direct answer`, `History anchors`, `Recommended path`, `Alternative path`, `Risk + next 7-day action`
  - `topic_reflection`: concise longitudinal mode (`80-140` words), single paragraph

Prompt guardrails enforce topic-only grounding and respect surface policy:
- if `detail_allowed=false`, reflection stays mirror-only (no prescriptive next-step coaching)
- unrelated turn concerns are excluded from synthesis

Deep reflection prompt messages now render compact plain-language sections from the packet (history, person context, current query, response contract) instead of embedding full raw packet JSON in the LLM user message.
Deep reflection prompt instructions explicitly prioritize the current query while constraining history to grounding context.
For `deep_answer` mode, provided `user_query` is preferred over reconstructed turn context and is marked with source metadata in the packet/result payload (`query_context.active_query_source`).
For `deep_answer`, a one-pass quality gate now auto-regenerates the LLM reply when contract checks fail (too short/too long or missing required sections), and persists gate diagnostics in `llm_reflection.quality_gate` + `llm_reflection.generation_attempts`.

Result payload additions:
- `deterministic_chat_response`
- `chat_response_source` (`llm` or `deterministic`)
- `llm_reflection` (`input_packet`, `prompt_messages`, `provider/model`, usage, error/fallback state)

## Simulation Surface

`sakhi/apps/api/services/demo/simulation_continuity.py` compiles continuity topics/arcs for simulation artifacts and supports ad-hoc arc construction.

`apps/web/app/lab/simulation/client.tsx` renders:
- Continuity topic selector.
- Continuity Mirror card.
- Continuity Spine explainability view.
- Included moments panel.

`apps/web/app/lab/simulation/continuityMirror.ts` provides deterministic copy generation for arc summary lines.

## Tests Added

Backend:
- `sakhi/tests/unit/services/test_continuity_chat.py`
- `sakhi/tests/unit/services/test_continuity_reflection.py`
- `sakhi/tests/unit/services/test_continuity_service.py`
- `sakhi/tests/unit/services/test_simulation_continuity.py`
- `sakhi/tests/unit/services/test_simulation_continuity_benchmark.py`

Kala:
- `kala/tests/test_arc.py`

Web:
- `apps/web/app/lab/simulation/__tests__/continuityMirror.spec.ts`
- `apps/web/app/lab/simulation/__tests__/continuityArcDetail.spec.ts`
