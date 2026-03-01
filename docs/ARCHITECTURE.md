# Sakhi Architecture

> An Ayurvedic-informed AI companion that provides personalized, context-aware responses based on a sophisticated memory and intelligence system.

---

## System Overview

```
+-----------------------------------------------------------+
|  USER-FACING LAYER (Friction Framework)                   |
|  - Operating Systems: Adaptive / Performance / Conservation|
|  - Operating Modes: Clarity / Activation / Recovery        |
|  - Friction States: Chaos / Intensity / Stagnation         |
+-----------------------------------------------------------+
                    | Translation
+-----------------------------------------------------------+
|  SCIENTIFIC BRIDGE LAYER                                   |
|  - Autonomic nervous system dominance                      |
|  - Chronobiology, circadian rhythms                        |
|  - Polyvagal theory states                                 |
+-----------------------------------------------------------+
                    | Computation
+-----------------------------------------------------------+
|  AYURVEDIC ENGINE LAYER (Internal - never shown to user)   |
|  - Doshas: Vata, Pitta, Kapha                             |
|  - Gunas: Sattva, Rajas, Tamas                            |
|  - Prakruti (baseline) vs Vikriti (current state)          |
+-----------------------------------------------------------+
```

### Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | FastAPI (Python 3.11+) |
| Database | PostgreSQL + pgvector |
| Queue | Redis + RQ |
| Frontend | Next.js 14 (React) |
| Mobile | React Native (Expo) |
| LLM | OpenAI (GPT-4o, GPT-4o-mini) |

---

## Project Structure

```
sakhi-monorepo/
├── apps/
│   ├── web/                   # Next.js frontend
│   └── mobile/                # React Native (Expo)
├── sakhi/                     # Python backend (CANONICAL)
│   ├── apps/api/              # FastAPI API
│   │   ├── routes/            # 75+ API route modules
│   │   └── services/          # Business logic (50+ modules)
│   ├── apps/engine/           # 30 computational engines
│   ├── apps/worker/           # Background job workers
│   │   ├── pipelines/         # Worker orchestration
│   │   └── tasks/             # 64 individual worker tasks
│   ├── libs/                  # Shared Python libraries
│   ├── tests/                 # All Python tests
│   └── infra/scripts/         # DB migrations, scripts
├── kala/                      # Governance kernel (pure computation, 547 tests)
├── docs/                      # All documentation
│   └── kala/                  # Governance kernel documentation
├── scripts/                   # Dev/utility scripts
└── config/                    # App configuration
```

---

## Conversation Turn Flow

When a user sends a message, it flows through three phases:

```
User Message
     │
     ▼
┌─────────────────────────────────────────────────────────────────┐
│  PHASE 1: SYNCHRONOUS RESPONSE (< 500ms)                        │
│  ├── Load deterministic context (pre-computed intelligence)     │
│  ├── Run adaptive response pipeline                             │
│  ├── Generate reply with LLM                                    │
│  └── Return response to user                                    │
└─────────────────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────────────┐
│  PHASE 2: ASYNC WORKER QUEUE (background)                       │
│  ├── enqueue_turn_jobs() → Redis Queue                          │
│  ├── 10+ workers process jobs asynchronously                    │
│  └── Updates DB tables for next turn's context                  │
└─────────────────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────────────┐
│  PHASE 3: NEXT TURN                                             │
│  └── Fresh deterministic context with updated intelligence      │
└─────────────────────────────────────────────────────────────────┘
```

### Key Files

| Purpose | File |
|---------|------|
| Turn endpoint | `sakhi/apps/api/routes/turn_v2.py` |
| Context router | `sakhi/apps/api/services/context_router.py` |
| Prompt builder | `sakhi/apps/api/services/conversation_v2/conversation_reasoner.py` |
| Context loader | `sakhi/apps/api/services/turn/deterministic_context_loader.py` |
| Worker runner | `sakhi/apps/worker/pipelines/turn_updates/runner.py` |

---

## Context Router — Tiered Context Intelligence

The Context Router ensures the LLM always has 360-degree awareness while keeping prompts focused and computation costs low.

```
User Message
     │
     ▼
┌─────────────────────────────────────────────────────────────────┐
│  CONTEXT ROUTER                                                  │
│  ├── Deterministic keyword/pattern classifier (13 modules)      │
│  ├── Intent-based routing (from extracted intents)              │
│  ├── Time-based routing (morning/evening rituals)               │
│  └── LLM fallback (GPT-4o-mini) when confidence < 0.5          │
│  Output: Set of active modules                                   │
└─────────────────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────────────┐
│  TIER 1: 360° Context Scan (always present)                      │
│  One-liner per module from cheap/always-computed data:           │
│  Identity momentum, emotional state, moment mode, friction,     │
│  morning/evening/micro cache, reflection status                 │
│  Cost: ~0ms (pure functions + cache reads)                       │
└─────────────────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────────────┐
│  TIER 2: Deep Context Sections (router-gated)                    │
│  Full detailed sections only for active modules:                │
│  Identity & Growth, Emotional Attunement, Moment Intelligence,  │
│  Morning/Evening Ritual, Micro Flow, Daily Reflection           │
│  Cost: LLM calls + DB queries, only when needed                 │
└─────────────────────────────────────────────────────────────────┘
```

### 13 Context Modules

| Module | Tier 1 (always) | Tier 2 (router-gated) |
|--------|-----------------|----------------------|
| identity | Fast frames (pure functions) | Full narrative + alignment detail |
| emotional_depth | Empathy + microreg (DB side effects) | Inner dialogue (LLM), nudge state |
| moment | Moment model (pure function) | Evidence pack (DB/LLM), deliberation |
| recommendations | Friction state (cheap) | Full recommendation generation (LLM) |
| scheduling | — | Calendar queries, nudges |
| email | — | Email context, contact prefs |
| causal | — | Causal reasoning (LLM) |
| morning_ritual | Cache reads | Already in tier 1 |
| evening_ritual | Cache reads | Already in tier 1 |
| micro_flow | Cache reads | Focus path / mini flow generation (LLM) |
| reflection | Cache reads | Already in tier 1 |
| vision | — | Image processing pipeline |
| agentic | — | Web search, agent tasks |

### Key Files

| Purpose | File |
|---------|------|
| Router | `sakhi/apps/api/services/context_router.py` |
| Context scan + Tier 2 builders | `sakhi/apps/api/services/conversation_v2/conversation_reasoner.py` |
| Router integration | `sakhi/apps/api/routes/turn_v2.py` |

See [features/context-routing.md](features/context-routing.md) for full details.

---

## API Routes

### Core Conversation
| Route | Purpose |
|-------|---------|
| `POST /v2/turn` | Main conversation endpoint |
| `GET /v2/conversation/history` | Conversation history |

### Voice
| Route | Purpose |
|-------|---------|
| `POST /api/voice/turn` | Voice conversation (STT → Sakhi → TTS) |
| `POST /api/voice/tts` | Standalone text-to-speech |

### Memory & Recall
| Route | Purpose |
|-------|---------|
| `/memory` | Memory recall operations |
| `/retrieval` | Hybrid semantic + keyword search |

### Friction Framework
| Route | Purpose |
|-------|---------|
| `/friction-framework` | Framework API |
| `/profile/operating-system` | User's constitutional type |
| `/state/current` | Current state vs baseline |

### Lab & Debug
| Route | Purpose |
|-------|---------|
| `/lab/memory-details` | View all intelligence for a user |
| `/lab/run-worker` | Test individual workers |
| `/lab/live-turn` | Test turn with debug output |

### Email Intelligence
| Route | Purpose |
|-------|---------|
| `POST /email/connect/gmail` | Start Gmail OAuth flow |
| `GET /email/connect/gmail/callback` | OAuth callback (redirects to app) |
| `GET /email/status` | Sync status |
| `POST /email/sync` | Trigger sync |
| `GET /email/signals` | Get all extracted signals |
| `GET /email/signals/avoidance` | Threads awaiting reply |
| `GET /email/signals/subscriptions` | Detected newsletters |
| `GET /email/signals/boundary` | Boundary erosion score |
| `GET /email/insight` | Surfaceable insight for conversation |
| `GET /email/context` | Email context for conversation engine |
| `POST /email/disconnect` | Disconnect and delete data |

---

## Memory System

Three-tier memory architecture inspired by human memory:

```
┌─────────────────────────────────────────────────────────────────┐
│  TIER 1: SHORT-TERM MEMORY (24-48h)                             │
│  - Recent conversations, journal entries                        │
│  - High recall speed (embeddings + keywords)                    │
│  - Table: memory_short_term                                     │
└─────────────────────────────────────────────────────────────────┘
                            │ Consolidation
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│  TIER 2: EPISODIC MEMORY (days to weeks)                        │
│  - Daily episode summaries                                      │
│  - State vectors (dosha, guna)                                  │
│  - Table: memory_episodic                                       │
└─────────────────────────────────────────────────────────────────┘
                            │ Pattern extraction
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│  TIER 3: LONG-TERM MEMORY (weeks to months)                     │
│  - Persistent patterns, values, identity themes                 │
│  - Soul state (shadow, light, conflicts)                        │
│  - Table: personal_model.long_term                              │
└─────────────────────────────────────────────────────────────────┘
```

---

## Adaptive Response Pipeline

5-stage pipeline for personalized responses:

```
┌─────────────────────────────────────────────────────────────────┐
│  STAGE 1: SENSING                                               │
│  - Domain classification (Body/Mind/Life/General)               │
│  - Symptom/Topic extraction                                     │
│  - Tone detection                                               │
│  Output: SenseFrame                                             │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│  STAGE 2: KNOWLEDGE GAP ANALYSIS                                │
│  - Load user's Operating System (constitution)                  │
│  - Query memory sources                                         │
│  - Compile: KNOWN / INFERRED / UNKNOWN                          │
│  Output: KnowledgeGap                                           │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│  STAGE 3: RESPONSE STRATEGY                                     │
│  - If UNKNOWN empty → RESPOND mode                              │
│  - If UNKNOWN has items → INQUIRE mode                          │
│  Output: ResponseStrategy                                       │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│  STAGE 4: CONTEXT SYNTHESIS                                     │
│  - Compress known facts                                         │
│  - Frame inferences with confidence                             │
│  - Include constitution-specific guidance                       │
│  Output: SynthesizedContext                                     │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│  STAGE 5: RESPONSE FORMATION                                    │
│  - Apply template: ACKNOWLEDGE → CONNECT → INQUIRE/RESPOND      │
│  - Tone calibration                                             │
│  - LLM generation                                               │
│  Output: Response                                               │
└─────────────────────────────────────────────────────────────────┘
```

---

## Background Workers

Workers update intelligence after each conversation turn:

| Worker | Purpose | Updates |
|--------|---------|---------|
| `turn_memory_update` | Ingests user message | memory_short_term |
| `ayurvedic_pipeline` | Ayurvedic signal extraction | elemental_*, energy_* |
| `episodic_consolidation_v21` | Creates daily episodes | memory_episodic |
| `rhythm_forecast` | Updates rhythm state | personal_model.rhythm_state |
| `identity_momentum_deep` | Tracks identity evolution | identity state |
| `emotion_soul_rhythm_deep` | ESR integration | emotion/soul/rhythm state |
| `esr` | Emotion state refresh | current emotional state |
| `soul_refresh` | Updates soul/prakriti | soul state |
| `longitudinal_update` | Weekly learning | longitudinal state |
| `rhythm_soul_deep` | Rhythm-soul integration | rhythm soul state |

---

## Engine Layer

30 standalone computational engines at `sakhi/apps/engine/`, each with its own `engine.py`. These produce deterministic intelligence that feeds the conversation pipeline:

| Category | Engines |
|----------|---------|
| State & Identity | alignment, coherence, identity_drift, identity_momentum |
| Emotion & Soul | emotion_loop, empathy, microreg, inner_conflict, inner_dialogue |
| Daily Flows | morning_ask, morning_momentum, morning_preview, evening_closure, daily_reflection |
| Narrative & Patterns | narrative, reflection_trace, pattern_sense, forecast, continuity |
| Micro Interventions | micro_journey, micro_momentum, micro_recovery, mini_flow |
| Planning & Action | focus_path, hands, nudge, tone, task_routing |
| Reasoning | deliberation_scaffold, evidence_pack, moment_model |

---

## Governance Integration (Kala)

The **kala** governance kernel is a pure-computation package with 547 tests. It is integrated into Sakhi's conversation pipeline:

```
Proposed Action → GovernanceGate
     │
     ├── Load constraints from governance_constraints table
     ├── Load objectives from governance_objectives table
     ├── Evaluate constraints (11 operators, priority-based)
     ├── Detect contradictions (5 typed categories)
     ├── Compute drift gating
     └── Log decision to governance_events ledger
```

| Purpose | File |
|---------|------|
| Governance bridge | `sakhi/apps/api/services/governance/service.py` |
| Constraint seeding | `sakhi/apps/api/services/governance/seed.py` |
| Demo seeder | `sakhi/apps/api/services/demo/governance_seeder.py` |
| Kala package | `kala/` (standalone, zero external dependencies) |

---

## Demo & Simulation

The simulation system showcases Sakhi's intelligence evolution over 30 days:

| Route | Purpose |
|-------|---------|
| `POST /demo/simulation/seed` | Seed governance + persona data |
| `POST /demo/simulation/add-journal` | Process journal through real pipeline |
| `GET /demo/simulation/state/{person_id}` | Get personal model state |
| `GET /demo/simulation/ledger/{person_id}` | Get governance event ledger |
| `POST /demo/simulation/evaluate` | Run kala GovernanceGate evaluation |

Frontend components at `apps/web/app/lab/simulation/`:
- **ThreeActDemo** — Three-act governance scenario (Illusion → Reveal → Divergence)
- **ReplayClient** — 30-day conversation replay with auto-play and drift visualization
- **ProfilesContrast** — Side-by-side persona comparison

---

## Personal Model

The `personal_model` table is the single source of truth for all user intelligence:

```sql
CREATE TABLE personal_model (
    person_id UUID PRIMARY KEY,

    -- Friction Framework (MVP)
    operating_system JSONB,      -- Prakruti (constitutional type)
    life_context JSONB,          -- Age, roles, life phase
    decision_profile JSONB,      -- Decision-making patterns

    -- Short-term state
    short_term JSONB,            -- Current dosha/guna drift

    -- Long-term patterns
    long_term JSONB,             -- emotion, mind, soul layers

    -- Rhythm & Energy
    rhythm_state JSONB,
    energy_state JSONB,

    -- Soul & Identity
    soul_state JSONB,
    identity_state JSONB,

    -- Brain states
    forecast_state JSONB,
    coherence_state JSONB,
    alignment_state JSONB,

    updated_at TIMESTAMPTZ
);
```

### Operating System Translation

| Dosha | Operating System | Characteristics |
|-------|------------------|-----------------|
| Vata-dominant | Adaptive | Creative, variable, quick-thinking |
| Pitta-dominant | Performance | Driven, intense, sharp |
| Kapha-dominant | Conservation | Steady, grounded, enduring |

---

## Database

**179 tables** organized by domain. See [DATABASE_SCHEMA.md](DATABASE_SCHEMA.md) for complete reference.

### Key Tables

| Domain | Tables |
|--------|--------|
| Memory | memory_short_term, memory_episodic, memory_long_term |
| Personal Model | personal_model, personal_model_energy |
| Conversation | journal_entries, conversation_turns |
| Friction | elemental_summary_weekly, energy_summary_weekly |
| Cache | 30+ cache tables for precomputed context |

### Vector Embeddings

```sql
-- 1536-dimension vectors (OpenAI text-embedding-3-small)
embedding vector(1536)
```

---

## Quick Commands

| Task | Command |
|------|---------|
| Start API | `make dev` |
| Start web | `pnpm dev:web` |
| Run tests | `make test` |
| Format code | `make format` |
| Run migrations | `make db-migrate` |

---

## Environment Variables

### Required
```bash
DATABASE_URL=postgresql://...
REDIS_URL=redis://localhost:6379/0
OPENAI_API_KEY=sk-...
```

### Optional
```bash
SUPABASE_URL=https://...
SUPABASE_SERVICE_ROLE_KEY=...
SAKHI_DISABLE_QUEUE=1  # Run workers inline (dev)
```

---

## Demo User

```
User ID: 565bdb63-124b-4692-a039-846fddceff90
Name: Vidhya
```

---

## Related Documentation

| Document | Purpose |
|----------|---------|
| [DATABASE_SCHEMA.md](DATABASE_SCHEMA.md) | Complete table reference |
| [DATABASE_MIGRATIONS.md](DATABASE_MIGRATIONS.md) | Migration instructions |
| [features/friction-framework.md](features/friction-framework.md) | Friction Framework API |
| [features/adaptive-response.md](features/adaptive-response.md) | Response pipeline details |
| [features/context-routing.md](features/context-routing.md) | Context Router & tiered intelligence |
| [guides/getting-started.md](guides/getting-started.md) | Setup instructions |
| [kala/](kala/) | Governance kernel documentation |
| [features/conversation-turn-anatomy.md](features/conversation-turn-anatomy.md) | Turn pipeline source of truth |
