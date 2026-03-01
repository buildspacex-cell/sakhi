# Changelog

All notable changes to Sakhi will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Governance kernel (kala)** — pure-computation governance with constraint evaluation (11 operators), drift gating, contradiction detection (5 categories), objective versioning, and 547 tests
- **Kala–Sakhi integration** — GovernanceGate wired into conversation pipeline via `services/governance/service.py`
- **"A Day with Sakhi" simulation demo** — three-act governance scenario (Illusion → Reveal → Divergence), interactive governance evaluation
- **30-day conversation replay** — real persona pipelines (Vidhya, Diya, Big D) with auto-play, speed controls, drift visualization
- **Simulation profile updater** — add journal entries to simulation profiles through real pipeline (`/demo/simulation/add-journal`)
- **Body health override** — physical symptom responses bypass generic Ayurvedic reasoning
- **Email Intelligence v1** — Gmail OAuth integration, LLM-powered digest (triage, action items), signal extraction (subscriptions, avoidance, boundaries, cognitive load)
- **Knowledge graph-powered symptom recommendations** + Prompt Playground
- **Web onboarding flow** — 8 screens, 19 questions, progressive OS calibration
- **Mobile onboarding, voice, and auth** with Ayurvedic knowledge graph
- **Full-brain simulation harness v2** — deep-dive visualizations for coherence, alignment, identity, themes
- **Context routing** — tiered context intelligence with hybrid router
- **Comprehensive test suite** — e2e, integration, and unit tests
- **Docker worker service** — `Dockerfile.worker` for Railway worker deployment
- Session memory for Claude (`.claude/MEMORY.md`, `.claude/CURRENT_TASK.md`)
- Quick task shortcuts, pre-commit hooks, code generators, feature flags, dev status dashboard

### Changed
- **Removed OpenRouter provider** — all LLM calls now use OpenAI directly (GPT-4o, GPT-4o-mini)
- **Separated THINK vs RESPOND** in SAKHI_INSTRUCTIONS prompt for clearer reasoning
- **Optimized conversation pipeline** — reduced turn latency from 15s to 6-8s
- **Adaptive response** — personalized WHY required in every response, adaptive prompt placed first
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
