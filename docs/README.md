# Sakhi Documentation

> **Sakhi** — An Ayurvedic-informed AI companion that helps you understand yourself through gentle, personalized conversation.

---

## Quick Start

```bash
# 1. Start the backend
cd sakhi && uvicorn apps.api.main:app --reload --port 8000

# 2. Start the frontend
cd apps/web && pnpm dev

# 3. Start workers (optional - for background processing)
cd sakhi && python -m apps.worker.main
```

**Demo User:** `565bdb63-124b-4692-a039-846fddceff90` (Vidhya)

---

## Documentation Index

### Vision & Philosophy
| Document | Description |
|----------|-------------|
| [Product Philosophy](vision/philosophy.md) | Core product vision and principles |
| [Inner Mirror Spec](vision/inner-mirror-spec.md) | The inner mirror concept |
| [Safety & Ethics](vision/safety-ethics.md) | Safety boundaries and ethics |

### Architecture
| Document | Description |
|----------|-------------|
| [System Overview](architecture/system-overview.md) | Complete system architecture, API routes, services |
| [Database Schema](architecture/database-schema.md) | All 117 tables with columns and types |
| [Conversation Flow](architecture/conversation-flow.md) | Turn processing, workers, context loading |
| [Workers](architecture/workers.md) | All 85+ workers, queues, scheduler config |

### Features
| Document | Description |
|----------|-------------|
| [Friction Framework](features/friction-framework.md) | User-facing framework API (Operating System, Modes, States) |
| [Adaptive Response](features/adaptive-response.md) | 5-stage response pipeline |
| [Body State](features/body-state.md) | Health/body intelligence integration |
| [Pattern Crystallization](features/pattern-crystallization.md) | Threshold-based pattern promotion |
| [Voice Integration](features/voice.md) | Speech-to-text and text-to-speech |

### Guides
| Document | Description |
|----------|-------------|
| [Getting Started](guides/getting-started.md) | Setup and run instructions |
| [Onboarding](guides/onboarding.md) | User onboarding flow |
| [Authentication](guides/authentication.md) | Google/Supabase auth setup |
| [Testing](guides/testing.md) | How to test the system |

---

## Key Concepts

### The Three Layers

```
┌─────────────────────────────────────────────────────────────┐
│  USER-FACING (Friction Framework)                           │
│  • Operating System: Adaptive / Performance / Conservation  │
│  • Operating Mode: Clarity / Activation / Recovery          │
│  • Friction State: Chaos / Intensity / Stagnation           │
└─────────────────────────────────────────────────────────────┘
                        ↓ Translation Layer
┌─────────────────────────────────────────────────────────────┐
│  SCIENTIFIC BRIDGE                                          │
│  • Autonomic nervous system dominance                       │
│  • Chronobiology, circadian rhythms                         │
│  • Polyvagal theory states                                  │
└─────────────────────────────────────────────────────────────┘
                        ↓ Computation
┌─────────────────────────────────────────────────────────────┐
│  AYURVEDIC ENGINE (Internal - never shown to user)          │
│  • Doshas: Vata, Pitta, Kapha                              │
│  • Gunas: Sattva, Rajas, Tamas                             │
│  • Prakruti (baseline) vs Vikriti (current state)          │
└─────────────────────────────────────────────────────────────┘
```

### Conversation Turn Flow

```
User Message
     ↓
┌─────────────────────────────────────────────┐
│  SYNCHRONOUS (< 500ms)                      │
│  Load context → Generate reply → Return     │
└─────────────────────────────────────────────┘
     ↓
┌─────────────────────────────────────────────┐
│  ASYNC (background)                         │
│  10 workers update intelligence             │
└─────────────────────────────────────────────┘
     ↓
Next turn loads fresh context
```

**Workers triggered per turn:** `turn_memory_update`, `ayurvedic_pipeline`, `episodic_consolidation_v21`, `rhythm_forecast`, `identity_momentum_deep`, `emotion_soul_rhythm_deep`, `esr`, `soul_refresh`, `longitudinal_update`, `rhythm_soul_deep`

---

## Project Structure

```
sakhi/
├── apps/
│   ├── api/              # FastAPI backend (60+ routes)
│   │   ├── routes/       # API endpoints
│   │   └── services/     # Business logic
│   └── worker/           # Background workers (85+ tasks)
│       ├── tasks/        # Individual worker tasks
│       └── pipelines/    # Worker orchestration
├── core/                 # Domain logic (soul, rhythm, emotion)
├── libs/                 # Shared libraries (embeddings, LLM, retrieval)
└── infra/scripts/migrations/  # Database migrations (41 files)

apps/web/                 # Next.js frontend
├── app/
│   ├── experience/       # User experience pages
│   ├── api/              # API routes (turn, voice, auth)
│   └── auth/             # Auth pages
└── lib/hooks/            # React hooks (useVoice, etc.)
```

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
SAKHI_DISABLE_QUEUE=0  # Set to 1 for inline workers (dev)
```

See [Getting Started](guides/getting-started.md) for full setup.

---

## API Endpoints

### Core Conversation
- `POST /v2/turn` — Main conversation endpoint
- `GET /v2/conversation/history` — Get conversation history

### Voice
- `POST /api/voice/turn` — Voice conversation (STT → Sakhi → TTS)
- `POST /api/voice/tts` — Standalone text-to-speech

### Lab/Debug
- `GET /lab/memory-details` — View all intelligence for a user
- `POST /lab/run-worker` — Test individual workers
- `GET /lab/live-turn` — Test turn with debug output

See [System Overview](architecture/system-overview.md) for complete API reference.

---

## Testing

```bash
# Backend tests
cd sakhi && pytest tests/

# Frontend type check
cd apps/web && pnpm tsc --noEmit

# Test a specific worker
curl -X POST http://localhost:8000/lab/run-worker \
  -H "Content-Type: application/json" \
  -d '{"person_id": "565bdb63-124b-4692-a039-846fddceff90", "worker": "esr"}'
```

See [Testing Guide](guides/testing.md) for comprehensive testing instructions.

---

## Archive

Old documentation preserved in [_archive/](_archive/) for reference.
