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
- **Mobile MVP release auth restored** — removed the TestFlight-only fixed-profile release bypass so production iOS builds now follow the normal Supabase auth flow instead of opening on a hardcoded Vidhya profile
- Reorganized monorepo structure and test directories
- Upgraded Next.js to 14.2.35 (patched CVE-2025-55184 and CVE-2025-67779)

### Fixed
- **Mobile auth onboarding simplification** - mobile sign-in now bootstraps `auth_users`/`persons`, binds cached `person_id` values to the authenticated Supabase user before treating the session as ready, routes first-time users through a name-only onboarding step, sends returning users directly to `/experience/converse`, shows an explicit session-expired re-login path, removes Apple sign-in from the live mobile auth screen, and keeps the older friction-framework onboarding flow out of the default runtime path
- **Mobile chat history hydration** — mobile `/experience/converse` now restores recent conversation turns from `/v2/conversation/history` on open, includes stable turn ids/timestamps in the history payload, and suppresses the empty-state flash while history is loading
- **Mobile MVP route/security cleanup** - parked soul routes and the unused voice screen are removed from the runtime app, mobile no longer exposes `EXPO_PUBLIC_OPENAI_API_KEY`, and legacy onboarding fall-throughs now route to conversation instead of voice
- **Internal TestFlight hardening** - active mobile chat/reflection screens now require an explicit backend URL instead of silently falling back to the old production Railway host, HealthKit is parked out of the current MVP build, and dead mobile helper files were removed so the release candidate can pass a clean mobile typecheck
- **iOS TestFlight build hardening** - the repo now pins `pnpm` as the workspace package manager, removes the stray root `package-lock.json`, and the local Fastlane build script now validates required mobile env vars while rejecting stale client OpenAI / release-bypass vars before upload
- **Overlap-aware continuity story gating** — continuity compilation now preserves bounded related-anchor evidence so shared moments can appear in both relevant story threads, while cross-topic `whole_story` readiness now allows dominant mirror-safe umbrella topics (for example Sakhi) to unlock Deep Reflect with meaningful supporting threads without lowering topic-detail safety globally
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
- **Deep reflection cross-topic mode expansion** — `/continuity/reflection/run` now accepts `mode=whole_story|cross_context` and `topic_keys[]`; whole-story runs answer the active query with linked-thread grounding, while cross-context runs perform longitudinal multi-thread reflection without requiring a query
- **Reflection My Story topic selection + persistence** — mobile/web reflection surfaces now admit lighter supporting threads once the anchor topic is deep enough, cross-context fallback copy explicitly names linked threads, and deep-reflection `window_start/window_end` writes persist native timestamps instead of stringified ISO values
- **Cross-topic continuity signal passthrough** — `/v2/turn` non-debug continuity payload now carries optional `candidate_topics`, `cross_context`, `whole_story`, and `life_dimensions` fields for product gating without debug payload access
- **Cross-topic cache foundation** — added `continuity_topic_correlations` and `continuity_life_dimensions` (migration `0015`) plus `services/continuity/cross_topic.py` read-through scoring/cache logic so cross-topic/whole-story readiness is derived from persisted composite correlations instead of per-turn temporal-only overlap
- **Continuity threshold/profile unification** — cross-topic caps and thresholds now live in `CONTINUITY_CROSS_TOPIC_THRESHOLD_PROFILE` (single source for topic cap, overlap gates, and life-dimension windows), and related-arc evidence is deduped before deep packet generation
- **Cross-topic cache hardening** — correlation cache now performs bounded all-pairs warm computation (not only selected-anchor pairs), semantic scoring prefers journal embedding cosine when available (lexical fallback retained), temporal overlap scan moved to sorted window matching, entry-tag lookup is resilient to key-format drift, cache TTL policy is profile-driven, and deep-reflection life-dimension context now reuses the same cross-topic cache service path as turn-time signaling
- **Cross-topic cache invalidation on journal delete** — destructive journal cleanup paths now invalidate `continuity_topic_correlations` and `continuity_life_dimensions` immediately (`/memory/dev/reset`, `/lab/cleanup`) so removed evidence does not remain visible until cache TTL expiry
- **Deep reflection emotion conflict guardrail** — deep reflection prompts now suppress emotion references unless priority-conflict evidence is explicit (time/money/commitment tradeoff), with a one-sentence cap when allowed
- **Mobile deep-answer contract hardening** — mobile chat now reads continuity topic from non-debug `/v2/turn` field (`continuity.topic_key/topic_label`), sends auth bearer headers on continuity endpoints for prod-bound person checks, and profile reflection auto-retries after continuity-policy enable when needed
- **Mobile whole-story deep trigger wiring** — mobile chat now uses `continuity.whole_story` readiness as the dynamic gate, sending `mode=whole_story` with linked `topic_keys[]` and no topic-only deep fallback in chat
- **Turn continuity readiness signal** — `/v2/turn` non-debug continuity payload now includes `continuity.deep_reflect` (`ready`, `reason`, `mirror_allowed`, `detail_allowed`, `selected_count`, `min_moments`) so clients can unlock Deep Reflect from a single response contract without separate readiness inference
- **Chat Deep Reflect mode split wiring (mobile + web)** — in-chat Deep Reflect now runs query-aware cross-context synthesis (`mode=whole_story`) with dynamic readiness messaging from continuity signals; normal chat behavior is unchanged
- **Mobile Reflection Me Story (cross-context)** — profile Reflection now includes a separate `Me Story` action that runs `mode=cross_context` over top active threads, while `<topic> Story` remains topic-centric (`mode=topic_reflection`)
- **Mobile continuity gating alignment** — chat now keeps the Deep Reflect hint row visible after first message (even before topic detection), and Reflection `Me Story` eligibility now honors continuity surface policy (`detail_allowed`/`mirror_allowed`) while anchoring cross-context runs on the currently selected thread
- **Mobile account hub + support console** — chat header now uses a single `Profile` account menu (Profile, Settings, Support Console, Sign out), with new mobile Settings and opt-in Support Console screens that generate time-limited support codes and user-reviewed diagnostics bundles before sharing
- **Web experience continuity/account parity with mobile** — `/experience/converse` now follows the mobile text-first chat contract (dynamic Deep Reflect gating + account hub actions), `/experience/reflection` now exposes continuity bubbles with `<topic> Story` and `My Story`, and new web account pages (`/experience/settings`, `/experience/support`) plus support-report proxy routes were added while removing the old in-chat debug panel from default user flow
- **Support Console backend wiring (consent-bound + revocable)** — mobile Support Console now persists diagnostics bundles through real API routes (`POST /support/report`, `GET /support/report`, `POST /support/report/revoke`) and supports immediate revoke, while operator retrieval uses break-glass protected `GET /admin/support/report/{support_code}` with metadata-only snapshots (no journal/message text)
- **Support timeline telemetry (consent-bound + metadata-only)** — Support Console now supports user-controlled live debug sessions (`POST /support/session/start|event|stop`) that capture ordered screen/action/API metadata (no journal/chat text), persist timeline events in dedicated tables, surface timeline preview on operator lookup, and let mobile chat/reflection flows emit session-linked diagnostic breadcrumbs
- **Mobile Reflection IA simplification + adaptive moments flow** — profile `Topic Reflection` screen now surfaces as `Reflection`, removes redundant occupancy bar chart + technical "Selected Thread" framing, and upgrades topic moments to adaptive density by depth (focus/flow horizontal lanes with month reflector, atlas vertical photo-stack with month-group headers) while preserving the existing visual style; thread-bottom action is now user-facing as whole-story summary (`Summarize <topic>`) with the same continuity-backed synthesis path
- **Simulation Add-Journal composer parity** — the top simulation journal composer now follows the same interaction model as "Continue the Conversation" (time-segment buttons, Cmd/Ctrl+Enter, and aligned submit row/button behavior)
- **Simulation cross-topic gate panel** — Ask-Sakhi turn debug now surfaces a dedicated cross-topic go/no-go validator (`candidate_topics`, `cross_context`, `whole_story`, `life_dimensions`) and supports test runs for all reflection modes (`deep_answer`, `topic_reflection`, `whole_story`, `cross_context`) from the same panel
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
