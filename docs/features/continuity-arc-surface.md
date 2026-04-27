# Continuity Arc Surface

Date: 2026-03-07  
Last Updated: 2026-04-25 (technical debt + gap plan added)  
Scope: Continuity policy, arc surfacing, deep reflection, and simulation continuity mirror.

## Naming (as of 2026-04-25)

| Old term | Current term | Where |
|---|---|---|
| Life Occupancy | Your Threads | Mobile screen title + card heading |
| `"sakhi"` topic label | `"Start Up"` | Taxonomy label in `continuity/taxonomy.py` + `demo/continuity_taxonomy.py` |
| Reflection (screen) | Your Threads | Mobile `soul/topic-reflection` screen header |
| Reflection (kicker in thread modal) | Thread | Modal kicker |
| Deep Reflect / Run Deep | Deep Dive | Button label, pending messages, error messages |
| `topic_reflection` mode | unchanged | Backend API field (internal only) |
| Continuity Arc (card title) | unchanged | Still shown inside thread detail modal |

These are UI label changes only. All API fields (`topic_reflection`, `reflection_id`, `/continuity/reflection/*`) remain unchanged.

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

`apps/mobile/app/experience/converse/index.tsx` mirrors the production deep-reflection interaction from chat:
- Sends turns through standard `/v2/turn` and captures continuity topic metadata from product field `continuity` (`topic_key`, `topic_label`) instead of debug payloads.
- Exposes a `Deep Dive` button (formerly `Run Deep`) that queues `/continuity/reflection/run` in `mode=deep_answer` with the current query.
- Polls `/continuity/reflection/status` + `/continuity/reflection/result` and renders a distinct premium deep-answer bubble in chat.
- Uses authenticated bearer headers for all continuity calls so auth-bound person resolution works in production runtime.

`apps/mobile/app/soul/topic-reflection.tsx` provides the Your Threads profile-level longitudinal view:
- Fetches `/continuity/topics` and renders size-weighted thread bubbles (screen title: **Your Threads**, formerly Life Occupancy).
- Arc load (`/continuity/arc`) fires non-blocking — bubbles appear immediately, arc detail loads in the background.
- Topics are cached for 2 minutes; repeat navigation within that window skips the network fetch. Refresh button bypasses cache.
- Deep dive polling runs at 800ms initial interval (max 35 attempts), down from 2000ms / 70 attempts.
- If continuity policy is disabled (403), attempts one policy-enable call and retries topics before showing an empty state.
- Uses a glass-style visual treatment so the threads view feels clearly distinct from normal chat.

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

Simulation continuity compilation now includes a second-pass thread-aware resolver:
- `sakhi/apps/api/services/continuity/thread_resolver.py`
- ambiguous or `unknown` follow-up entries can attach to an already-confirmed thread when the evidence is strong enough
- close runner-up threads are now preserved as contextual attachments instead of forcing a single winner-or-drop outcome
- attachment uses multiple signals together (candidate anchor score, follow-up language, term overlap, light recency bias) instead of pure time bucketing
- entries that still cannot be attached are returned in `compiled["unresolved_entries"]` for auditability
- inferred attachments are marked with `membership_role="inferred"` so downstream/debug consumers can distinguish direct classification from thread attachment
- compiled topics now track `primary_selected_count`, `attached_selected_count`, `effective_selected_count`, and `related_selected_count` separately so chat Deep Reflect can unlock from real same-thread depth without counting projected cross-topic overlap

### Journal Identity Consistency

Active journal write paths now populate both `journal_entries.person_id` and `journal_entries.user_id` consistently.

- new writes resolve canonical owner columns before insert
- migration `sakhi/infra/scripts/migrations/0016_journal_person_id_backfill.sql` backfills legacy rows where `person_id` was null but `user_id` was present

This keeps continuity loaders, debug tools, and future surface code from depending on legacy `person_id OR user_id` fallbacks forever.

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
- `sakhi/tests/unit/services/test_thread_resolver.py`

Kala:
- `kala/tests/test_arc.py`

Web:
- `apps/web/app/lab/simulation/__tests__/continuityMirror.spec.ts`
- `apps/web/app/lab/simulation/__tests__/continuityArcDetail.spec.ts`

---

## Technical Debt & Gap-Closing Plan

> Added: 2026-04-25. Based on a full audit of the engine against what we claim in the pitch and in `docs/features/contextual-sequencing.md`.

---

### Audit Finding: What We Claim vs. What Is Built

The continuity engine is real, working, and more sophisticated than anything else in the market. But a precise audit against the pitch language and the contextual sequencing spec reveals three categories of gap:

**Category A — Works but doesn't generalise**
The classification and arc pipeline works well for the 12 hardcoded taxonomy anchors. For any topic outside those anchors (user discusses immigration, crypto investing, a health condition, a creative project), the classifier returns `anchor="unknown"` and produces nothing. The demo works because the Maya persona maps cleanly to the `sakhi/startup` anchor. A general user with general concerns will get no continuity.

**Category B — Built but heuristic, not semantic**
Decision state detection (questioning, leaning_yes, committed, deferred, reversed) is entirely keyword-based — scanning for defer_cues, reversal_cues, positive/negative cues from a hardcoded list. If a user expresses a shift without using those exact words, the state is not detected. The kala arc engine is strong; the input quality going into it is fragile.

**Category C — In the spec, not in the code**
Epistemic state transitions, affective trajectory, relational dimension, temporal decay per dimension, and thread forking are all described in `docs/features/contextual-sequencing.md` but none are implemented. We currently track 2 real dimensions: topic/facet and decision state. The 7-dimension claim in the competitive positioning is aspirational.

---

### The Gap Table

| Capability | Claimed | Built | Gap |
|---|---|---|---|
| Thread continuity across days | Yes | Yes — works | None |
| Decision state per entry | Yes | ✅ Lexical + LLM fallback (Phase 1.2) | Closed |
| Arc direction / trajectory | Yes | Yes — kala arc engine | Strong, no gap |
| Sub-threads | Yes | Yes | None |
| Cross-topic correlation | Yes | Yes | None |
| Adapts to any user topic | Implied | ✅ Personal taxonomy + LLM anchor inference (Phase 1.1) | Closed |
| Semantic state detection | Implied | ✅ LLM decision state inference for ambiguous entries | Closed |
| Epistemic state transitions | Doc'd | ✅ Built (Phase 2.1) — `epistemic_state` column + LLM inference | Closed |
| Affective trajectory | Partial | ✅ Built (Phase 2.2) — `affective_scalar` column, emotion→float mapping | Closed |
| Temporal decay per dimension | Doc'd | Not built | Lower priority |
| Thread forking/merging | Doc'd | Not built | Lower priority |

**Implementation status:** Phase 1 (1.1 + 1.2) and Phase 2 (2.1 + 2.2) complete as of 2026-04-20.
Files: `continuity/personal_taxonomy.py`, `continuity/llm_enrichment.py`, migration `0018_continuity_personal_taxonomy.sql`.
Worker pipeline: `continuity_enrichment` job enqueued per turn via `turn_v2.py` → `runner.py`.

---

### Phase 1 — Close the Production Gap (Pre-Seed Priority)

**Goal:** Make the engine work for any user on any topic, not just the 12 taxonomy personas.

#### 1.1 Hybrid Classification — LLM Fallback for Unknown Anchors

**The problem:** When lexical scoring produces `anchor="unknown"` or `ClassificationState.UNKNOWN`, there is no continuity. A user whose conversations don't use taxonomy keywords gets nothing.

**The fix:** A two-pass classifier.
- Pass 1: Run existing lexical classifier (fast, deterministic, zero cost). If `ClassificationState.CONFIDENT` → done.
- Pass 2: If `UNCERTAIN` or `UNKNOWN`, run a lightweight LLM call (gpt-4o-mini) to extract the topic anchor from the entry. Store the extracted anchor in `continuity_labels` as `source="llm_inferred"`.
- Future entries from the same user on the same topic can match against their inferred anchors — building a user-specific taxonomy over time.

**Where it goes:**
- New function `_llm_infer_anchor(text, person_id)` in `sakhi/apps/api/services/continuity/inference.py`
- Called from `classify_entry_for_continuity` when lexical result is UNCERTAIN/UNKNOWN
- Run async via background worker, not inline on turn (latency constraint)
- Store inferred anchors in a new `continuity_personal_taxonomy` table per person — `(person_id, anchor, label, keywords[], created_at, entry_count)`
- The classifier checks personal taxonomy before hardcoded taxonomy

**Result:** Engine works for any topic after 2–3 entries. First entry on an unknown topic: no continuity. Second entry: personal taxonomy seeded. Third entry: arc begins forming.

**Effort:** Medium — 2–3 days. The classifier structure and DB write path already exist.

---

#### 1.2 LLM-Assisted Decision State Inference

**The problem:** `_infer_entry` and `_derive_scalar` rely on keyword lists. Subtle state transitions are missed. "I keep going back to this" should fire `questioning`. "I think I've made up my mind" should fire `committed`. Neither will match the current cue lists.

**The fix:** When an entry's decision state is not derivable from keywords (no defer_cue, reversal_cue, positive_cue fires), run a targeted LLM extraction:
- Prompt: "Given this journal entry, classify the person's decision state on the topic as one of: questioning, leaning_yes, leaning_no, committed, deferred, reversed, resolved, or unknown. Return only the state label."
- Model: gpt-4o-mini (cheap, fast)
- Run async — not blocking the turn

**Where it goes:**
- `sakhi/apps/api/services/continuity/inference.py` — new `_llm_infer_decision_state(text, anchor)` function
- Called from the background worker pipeline, not inline
- Result stored in `continuity_labels.decision_state` (already has the column)
- Only fires when `decision_state is None` after lexical pass

**Effort:** Small — 1 day. The column and write path already exist.

---

### Phase 2 — Close the Multi-Dimensional Gap (Post-Demo, Pre-Seed Close)

**Goal:** Make the "multi-dimensional state tracking" claim accurate, not aspirational. The minimum viable set that earns the contextual sequencing differentiation: epistemic state + affective trajectory on top of the existing decision state + arc.

#### 2.1 Epistemic State Dimension

**The problem:** We claim Sakhi tracks "where your thinking is" — but we only track decision state (what you've decided). We don't track epistemic state (what you believe, how certain you are, whether a belief has updated).

**The fix:** Add `epistemic_state` as a second tracked dimension alongside `decision_state`.

States: `certain`, `uncertain`, `updating`, `contradicting`, `resolved`

Lexical markers to detect:
- certain: "I know", "clear to me", "I'm sure", "no doubt"
- uncertain: "I'm not sure", "I don't know", "unclear", "confused about"
- updating: "I used to think", "turns out", "changed my mind on this", "now I see"
- contradicting: "but then", "but also", "on the other hand"

Scalar mapping (same approach as decision_state → scalar):
- certain: 0.9, uncertain: 0.2, updating: 0.5, contradicting: 0.3, resolved: 1.0

**Where it goes:**
- Add `epistemic_state` field to the entry data model in `simulation_continuity.py` and `continuity_labels` table (migration required)
- Add `_derive_epistemic_state(text)` to the classifier
- The kala arc engine already handles multiple scalar series — pass `epistemic_scalar` alongside `decision_scalar`
- Arc features will then show epistemic trajectory (rising = growing certainty) alongside decision trajectory

**Effort:** Medium — 2–3 days. New column, new classifier function, wiring into arc.

---

#### 2.2 Affective Trajectory

**The problem:** `emotion_tagging.py` already exists in `sakhi/apps/api/services/memory/`. The continuity engine has `positive_cues`/`negative_cues` but treats them as binary flags, not a tracked trajectory. We lose the signal of whether anxiety about a topic is rising or falling over time.

**The fix:** Wire the existing emotion tagger output into the continuity arc as an affective scalar.
- Run `emotion_tagging` on each entry (already runs in the memory pipeline)
- Map emotion tags to an affective scalar: joy/calm/confident → +0.6 to +1.0, neutral → 0.0, anxious/frustrated/overwhelmed → -0.4 to -0.8
- Store as `affective_scalar` in `continuity_labels`
- Pass to kala arc as a third scalar series (alongside decision and epistemic)
- Arc features output `affective_direction` — is the emotional load around this topic rising or falling?

**Where it goes:**
- `emotion_tagging.py` output → `continuity_labels.affective_scalar` (new column, migration required)
- Minimal change to arc pipeline — kala already handles scalar series
- No new LLM calls — reuses existing emotion tagging

**Effort:** Small-medium — 1–2 days. Most infrastructure exists.

---

### Phase 3 — Complete the Contextual Sequencing Spec (Year 1)

These gaps are real but not blocking for demo or pre-seed. Build them as the user base grows and data volume supports them.

#### 3.1 Temporal Decay Model Per Dimension

**The problem:** A decision state from 6 months ago is treated equally to one from last week. Decision states are volatile; a `committed` from 3 months ago may be irrelevant now. Epistemic states are stickier. Affective states are the most volatile.

**The fix:** Per-dimension staleness functions applied when building the continuity pack:
- `decision_state`: half-life ~30 days. A `committed` entry from 90 days ago contributes 25% of its scalar weight.
- `epistemic_state`: half-life ~90 days. Beliefs update slowly.
- `affective_scalar`: half-life ~14 days. Emotional state is highly current.

**Where it goes:**
- New `_apply_dimension_decay(entries, dimension, half_life_days)` utility in `simulation_continuity.py`
- Applied in `_normalize_items` before arc construction
- Configurable via `ContinuityThresholdProfile` (already designed for version-controlled thresholds)

**Effort:** Medium — 2 days.

---

#### 3.2 Thread Forking

**The problem:** One discussion on "career direction" forks into "promotion" and "should I leave entirely" — two separate live threads that need individual tracking. Currently both stay in the `career` anchor, sub-threaded at best.

**The fix:** Extend the sub-thread system to support forking.
- When two sub-threads under the same anchor show divergent scalar trajectories (one rising, one falling) AND have ≥3 distinct moments each AND co-appear in entries → declare a fork
- Each fork branch becomes a trackable continuity object with its own arc
- The parent anchor becomes a container, not a leaf thread

**Where it goes:**
- `_detect_sub_threads` in `simulation_continuity.py` — add fork detection pass
- `build_simulation_continuity_arc` — handle forked arc construction
- New `fork_id` field in `continuity_labels`

**Effort:** Large — 4–5 days. Architecturally complex. Year 1 item.

---

### Priority Summary

| Phase | What it closes | Effort | When |
|---|---|---|---|
| 1.1 Hybrid classification | Engine works for any user topic | 2–3 days | Pre-seed |
| 1.2 LLM decision state | Detection quality on subtle entries | 1 day | Pre-seed |
| 2.1 Epistemic state | "Multi-dimensional" claim becomes accurate | 2–3 days | Post-demo |
| 2.2 Affective trajectory | Third tracked dimension, reuses existing tagger | 1–2 days | Post-demo |
| 3.1 Temporal decay | Recency weighting per dimension | 2 days | Year 1 |
| 3.2 Thread forking | Full contextual sequencing spec | 4–5 days | Year 1 |

**Total to close Category A and B gaps (production-ready for any user):** ~4 days
**Total to close Category C gaps (full spec):** additional ~10 days spread over Year 1

Phase 1 is the honest minimum before claiming the engine generalises. Phase 2 is the honest minimum before claiming multi-dimensional state tracking. Phase 3 completes the contextual sequencing spec.
