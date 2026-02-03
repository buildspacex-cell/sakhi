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
| LLM | Multi-provider (OpenAI, OpenRouter) |

---

## Project Structure

```
sakhi-monorepo/
├── apps/
│   ├── web/                   # Next.js frontend
│   └── mobile/                # React Native (Expo)
├── sakhi/                     # Python backend (CANONICAL)
│   ├── apps/api/              # FastAPI API
│   │   ├── routes/            # 60+ API route modules
│   │   └── services/          # Business logic
│   ├── apps/worker/           # Background job workers
│   │   ├── pipelines/         # Worker orchestration
│   │   └── tasks/             # Individual worker tasks
│   ├── libs/                  # Shared Python libraries
│   ├── tests/                 # All Python tests
│   └── infra/scripts/         # DB migrations, scripts
├── docs/                      # All documentation
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
| Context loader | `sakhi/apps/api/services/turn/deterministic_context_loader.py` |
| Worker runner | `sakhi/apps/worker/pipelines/turn_updates/runner.py` |

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
| [guides/getting-started.md](guides/getting-started.md) | Setup instructions |
