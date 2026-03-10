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
- **Mobile continuity premium surfaces** — profile now includes a glass-style continuity reflection page with life-occupancy bubble mapping from continuity topics/arcs and threaded deep-reflection synthesis
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
- **Environment source-of-truth clarified** — docs now explicitly define local runtime precedence (`.env.local` → `.env`) and production env ownership (Railway/Vercel dashboards); template env files were removed from the repository
- **Known-user MVP privacy/trust rollout guide** — added concrete hardening checklist for founder-access risk mitigation (break-glass access, log/debug lockdown, retention/deletion policy, and beta trust gate wiring in deploy checklist)
- **Env contract gate in build workflow** — `sakhi/infra/scripts/check_env.py` now supports profiles (`local`, `prod_api`, `prod_web`, `ci`), `make verify` now enforces local env contract checks, and CI runs a `ci` profile pre-test validation
- **Localhost web auth bypass** — development-only bypass for protected web routes via `DEV_AUTH_BYPASS_PERSON_ID` (defaults to `a1b2c3d4-1111-4000-8000-000000000001`)
- **Mobile dev profile override (iOS/Expo)** — development-only bypass via `EXPO_PUBLIC_DEV_BYPASS_PERSON_ID` to run the full mobile experience against a fixed `person_id` (for example Vidhya simulation profile) without Supabase login
- **Internal TestFlight fixed-profile build profile** — added `apps/mobile/eas.json` profile `testflight-vidhya` plus release override envs (`EXPO_PUBLIC_RELEASE_BYPASS_*`) so internal Fastlane/EAS TestFlight builds can open directly on `a1b2c3d4-1111-4000-8000-000000000001` without affecting normal production builds
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
- **Deep reflection ownership checks** — continuity reflection status/result reads are now scoped by both reflection id and `person_id`, blocking cross-user UUID-only fetches
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
- **Deep reflection mode split (deep_answer vs topic_reflection)** — `/continuity/reflection/run` now accepts `mode` and optional `user_query`; deep-answer runs use the provided query as primary input while topic-reflection runs stay longitudinal, and clients can route query-scoped deep answers separately from topic-arc reflections
- **Mobile deep-answer contract hardening** — mobile chat now reads continuity topic from non-debug `/v2/turn` field (`continuity.topic_key/topic_label`), sends auth bearer headers on continuity endpoints for prod-bound person checks, and profile reflection auto-retries after continuity-policy enable when needed
- **Turn continuity readiness signal** — `/v2/turn` non-debug continuity payload now includes `continuity.deep_reflect` (`ready`, `reason`, `mirror_allowed`, `detail_allowed`, `selected_count`, `min_moments`) so clients can unlock Deep Reflect from a single response contract without separate readiness inference
- **Mobile Deep Reflect gating hardening** — chat now uses `/v2/turn` non-debug `continuity.deep_reflect` readiness as the source of truth (topic + depth + surface gates), with dynamic composer messaging (`A clear space to think out loud.` / unlock guidance) and in-thread `Run Deep` execution for query-aware deep answers
- **Mobile Reflection IA simplification + adaptive moments flow** — profile `Topic Reflection` screen now surfaces as `Reflection`, removes redundant occupancy bar chart + technical "Selected Thread" framing, and upgrades topic moments to adaptive density by depth (focus/flow horizontal lanes with month reflector, atlas vertical photo-stack with month-group headers) while preserving the existing visual style; thread-bottom action is now user-facing as whole-story summary (`Summarize <topic>`) with the same continuity-backed synthesis path
- **Simulation Add-Journal composer parity** — the top simulation journal composer now follows the same interaction model as "Continue the Conversation" (time-segment buttons, Cmd/Ctrl+Enter, and aligned submit row/button behavior)
- **Deep-answer response contract + regeneration gate** — deep-answer runs now target a longer structured reply (`180-280` words with required sections: direct answer, history anchors, recommended path, alternative path, risk + next 7-day action) and auto-regenerate once when the first draft misses contract checks
- **Auth-bound person resolution on user data routes** — routes that resolve person context (`/v2/turn`, conversation history, experience journal, memory, continuity) now bind to the authenticated principal in production and reject mismatched `?user=<uuid>` access
- **Normal-chat response contract update** — turn prompt now targets a focused tactical answer (`60-120` words, max 1 question) instead of the prior ultra-short `30-50` style
- **Observability redaction hardening** — monitoring payloads, telemetry request logs, and formatted application logs now redact sensitive free-text fields (`text`, `content`, `prompt`, `query`, `message`, `body`, `payload`) and inline secrets/tokens by default to reduce journal/prompt leakage risk in production sinks
- **Monitoring burst policy + incident alert classes** — monitoring now detects repeated auth failures, crash-loop exception bursts, and export/delete spikes via configurable threshold windows, and emits normalized break-glass allow/deny alert events for privileged route access
- **Rhythm planner path deferred by default** — turn-time `rhythm_planner_alignment` loading is now disabled unless `SAKHI_ENABLE_RHYTHM_PLANNER_ALIGNMENT=1`, preventing rhythm table dependencies from impacting core turn flows
- **Weekly rhythm rollup deferred by policy** — `weekly_rhythm_rollup` is now disabled by default (`SAKHI_ENABLE_WEEKLY_RHYTHM_ROLLUP=0`) and scheduler enqueue is skipped unless explicitly enabled
- **Production route guardrails** — internal operator routes (`/lab`, `/dev`, `/demo`, `/admin`) are now blocked by default in production runtime unless `SAKHI_ENABLE_INTERNAL_ROUTES_IN_PROD=1`
- **Operator break-glass enforcement for privileged routes** — when internal routes are explicitly enabled in production, privileged paths (`/lab`, `/dev`, `/demo`, `/admin`, `/debug`, `/memory/dev`, `/system/audit`) now require `SAKHI_OPERATOR_ACCESS_TOKEN` plus operator headers (`x-sakhi-operator-id`, `x-sakhi-approval-ref`, `x-sakhi-breakglass-reason`) with audit alerts for allow/deny decisions
- **Health/readiness hardening** — `/health` now reports dependency-aware readiness (DB required, Redis optional) with proper `503` degradation, plus explicit `/health/live` and `/health/ready` endpoints
- **External alerting sink wiring** — API unhandled exceptions and worker job/crash failures now route through `apps/api/core/monitoring.py` to optional Sentry (`SAKHI_SENTRY_DSN`) and/or webhook on-call sinks (`SAKHI_ALERT_WEBHOOK_URL`) with dedupe window controls
- **Context audit harness fix** — `scripts/context-audit.sh` now validates the actual `Makefile quick-test` target file list instead of checking a stale removed path
- **Journal encryption strict-mode hardening** — journal crypto now runs fail-closed on missing/weak `SAKHI_JOURNAL_MASTER_KEY`, defaults to `SAKHI_JOURNAL_WRITE_MODE=encrypted_only`, raises on decrypt failures in strict mode, and patches remaining worker/service/read paths for encrypted-only compatibility (including keyword/search fallbacks that no longer depend on plaintext DB columns)
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
