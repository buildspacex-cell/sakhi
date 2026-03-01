# Sakhi Documentation

> **Sakhi** — An Ayurvedic-informed AI companion that helps you understand yourself through gentle, personalized conversation.

---

## Quick Start

```bash
# Start the backend
make dev

# Start the frontend (in another terminal)
pnpm dev:web

# Start workers (optional - for background processing)
make worker
```

**Demo User:** `6b5b2fbc-9efb-4ba4-be0a-9ec527e23f90` (Vidhya)

---

## Documentation Index

### Core Reference

| Document | Description |
|----------|-------------|
| [ARCHITECTURE.md](ARCHITECTURE.md) | System architecture, conversation flow, memory system |
| [CODEBASE_CONTEXT.md](CODEBASE_CONTEXT.md) | Audited codebase baseline, working vs broken signals, quality gates |
| [DATABASE_SCHEMA.md](DATABASE_SCHEMA.md) | Complete schema reference (179 tables) |
| [DATABASE_MIGRATIONS.md](DATABASE_MIGRATIONS.md) | How to make database changes |

### Planning & Roadmap

| Document | Description |
|----------|-------------|
| [BUILD_PLAN.md](BUILD_PLAN.md) | Feature roadmap with completion status |
| [AYURVEDIC_ENGINE_DEEPENING_PLAN.md](AYURVEDIC_ENGINE_DEEPENING_PLAN.md) | Knowledge Graph implementation plan |

### Features

| Document | Description |
|----------|-------------|
| [Friction Framework](features/friction-framework.md) | User-facing Operating System, Modes, States |
| [Friction Framework Mapping](features/FRICTION_FRAMEWORK_MAPPING.md) | Technical Ayurvedic-to-Friction mapping |
| [Adaptive Response](features/adaptive-response.md) | 5-stage response pipeline |
| [Agent Task Orchestrator](features/agent-task-orchestrator.md) | Preference-aware autonomous task execution |
| [Body State](features/body-state.md) | Health/body intelligence integration |
| [Pattern Crystallization](features/pattern-crystallization.md) | Threshold-based pattern promotion |
| [Voice](features/voice.md) | Speech-to-text and text-to-speech |

### Guides

| Document | Description |
|----------|-------------|
| [Getting Started](guides/getting-started.md) | Setup and run instructions |
| [Authentication](guides/authentication.md) | Google/Supabase auth setup |
| [Onboarding](guides/onboarding.md) | User onboarding flow |
| [Testing](guides/testing.md) | How to test the system |
| [Test Status](TEST_STATUS.md) | Test coverage tracking (workers, routes) |
| [Deployment Checklist](guides/TODO_DEPLOY.md) | Pre-deploy checklist and env vars |

### Vision & Philosophy

| Document | Description |
|----------|-------------|
| [Philosophy](vision/philosophy.md) | Core product vision and principles |
| [Inner Mirror](vision/inner-mirror-spec.md) | The inner mirror concept |
| [Safety & Ethics](vision/safety-ethics.md) | Safety boundaries and ethics |

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
User Message → Load Context → Generate Reply → Return (< 500ms)
                    ↓
            Queue Workers (async)
                    ↓
            Update Intelligence
                    ↓
            Next Turn Loads Fresh Context
```

---

## Project Structure

```
sakhi-monorepo/
├── apps/
│   ├── web/               # Next.js frontend
│   └── mobile/            # React Native (Expo)
├── sakhi/                 # Python backend (CANONICAL)
│   ├── apps/api/          # FastAPI API
│   ├── apps/worker/       # Background job workers
│   ├── libs/              # Shared Python libraries
│   ├── tests/             # All Python tests
│   └── infra/scripts/     # DB migrations, scripts
├── docs/                  # All documentation
├── scripts/               # Dev/utility scripts
└── config/                # App configuration
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
SAKHI_DISABLE_QUEUE=1  # Run workers inline (dev)
```

---

## Archive

Old documentation preserved in [_archive/](_archive/) for reference.
