# Changelog

All notable changes to Sakhi will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Governance kernel (kala)** — pure-computation governance with constraint evaluation (11 operators), drift gating, contradiction detection (5 categories), objective versioning, and 552 tests
- **Kala–Sakhi integration** — GovernanceGate wired into conversation pipeline via `services/governance/service.py`
- **Continuity Arc surface (chat + API)** — policy-gated continuity topics/arcs, per-source exclusions, and deep reflection run/status/result endpoints under `/continuity/*`
- **Turn-level continuity injection** — `turn_v2` now builds a continuity pack and passes hidden longitudinal context into prompt construction
- **Simulation continuity compiler + mirror UI** — precomputed continuity topics/arcs in simulation artifacts, plus continuity mirror/spine explainability views in lab simulation
- **Kala arc primitives** — new `kala.arc` module for deterministic temporal arc construction, segmentation, and feature extraction
- **"A Day with Sakhi" simulation demo** — three-act governance scenario (Illusion → Reveal → Divergence), interactive governance evaluation
- **30-day conversation replay** — real persona pipelines (Vidhya, Diya, Big D) with auto-play, speed controls, drift visualization
- **Simulation profile updater** — add journal entries to simulation profiles through real pipeline (`/demo/simulation/add-journal`)
- **Simulation Ask-Sakhi turn debug** — simulation journal submissions now surface continuity evidence and prompt payload (`turn_debug`) for fast local product testing
- **Simulation deep reflection tester** — Ask-Sakhi debug panel now supports one-click deep reflection run/status/result over the surfaced continuity topic, with disabled-state guidance when a topic is unavailable
- **Body health override** — physical symptom responses bypass generic Ayurvedic reasoning
- **Email Intelligence v1** — Gmail OAuth integration, LLM-powered digest (triage, action items), signal extraction (subscriptions, avoidance, boundaries, cognitive load)
- **Knowledge graph-powered symptom recommendations** + Prompt Playground
- **Web onboarding flow** — 8 screens, 19 questions, progressive OS calibration
- **Mobile onboarding, voice, and auth** with Ayurvedic knowledge graph
- **Full-brain simulation harness v2** — deep-dive visualizations for coherence, alignment, identity, themes
- **Context routing** — tiered context intelligence with hybrid router
- **Comprehensive test suite** — e2e, integration, and unit tests
- **Continuity + arc test suites** — backend continuity unit tests, simulation continuity benchmark tests, kala arc tests, and web continuity mirror specs
- **Docker worker service** — `Dockerfile.worker` for Railway worker deployment
- Session memory for Claude (`.claude/MEMORY.md`, `.claude/CURRENT_TASK.md`)
- Quick task shortcuts, pre-commit hooks, code generators, feature flags, dev status dashboard

### Changed
- **Removed OpenRouter provider** — all LLM calls now use OpenAI directly (GPT-4o, GPT-4o-mini)
- **Separated THINK vs RESPOND** in SAKHI_INSTRUCTIONS prompt for clearer reasoning
- **Optimized conversation pipeline** — reduced turn latency from 15s to 6-8s
- **Adaptive response** — personalized WHY required in every response, adaptive prompt placed first
- **Environment source-of-truth clarified** — docs now explicitly define local runtime precedence (`.env.local` → `.env`), production env ownership (Railway/Vercel dashboards), and template-only role of `.env.example` files
- **Env contract gate in build workflow** — `sakhi/infra/scripts/check_env.py` now supports profiles (`local`, `prod_api`, `prod_web`, `ci`), `make verify` now enforces local env contract checks, and CI runs a `ci` profile pre-test validation
- **Localhost web auth bypass** — development-only bypass for protected web routes via `DEV_AUTH_BYPASS_PERSON_ID` (defaults to `a1b2c3d4-1111-4000-8000-000000000001`)
- Reorganized monorepo structure and test directories
- Upgraded Next.js to 14.2.35 (patched CVE-2025-55184 and CVE-2025-67779)

### Fixed
- **Governance seeder race condition** — ON CONFLICT guards for concurrent seed requests
- **JSONB parsing** — asyncpg returns JSONB as strings; added `_parse_json()` helpers in coherence/alignment engines
- **Alignment engine wrong SQL** — was querying `long_term->>'emotion_state'` instead of direct `emotion_state` column
- **Identity momentum guard** — relaxed soul_state key check to accept all populated states
- **Theme inference for simulation** — episodic memory fallback when reflections/goals are empty
- **Lost-in-the-middle** — repeat key known facts before user message
- **Dedup facts, strip jargon** from inferences with concrete generic-vs-personal examples
- **BM25 JSONB type cast** + asyncpg JSONB string parsing
- **Auth redirect loops** — infinite redirect on login, onboarded user redirect past welcome screen
- **Debug panel** — wire memory recalls, engine states, compound symptom extraction
- **Deep reflection persistence fallback** — continuity reflection now falls back to payload-only persistence if `window_start/window_end` timestamp writes fail
- **Simulation deep reflection polling timeout** — continuity reflection proxy routes now force no-store responses and the simulation poller adds cache-busting params so status transitions (`queued` → `running` → `done`) are not stuck on stale cached payloads
- **Deep reflection chat response surfacing** — reflection results now include a deterministic `chat_response` field, and web pollers probe `/continuity/reflection/result` during status waits so completed reflections reliably render as chat output in simulation and converse UI
- **Deep reflection LLM synthesis contract** — deep reflection now composes a compact packet (`arc_compact_global`, `recent_episode_compact`, `evidence_anchors`, `delta_since_last_reflection`, `latest_turn_context`, `response_contract`) and, when router is available, generates user-facing `chat_response` via LLM while preserving deterministic fields plus `chat_response_source` and `llm_reflection` debug payload
- **Deep reflection topic drift guardrails** — LLM packet now filters latest-turn context to topic-matched user turns only and fixes episodic retrieval matching (`memory_episodic.person_id` or `user_id`) to avoid unrelated work/family bleed into topic-scoped reflections
- **Deep reflection surface-policy carry-through** — LLM packet now includes continuity `surface` flags and response-contract gates (`detail_allowed`, `mirror_allowed`, `nudge_policy`) so detail-blocked runs stay mirror-only and avoid prescriptive drift
- **Turn-level continuity compaction depth** — hidden `LONGITUDINAL CONTINUITY` prompt block now carries compact thread stats, sampled phase path, and historical anchor moments in addition to start/pivot/current signals so normal chat gets richer longitudinal grounding
- **Turn-level qualitative arc summary** — continuity packs now include deterministic `history_compact.qualitative_arc_summary` plus `qualitative_mode` (`detailed` vs `mirror_only`) so each turn gets a compact whole-story narrative without overloading the prompt
- **Turn-level decision ledger + simple history framing** — continuity packs now include `history_compact.decision_ledger` (journal decisions + acknowledged Sakhi suggestions), and the hidden prompt section now explicitly frames: topic history, what we know about the person, and the current query
- **Turn-level chronology phrasing** — hidden continuity prompt rendering now prefers natural sequence labels (`First/Then/Now`, `Early/Middle/Recent`) over raw date-range prefixes, preserving order while keeping context language-first for LLM synthesis
- **Simulation typing shortcut guard** — replay keyboard shortcuts now ignore focused text inputs (including the Continue Conversation textarea), so `Space` inserts normally instead of toggling autoplay while typing
- **Continuity prompt simplification (chat + deep reflection)** — both continuity prompt paths now use a language-first structure (`History on this topic`, `What we know about this person`, `Current query now`), reduce score/count-heavy framing in hidden continuity context, and stop sending full raw packet JSON in deep reflection LLM prompts
- **Continuity prompt query-priority rule** — both normal continuity chat and deep reflection prompts now explicitly prioritize answering the current query directly, while using history/person context only for grounding coherence
- **Deep reflection mode split (deep_answer vs topic_reflection)** — `/continuity/reflection/run` now accepts `mode` and optional `user_query`; deep-answer runs use the provided query as primary input while topic-reflection runs stay longitudinal, and simulation/converse UIs now expose separate actions for both modes
- **Deep-answer response contract + regeneration gate** — deep-answer runs now target a longer structured reply (`180-280` words with required sections: direct answer, history anchors, recommended path, alternative path, risk + next 7-day action) and auto-regenerate once when the first draft misses contract checks
- **Normal-chat response contract update** — turn prompt now targets a focused tactical answer (`60-120` words, max 1 question) instead of the prior ultra-short `30-50` style
- **Rhythm planner path deferred by default** — turn-time `rhythm_planner_alignment` loading is now disabled unless `SAKHI_ENABLE_RHYTHM_PLANNER_ALIGNMENT=1`, preventing rhythm table dependencies from impacting core turn flows
- **Weekly rhythm rollup deferred by policy** — `weekly_rhythm_rollup` is now disabled by default (`SAKHI_ENABLE_WEEKLY_RHYTHM_ROLLUP=0`) and scheduler enqueue is skipped unless explicitly enabled
- **Production route guardrails** — internal operator routes (`/lab`, `/dev`, `/demo`, `/admin`) are now blocked by default in production runtime unless `SAKHI_ENABLE_INTERNAL_ROUTES_IN_PROD=1`
- **Health/readiness hardening** — `/health` now reports dependency-aware readiness (DB required, Redis optional) with proper `503` degradation, plus explicit `/health/live` and `/health/ready` endpoints
- **External alerting sink wiring** — API unhandled exceptions and worker job/crash failures now route through `apps/api/core/monitoring.py` to optional Sentry (`SAKHI_SENTRY_DSN`) and/or webhook on-call sinks (`SAKHI_ALERT_WEBHOOK_URL`) with dedupe window controls
- **Context audit harness fix** — `scripts/context-audit.sh` now validates the actual `Makefile quick-test` target file list instead of checking a stale removed path
- Production errors: synthesis param, JSONB serialization
- Vercel build: styled-jsx React conflict, env var injection, monorepo .env.production

---

## [0.1.0] - 2026-02-01

### Added
- Initial Sakhi MVP
- FastAPI backend with 75+ routes
- Next.js 14 frontend
- Ayurvedic-informed conversation engine
- Memory system (episodic, semantic, graph)
- Friction Framework for user state
- Voice integration (STT/TTS)
- Desktop agent foundation
