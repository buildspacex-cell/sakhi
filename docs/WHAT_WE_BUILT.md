# Sakhi — What We Built

> A complete inventory of the Sakhi system as of March 2026.
>
> ~200K lines of code. 179 database tables. 34 engines. 552 kala tests. Zero shortcuts.

---

## One Paragraph

Sakhi is a personal wellness AI grounded in Ayurveda. It holds ongoing conversations with a person, tracks their state over time (doshas, energy, emotions, patterns, rhythms), detects drift from their baseline, and governs its own behavior through a deterministic kernel called kala. The system runs a FastAPI backend with 81 API route modules and 114 worker modules, a Next.js web app with 78 pages, a React Native mobile app with 34 screens, and a pure-computation governance kernel with 552 tests. It processes every conversation turn through a multi-stage pipeline: load context from memory, route through 13 context modules, inject policy-gated continuity context when available, generate an Ayurvedically-informed response, then fan out to background workers that update memory, consolidate episodes, learn patterns, and refresh state.

---

## The Numbers

| What | Count |
|---|---|
| Python backend (sakhi/) | ~146K lines across 81 route modules, 233 service modules, 86 worker task modules |
| Engine modules (sakhi/apps/engine/) | 34 computational engines |
| Governance kernel (kala/) | ~11K lines, 49 source files, 552 tests |
| Web app (apps/web/) | ~42K lines TypeScript, 78 pages, 119 API proxy routes |
| Mobile app (apps/mobile/) | ~7.9K lines TypeScript, 34 screens |
| Database tables | 179 |
| Background workers | 86 task files + 114 worker modules |
| Context modules | 13 (11 primary + 2 ritual caches) |
| LLM call sites | 80+ across routes, services, workers |
| Vector dimensions | 1536 (OpenAI text-embedding-3-small) |

---

## Architecture

Three-layer design, inspired by how Ayurveda structures understanding:

```
┌──────────────────────────────────────────────────┐
│  User Layer (Friction Framework)                  │
│  What the person experiences: chaos, intensity,   │
│  stagnation, or balance. Adaptive response style. │
├──────────────────────────────────────────────────┤
│  Scientific Bridge                                │
│  Memory, pattern detection, context routing,      │
│  rhythm tracking, temporal analysis.              │
├──────────────────────────────────────────────────┤
│  Ayurvedic Engine                                 │
│  Doshas (Vata/Pitta/Kapha), gunas, prakruti,     │
│  vikriti, drift, causal reasoning.               │
├──────────────────────────────────────────────────┤
│  Governance Kernel (kala)                         │
│  Constraints, drift gating, contradictions,       │
│  objective versioning. Pure computation.          │
└──────────────────────────────────────────────────┘
```

---

## Conversation Pipeline

Every conversation turn flows through this pipeline:

```
User message arrives (POST /v2/turn)
  │
  ├─ 1. CONTEXT LOADING (~150-300ms)
  │     Load from memory (STM, episodic, long-term)
  │     Load persona, rhythm state, active tasks
  │     (rhythm_planner_alignment is deferred by default unless explicitly enabled)
  │     Load friction state (chaos/intensity/stagnation/balanced)
  │
  ├─ 2. CONTEXT ROUTING
  │     Classify message → select relevant modules
  │     13 modules: memory, persona, rhythm, tasks, email,
  │     recommendations, inner dialogue, relationships,
  │     causal reasoning, evidence packs, ...
  │
  ├─ 3. ADAPTIVE RESPONSE (5 stages)
  │     Sensing → Knowledge Gap → Strategy → Synthesis → Response
  │     Tone adapted to friction state and conversation history
  │
  ├─ 4. REPLY DELIVERY (<8 seconds total)
  │     Return response + metadata to client
  │
  └─ 5. ASYNC WORKER FAN-OUT
        ├─ turn_memory_update (store in STM)
        ├─ episodic_consolidation (daily episodes)
        ├─ preference_learning (learn from feedback)
        ├─ intent_extraction (extract user intents)
        ├─ journal_enrich (enrich journal entry)
        └─ session_compress (compress session history)
```

**Daily state refresh** (scheduled, not per-turn):
- Ayurvedic pipeline → vikriti, prakruti, friction state
- Emotion-soul-rhythm deep frame
- Soul values extraction
- Rhythm inference → learn daily profile
- Pattern crystallization → recurring patterns
- Goal evolution → adapt objectives
- Memory synthesis → weekly/monthly consolidation
- Meta-reflection → weekly self-assessment

**Continuity surface** (policy-gated):
- Continuity policy/exclusions (`/continuity/policy`)
- Topic + arc retrieval (`/continuity/topics`, `/continuity/arc`)
- Turn-level hidden continuity pack injection for prompt coherence (`turn_v2` metadata), including compact thread stats, sampled phase path, anchor moments, deterministic qualitative arc summary, and a chronological decision ledger (including acknowledged Sakhi suggestions) for stronger longitudinal grounding
- Turn-level product continuity signal in `/v2/turn` responses (`continuity.topic_key`, `continuity.topic_label`, `continuity.deep_reflect`, plus optional `candidate_topics`, `cross_context`, `whole_story`, `life_dimensions`) so clients can trigger both topic-depth and cross-topic deep flows without debug payloads
- Cross-topic continuity cache layer (`continuity_topic_correlations`, `continuity_life_dimensions`) with lazy read-through recompute and indexed lookup for pairwise thread correlation + cross-cutting dimension signals (time, financial, emotional)
- Cross-topic cache hardening now includes bounded all-pairs warm compute, profile-driven cache TTL policy, resilient `entry_tags` resolution for compiler key-format drift, embedding-cosine semantic scoring when journal vectors are present (lexical fallback otherwise), and shared life-dimension cache usage between `/v2/turn` and deep-reflection packet assembly
- Deep reflection async flow (`/continuity/reflection/run|status|result`) with compact LLM synthesis packet + deterministic fallback (`chat_response_source`, `llm_reflection` debug payload) for direct chat rendering, including surface-policy carry-through (`detail_allowed`/`mirror_allowed`) to keep blocked-detail reflections mirror-only, language-first prompt framing (`history`, `person context`, `current query`), explicit run modes (`topic_reflection`, `deep_answer`, `whole_story`, `cross_context`), linked-thread injection via `topic_keys`, and emotion mention guardrails (only when explicit priority conflict evidence is present)
- Chat Deep Reflect now uses dynamic cross-context readiness (`continuity.whole_story`) and runs `mode=whole_story` in both mobile and web converse flows; normal chat responses stay topic-centric and unchanged
- Mobile Reflection now splits story surfaces cleanly: `<topic> Story` remains topic-centric (`mode=topic_reflection`) while `Me Story` runs cross-context synthesis (`mode=cross_context`) across active linked threads
- Mobile account header now uses a single account hub action (Profile, Settings, Support Console, Sign out), and Support Console now persists user-consented support bundles through backend APIs (`/support/report`, `/support/report/revoke`) with time-limited codes, metadata-only diagnostics snapshots, and a user-controlled live debug timeline session (`/support/session/start|event|stop`) that captures screen/action/API telemetry without journal/chat text
- Web experience now mirrors the mobile continuity flow: text-first chat with dynamic in-chat Deep Reflect gating, account hub menu (Reflection, Settings, Support Console, Sign out), and continuity-backed Reflection/My Story surfaces without exposing the chat debug panel in the default user flow
- Simulation Ask-Sakhi debug inspector exposes `turn_debug` (continuity pack + prompt payload), includes a cross-topic gate validator (`candidate_topics`, `cross_context`, `whole_story`, `life_dimensions`) for cohort go/no-go checks, and now supports all deep reflection run modes (`deep_answer`, `topic_reflection`, `whole_story`, `cross_context`) with cache-busted polling/result probing in `apps/web/app/lab/simulation/client.tsx`
- Simulation "Add Journal" composer now uses the same chat flow pattern as "Continue the Conversation" (time segmented buttons, Cmd/Ctrl+Enter submit, aligned submit row behavior) to keep local testing interactions consistent.

**Production hardening controls**:
- Health probes now include liveness and readiness contracts: `GET /health/live` and `GET /health`/`GET /health/ready` (DB required, Redis optional), with readiness returning `503` on DB failure.
- Internal/non-user routes are blocked by default in production runtime (`/lab`, `/dev`, `/demo`, `/admin`, `/debug`, `/memory/dev`, `/system/audit`) unless explicitly re-enabled via `SAKHI_ENABLE_INTERNAL_ROUTES_IN_PROD=1`; when re-enabled, break-glass operator headers + `SAKHI_OPERATOR_ACCESS_TOKEN` are required.
- Production person resolution now enforces authenticated ownership on user-scoped routes (`/v2/turn`, conversation history, experience journal, memory, continuity): mismatched `?user=<uuid>` access is denied.
- Rhythm rollup and planner rhythm alignment are both deferred by default (`SAKHI_ENABLE_WEEKLY_RHYTHM_ROLLUP=0`, `SAKHI_ENABLE_RHYTHM_PLANNER_ALIGNMENT=0`) so missing rhythm tables are kept out of default turn/scheduler paths.
- External incident alerting is wired for production failures via `sakhi/apps/api/core/monitoring.py` (optional Sentry DSN and/or webhook sink), including API unhandled exception capture and worker job/crash reporting with dedupe guards.
- Observability redaction is enforced for trust-sensitive payloads: monitoring sinks, request telemetry logs, and formatted log lines redact free-text prompt/journal/query/message/body fields plus inline secret/token values by default.
- Monitoring alert policy now includes burst detection for repeated auth failures, crash loops, and export/delete spikes, and emits normalized break-glass grant/deny alert events for privileged route access.
- Build/CI now fail fast on missing config using profile-based env contract validation (`make check-env`, `make verify`, CI `check_env.py --profile ci`).
- Journal writes now include per-user encrypted payloads (`journal_entries.raw_encrypted`) across API insert paths, derived from required `SAKHI_JOURNAL_MASTER_KEY` (32+ chars) with `SAKHI_JOURNAL_WRITE_MODE=encrypted_only` as the default runtime posture (`dual_write` only for temporary migration windows).
- Deep reflection status/result endpoints now require matching `person_id` ownership in addition to reflection id, closing UUID-only read access.
- Support diagnostics access is consent-bound and revocable: only user-generated support codes can unlock support bundles, operator retrieval lives behind `/admin/support/*` break-glass controls, and support bundles can include short-lived timeline telemetry (screen/action/API events) with strict metadata-only redaction (no journal/message text).

---

## What Each Layer Does

### Friction Framework (User-Facing)

The person never sees doshas or gunas. They experience **friction states**:

| State | What the person feels | Underlying driver |
|---|---|---|
| **Chaos** | Scattered, anxious, overwhelmed | Elevated Vata |
| **Intensity** | Driven, irritable, burning out | Elevated Pitta |
| **Stagnation** | Stuck, sluggish, unmotivated | Elevated Kapha |
| **Balanced** | Grounded, clear, flowing | Doshas near baseline |

The friction state determines how Sakhi responds: tone, pacing, what it suggests, what it avoids. A person in chaos gets grounding. A person in intensity gets permission to slow down. A person in stagnation gets gentle activation.

### Memory System (3 Tiers)

| Tier | Window | What it holds |
|---|---|---|
| **Short-term** | 24-48 hours | Recent conversation turns, immediate context |
| **Episodic** | Days to weeks | Daily episode summaries with state vectors |
| **Long-term** | Weeks to months | Consolidated patterns, stable preferences, identity |

Memory recall uses **hybrid retrieval**: semantic similarity (vector search) + keyword matching (BM25) + recency weighting (45-day half-life) + diversity filtering.

### Ayurvedic Engine

- **Prakruti** — Constitutional baseline (computed during onboarding). The person's natural balance of Vata/Pitta/Kapha.
- **Vikriti** — Current state deviation from baseline. Computed daily from conversation signals, journal entries, and behavioral patterns.
- **Drift** — Euclidean distance between prakruti and vikriti in 3D dosha space. Expressed as percentage with severity (minimal/mild/moderate/significant).
- **Gunas** — Sattva (clarity), Rajas (activity), Tamas (inertia). Another axis of state assessment.
- **Causal reasoning** — "Why is Vata elevated?" → Evidence from recent conversations, patterns, and temporal signals.

### Governance Kernel (kala)

Pure computation. No I/O, no database, no LLM. 552 tests.

- **Constraint evaluation** — Data-driven rules (field/operator/value). 11 operators. Priority-based (HARD → block, SOFT → confirm).
- **Drift gating** — Drift percentage triggers governance responses. Above threshold → block proactive suggestions.
- **Contradiction detection** — 5 typed categories: previously_rejected, contradicts_commitment, repetition_loop, outdated_objective_version, violates_recent_override.
- **Temporal substrate** — Timeline[T], trend detection, moving averages, rate of change, multi-source reconciliation, pattern crystallization with decay.
- **Objective versioning** — Objectives evolve (v1 → v2 → v3) with lineage. Stale constraints detected automatically.
- **State reducer** — Replays events into deterministic state. Same events → same snapshot. Auditable.

See [docs/kala/](kala/) for complete kala documentation.

---

## Backend Inventory

### API Routes (81 files)

**Core conversation:**
- `turn_v2.py` — Main conversation turn orchestrator
- `conversation.py` — History and message handling
- `journal_turn.py` — Journal entry conversation loop

**Ayurvedic & wellness:**
- `friction_framework.py` — Friction state assessment
- `recommendations.py` — Personalized recommendations
- `health.py`, `body.py`, `breath.py` — Physical state tracking

**Soul & identity:**
- `soul.py` — Values, identity signatures, purpose themes
- `identity_momentum.py`, `identity_state.py`, `identity_timeline.py` — Identity evolution
- `narrative.py`, `narrative_arcs.py` — Life story arcs

**Rhythm & temporal:**
- `rhythm.py` — Daily rhythm patterns
- `morning_ask.py`, `morning_momentum.py`, `morning_preview.py` — Morning flow
- `evening_closure.py` — Evening reflection
- `forecast.py` — Rhythm forecast

**Emotional & psychological:**
- `emotion_soul_rhythm.py` — Emotion-soul-rhythm integration
- `inner_dialogue.py`, `inner_conflict.py` — Internal state
- `alignment.py`, `coherence.py` — Value alignment and life coherence

**Focus & productivity:**
- `focus.py`, `focus_path.py` — Focus state management
- `micro_journey.py`, `micro_momentum.py` — Micro-goal journeys
- `decision_graph.py` — Decision support

**Memory & learning:**
- `memory.py` — Recall and synthesis
- `memory_graph.py` — Memory graph visualization
- `learning.py` — Feedback and preference learning

**External integrations:**
- `email.py` — Gmail OAuth, signal extraction, digest
- `calendar.py`, `scheduling.py` — Calendar integration
- `agent.py`, `agentic.py` — Desktop agent coordination
- `mesh.py` — Inter-Sakhi coordination
- `support.py` — User-consented support diagnostics bundles + break-glass operator lookup

**Analytics:**
- `analytics/breath.py`, `analytics/patterns.py`, `analytics/summary.py`, `analytics/themes.py`, `analytics/timeseries.py`

### Engine Layer (30 modules)

Standalone computational engines at `sakhi/apps/engine/`, each producing deterministic intelligence:

| Category | Engines |
|---|---|
| State & Identity | alignment, coherence, identity_drift, identity_momentum |
| Emotion & Soul | emotion_loop, empathy, microreg, inner_conflict, inner_dialogue |
| Daily Flows | morning_ask, morning_momentum, morning_preview, evening_closure, daily_reflection |
| Narrative & Patterns | narrative, reflection_trace, pattern_sense, forecast, continuity |
| Micro Interventions | micro_journey, micro_momentum, micro_recovery, mini_flow |
| Planning & Action | focus_path, hands, nudge, tone, task_routing |
| Reasoning | deliberation_scaffold, evidence_pack, moment_model |

### Services (50 directories)

| Service | What it does |
|---|---|
| `conversation_v2/` | Main conversation engine, reasoner, context builder, tone |
| `ayurveda/` | Prakruti, vikriti, graph reasoning, food recommendations, causal reasoning |
| `memory/` | Multi-layer memory: recall, episodic, STM, LTM, synthesis, BM25, embeddings |
| `turn/` | Per-turn orchestration: context loading, reply building, async triggers |
| `persona/` | Persona adaptation and session tuning |
| `rhythm/` | Rhythm engine, triggers, scheduling |
| `email/` | Gmail adapter, signal extraction |
| `agent/` | Browser automation, vision loop, screen analysis |
| `learning/` | Multi-level preference adaptation |
| `patterns/` | Pattern detection and crystallization |
| `soul/` | Soul values computation |
| `governance/` | Kala governance bridge (constraints, drift gating, event ledger) |
| `continuity/` | Continuity policy, topic compilation, arc surfacing, deep reflection jobs |
| `demo/` | Demo seeding, simulation harness, governance seeder |
| `focus/` | Focus state management |
| `missions/` | Mission/project tracking |
| `relationships/` | Relationship state and attention |
| `planning/`, `planner/` | Planning and scheduling |
| `reflection/`, `meta_reflection/` | Reflection and meta-reflection |
| `narratives/` | Narrative generation |
| `body/`, `environment/` | Physical and environmental context |

### Workers (86 task files)

**Per-turn (triggered after every conversation):**
- Memory update, episodic consolidation, preference learning, intent extraction

**Daily schedule:**
- Ayurvedic pipeline, emotion-soul-rhythm, soul refresh, rhythm inference
- Pattern crystallization, goal evolution, memory synthesis
- Body refresh, environment refresh, alignment refresh

**Weekly schedule:**
- Meta-reflection, weekly learning cycle, weekly rhythm rollup, weekly signals

**Email:**
- Email sync, email digest generation

**Task & planning:**
- Task enrichment, progressive structuring, task weaving, task routing

---

## Frontend Inventory

### Web App (Next.js 14, 78 pages)

**Tech:** Next.js 14 (App Router), React 18, TypeScript, Tailwind CSS, Framer Motion, Supabase Auth, SWR

**Main experiences:**
- `/experience/converse` — Conversation interface (main chat)
- `/experience/voice` — Voice mode (Whisper STT → Sakhi → OpenAI TTS)
- `/experience/onboarding` — Onboarding flow
- `/experience/me` — User profile and wellness state
- `/experience/journal` — Journal writing
- `/experience/calendar` — Calendar and scheduling
- `/experience/memory` — Memory visualization
- `/experience/reflection` — Deep reflection
- `/experience/dashboard` — Analytics dashboard
- `/experience/weekly` — Weekly review

**Soul section:**
- `/soul/values` — Core values exploration
- `/soul/alignment` — Life alignment assessment
- `/soul/narrative` — Personal narrative
- `/soul/timeline` — Life timeline visualization
- `/soul/shadow-work` — Shadow work exercises

**Lab (internal):**
- `/lab/simulation` — Full-brain simulation harness
- 15+ detail pages for debugging memory, persona, rhythm, patterns, etc.

**119 API proxy routes** forwarding to the Python backend.

### Mobile App (React Native / Expo, 30 screens)

**Tech:** Expo 54, React Native 0.81, React 19, TypeScript, NativeWind (Tailwind), Supabase Auth, React Query, Apple HealthKit integration

**Screens:**
- Auth flow (login, OAuth callback)
- Onboarding (questions, result, health connect)
- Conversation (canonical flow — mobile is source of truth)
- Soul (8 screens: hub, values, alignment, narrative, timeline, shadow, friction, insights)
- Voice mode

**Native integrations:**
- Apple Sign-In
- HealthKit (sleep, heart rate, activity)
- Haptic feedback
- Secure token storage

---

## Voice Pipeline

```
User speaks → MediaRecorder → audio blob
  → POST /api/voice/turn
    → Whisper STT (transcription)
    → POST /v2/turn (conversation)
    → OpenAI TTS (nova/shimmer/alloy voice)
  → Audio playback to user
```

Supports: echo cancellation, noise suppression, auto-play, speed control (0.25-4.0x), interrupt.

---

## Email Intelligence

Gmail integration that extracts behavioral signals from email patterns:

- **OAuth flow** → connect Gmail account
- **Sync** → fetch email metadata (subject, sender, timestamps)
- **Signal extraction** → subscription detection, sender avoidance patterns, communication boundaries, cognitive load scoring
- **Digest** → LLM-powered triage (GPT-4o-mini) → action items, FYI, noise, commitments
- **UI** → EmailDigestCard on the Me page showing categorized items

---

## Database (179 Tables)

Organized across domains:

| Domain | What it stores |
|---|---|
| **Personal Model** | Operating system (prakruti, vikriti, friction state, doshas, gunas) |
| **Memory** | Short-term, episodic, long-term memories with embeddings |
| **Conversation** | Turn history, session state, context snapshots |
| **Friction** | Friction state history, recommendations, feedback |
| **Rhythm** | Daily rhythm profiles, forecasts, nudges |
| **Soul** | Values, identity signatures, narrative arcs |
| **Patterns** | Crystallized patterns, pattern trends |
| **Email** | Sync state, email events, signals, digest items |
| **Learning** | Intervention plans, feedback loops, preference history |
| **Calendar** | Events, scheduling state |
| **Agent** | Registered agents, approvals, task routing |
| **Missions** | Goals, mission plans, progress tracking |

All person-scoped via `person_id UUID`. Vector columns use `vector(1536)`. JSONB for flexible metadata. Timestamps on everything.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.11, FastAPI, Poetry |
| Frontend (web) | Next.js 14, React 18, TypeScript, Tailwind |
| Frontend (mobile) | Expo 54, React Native, NativeWind |
| Database | PostgreSQL + pgvector (via Supabase) |
| Auth | Supabase Auth (web), Apple Sign-In (mobile) |
| Background jobs | Redis + RQ (Python) |
| Simulation | 3 personas (Vidhya, Diya, Big D), 30-day replay, governance demo |
| LLM | OpenAI GPT-4o, GPT-4o-mini |
| Embeddings | OpenAI text-embedding-3-small (1536D) |
| Voice | OpenAI Whisper (STT) + OpenAI TTS |
| Governance | kala (pure Python, zero dependencies) |
| Deployment | Vercel (web), Railway (API), EAS (mobile) |

---

## What Makes This Different

1. **Ayurvedic grounding.** Not generic wellness. Doshas, gunas, prakruti/vikriti provide a structured framework for understanding a person's state — not just "mood: happy/sad" but a multi-dimensional state space with drift detection.

2. **Temporal intelligence.** Every data structure has a temporal dimension. Memory decays. Patterns crystallize and fade. State drifts and recovers. Moving averages smooth noise. The system gets smarter over time, not just bigger.

3. **Governance kernel.** kala provides deterministic governance over probabilistic LLM inference. Constraints, drift gating, contradiction detection, objective versioning — all pure computation, all auditable, all replayable. 552 tests, zero external dependencies.

4. **Friction-first UX.** The person never sees doshas. They experience friction states (chaos, intensity, stagnation, balanced) that feel natural. The Ayurvedic engine runs underneath.

5. **Deep pipeline.** Not a chatbot wrapper. 64+ background workers process every interaction: memory storage, episodic consolidation, pattern learning, rhythm inference, preference adaptation, causal reasoning. The system is continuously learning.

6. **Multi-layer memory.** Three tiers (STM, episodic, long-term) with hybrid retrieval (vector + BM25 + recency), diversity filtering, and consolidation. Not just "store embeddings and retrieve."

---

*Last updated: 2026-03-05*
