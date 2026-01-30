# Sakhi Application Architecture

> **Status:** Complete Architecture Document
> **Created:** 2026-01-26
> **Purpose:** Comprehensive system architecture overview

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [API Layer Structure](#2-api-layer-structure)
3. [Service Layer Structure](#3-service-layer-structure)
4. [Database Schema](#4-database-schema)
5. [Memory System Architecture](#5-memory-system-architecture)
6. [Conversation Flow](#6-conversation-flow)
7. [Adaptive Response Pipeline](#7-adaptive-response-pipeline)
8. [Personal Model Structure](#8-personal-model-structure)
9. [Data Flow Diagrams](#9-data-flow-diagrams)
10. [Key Technologies](#10-key-technologies)

---

## 1. System Overview

Sakhi is an Ayurvedic-informed AI companion that provides personalized, context-aware responses based on a sophisticated memory and intelligence system. The architecture follows a three-layer model:

```
+-----------------------------------------------------------+
|  USER-FACING LAYER (Friction Framework)                   |
|  - Operating Systems (Adaptive/Performance/Conservation)  |
|  - Operating Modes (Clarity/Activation/Recovery)          |
|  - Friction States (Chaos/Intensity/Stagnation)           |
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
|  AYURVEDIC ENGINE LAYER (Internal)                         |
|  - Doshas (Vata, Pitta, Kapha)                            |
|  - Gunas (Sattva, Rajas, Tamas)                           |
|  - Prakruti vs Vikriti                                     |
|  - Pancha Mahabhutas (5 elements)                         |
+-----------------------------------------------------------+
```

### Core Technologies

- **Backend:** FastAPI (Python)
- **Database:** PostgreSQL with pgvector extension
- **Queue:** Redis with RQ (Redis Queue)
- **Frontend:** Next.js (React)
- **LLM Router:** Multi-provider (OpenAI, OpenRouter, Web)

---

## 2. API Layer Structure

**Entry Point:** `sakhi/apps/api/main.py`

### Core Routers

The main FastAPI application includes 60+ route modules organized by functionality:

#### Conversation & Turn Routes

| Route | Purpose | Key Operations |
|-------|---------|----------------|
| `/v2/turn` | Main conversation endpoint | Synchronous response generation, async worker dispatch |
| `/v2/turn/probe` | Health check for turn endpoint | Status verification |
| `/conversation` | Conversation management | Session handling, history |
| `/conversation-history` | Retrieve past conversations | History queries (includes `source: text\|voice`) |
| `/chat` | Legacy chat interface | Chat operations |

#### Voice Routes (Frontend API)

| Route | Purpose | Key Operations |
|-------|---------|----------------|
| `/api/voice/turn` | Voice conversation endpoint | Whisper STT → Sakhi turn → OpenAI TTS |
| `/api/voice/tts` | Standalone TTS | Text to speech with voice options (nova, shimmer, alloy) |

#### Memory & Recall Routes

| Route | Purpose |
|-------|---------|
| `/memory` | Memory recall operations |
| `/memory-graph` | Memory graph operations |
| `/retrieval` | Hybrid semantic + keyword search |
| `/memories` | List recent memories |

#### Personal Intelligence Routes

| Route | Purpose |
|-------|---------|
| `/persona` | User persona management |
| `/soul` | Soul state engine |
| `/soul-analytics` | Soul analytics (values, shadow, light, conflicts) |
| `/emotion-soul-rhythm` | Emotion x Soul x Rhythm integration |
| `/identity-momentum` | Identity evolution tracking |
| `/identity-timeline` | Identity phase detection |
| `/identity-state` | Current identity state |

#### Planning & Action Routes

| Route | Purpose |
|-------|---------|
| `/planner` | Goal planning and decomposition |
| `/plan` | Create plan from objective |
| `/intents/{id}/commit` | Commit intent to plan |
| `/actions/task` | Task creation |

#### Rhythm & Body Routes

| Route | Purpose |
|-------|---------|
| `/rhythm` | Rhythm state engine |
| `/rhythm-soul` | Rhythm-soul integration |
| `/breath` | Breath tracking |
| `/body-signals` | Body signal recording (sleep, energy, meal, movement) |
| `/beats` | Daily rhythm windows |

#### Analytics & Insights Routes

| Route | Purpose |
|-------|---------|
| `/insights` | Generated insights |
| `/growth` | Growth tracking |
| `/patterns` | Pattern detection |
| `/alignment` | Value-goal alignment scoring |
| `/coherence` | Identity coherence calculation |
| `/forecast` | Future state prediction |

#### Daily Scaffolds Routes

| Route | Purpose |
|-------|---------|
| `/daily-reflection` | Daily reflection generation |
| `/evening-closure` | Evening closure ritual |
| `/morning-preview` | Morning preview |
| `/morning-ask` | Morning check-in |
| `/morning-momentum` | Morning momentum builder |
| `/micro-momentum` | Micro momentum interventions |
| `/micro-recovery` | Micro recovery breaks |
| `/micro-journey` | Micro journey scaffolds |

#### Friction Framework Routes

| Route | Purpose |
|-------|---------|
| `/friction-framework` | Friction framework API |
| `/profile/operating-system` | User's constitutional type (prakruti) |
| `/state/current` | Current state vs baseline (vikriti) |
| `/state/processing-capacity` | Agni (processing bandwidth) |
| `/state/cognitive-residue` | Ama (unprocessed stress) |
| `/state/vitality-reserve` | Ojas (long-term resilience) |

#### Lab & Debug Routes

| Route | Purpose |
|-------|---------|
| `/lab/*` | Lab endpoints for testing workers |
| `/graph-debug` | Memory graph debugging |
| `/dev` | Development utilities |

---

## 3. Service Layer Structure

**Location:** `sakhi/apps/api/services/`

### Service Organization

Services are organized by functional domain:

#### Memory Services (`/memory/`)

- **`memory_ingest.py`** - Ingests journal entries into memory system
- **`memory_short_term.py`** - Short-term memory operations
- **`memory_long_term.py`** - Long-term memory consolidation
- **`memory_episodic.py`** - Episodic memory (daily episodes)
- **`recall.py`** - Memory recall with semantic + keyword search
- **`context_synthesizer.py`** - Synthesizes memory context for LLM
- **`context_select.py`** - Selects relevant context
- **`deep_context.py`** - Deep context loading
- **`session_vectors.py`** - Session-level embeddings
- **`session_match.py`** - Session similarity matching
- **`personal_model_repo.py`** - Personal model CRUD operations

#### Conversation Services (`/conversation_v2/`)

- **`conversation_engine.py`** - Reply generation
- **`conversation_reasoner.py`** - Reasoning about user input
- **`conversation_context_builder.py`** - Builds context for conversation
- **`conversation_tone.py`** - Tone calibration

#### Turn Services (`/turn/`)

- **`deterministic_context_loader.py`** - Loads pre-computed intelligence
- **`context_cache.py`** - Context caching
- **`reply_service.py`** - Turn reply construction
- **`async_triggers.py`** - Queue job dispatch

#### Soul Services (`/soul/`)

- **`engine.py`** - Soul state extraction (values, shadow, light, conflicts)

#### Planner Services (`/planner/`)

- **`engine.py`** - Planning orchestration
- **`decompose.py`** - Goal decomposition
- **`extract.py`** - Intent extraction
- **`rank.py`** - Task prioritization
- **`commit.py`** - Plan commitment

#### Adaptive Response Services (`/response/`)

- **`pipeline.py`** - Main 5-stage adaptive pipeline
- **`sensing.py`** - Domain classification, symptom extraction
- **`knowledge_gap.py`** - Memory queries, gap analysis
- **`strategy.py`** - Response mode selection
- **`synthesizer.py`** - Context compression for LLM
- **`diagnostic_kb.py`** - Diagnostic question knowledge base

---

## 4. Database Schema

**Location:** `sakhi/infra/scripts/migrations/`

### Core Tables

#### Users & Authentication

```sql
CREATE TABLE users (
    id UUID PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    full_name TEXT,
    password_hash TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

#### Journal & Content

```sql
CREATE TABLE journal_entries (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    content TEXT NOT NULL,
    mood TEXT,
    facets JSONB DEFAULT '{}',
    layer TEXT DEFAULT 'inner',  -- 'inner' | 'outer'
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE journal_embeddings (
    entry_id UUID PRIMARY KEY REFERENCES journal_entries(id),
    embedding VECTOR(1536) NOT NULL
);
```

#### Memory System

```sql
-- Short-term memory (24-48h TTL)
CREATE TABLE memory_short_term (
    id UUID PRIMARY KEY,
    person_id UUID NOT NULL,
    entry_id UUID,
    text TEXT NOT NULL,
    embedding VECTOR(1536),
    salience FLOAT DEFAULT 0.5,
    ts TIMESTAMPTZ NOT NULL,
    ttl_hours INT DEFAULT 48,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Episodic memory (daily episodes)
CREATE TABLE memory_episodic (
    id UUID PRIMARY KEY,
    person_id UUID NOT NULL,
    window_start TIMESTAMPTZ NOT NULL,
    window_end TIMESTAMPTZ NOT NULL,
    summary TEXT NOT NULL,
    embedding VECTOR(1536),
    context_tags JSONB DEFAULT '[]',
    state_vector JSONB,  -- Dosha current state
    guna_vector JSONB,   -- Operating mode (sattva/rajas/tamas)
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Long-term memory (persistent patterns)
CREATE TABLE memory_long_term (
    id UUID PRIMARY KEY,
    person_id UUID NOT NULL,
    category TEXT NOT NULL,
    summary TEXT NOT NULL,
    evidence JSONB,
    confidence FLOAT DEFAULT 0.5,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

#### Personal Model (Central Intelligence Hub)

```sql
CREATE TABLE personal_model (
    person_id UUID PRIMARY KEY,

    -- Friction Framework (MVP)
    operating_system JSONB,      -- Prakruti (constitutional type)
    life_context JSONB,          -- Age, roles, life phase, constraints
    decision_profile JSONB,      -- Decision-making patterns

    -- Short-term state
    short_term JSONB DEFAULT '{}',

    -- Long-term patterns
    long_term JSONB DEFAULT '{}',  -- emotion, mind, soul layers

    -- Longitudinal learning
    longitudinal_state JSONB DEFAULT '{}',

    -- Rhythm & Energy
    rhythm_state JSONB,
    energy_state JSONB,

    -- Elemental & Ayurvedic
    elemental_state JSONB,
    dosha_baseline JSONB,

    -- Soul & Identity
    soul_state JSONB,
    identity_state JSONB,

    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

#### Conversation Sessions

```sql
CREATE TABLE conversation_sessions (
    id UUID PRIMARY KEY,
    person_id UUID NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_turn_at TIMESTAMPTZ
);

CREATE TABLE conversation_turns (
    id UUID PRIMARY KEY,
    session_id UUID REFERENCES conversation_sessions(id),
    user_message TEXT NOT NULL,
    assistant_message TEXT NOT NULL,
    metadata JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE session_summaries (
    session_id UUID PRIMARY KEY REFERENCES conversation_sessions(id),
    summary TEXT NOT NULL,
    compressed_at TIMESTAMPTZ DEFAULT NOW()
);
```

### Key Relationships

```
users (1) --+-- (*) journal_entries
            |-- (*) memory_short_term
            |-- (*) memory_episodic
            |-- (1) personal_model
            |-- (*) conversation_sessions
            |-- (*) intents
            +-- (*) tasks

journal_entries (1) --- (1) journal_embeddings
                    +-- (*) journal_inference

conversation_sessions (1) --- (*) conversation_turns
                          +-- (0..1) session_summaries

personal_model (1) --- stores all intelligence layers
```

---

## 5. Memory System Architecture

Sakhi implements a **three-tier memory architecture** inspired by human memory systems:

### Memory Tiers

```
+-------------------------------------------------------------+
|  TIER 1: SHORT-TERM MEMORY (24-48h)                         |
|  - Recent conversations, journal entries                     |
|  - High recall speed (embeddings + keywords)                |
|  - Auto-expiring (TTL)                                       |
|  - Table: memory_short_term                                 |
+-------------------------------------------------------------+
                            | Consolidation
+-------------------------------------------------------------+
|  TIER 2: EPISODIC MEMORY (days to weeks)                    |
|  - Daily episode summaries                                   |
|  - State vectors (dosha, guna)                              |
|  - Context tags (body, mind, emotion signals)               |
|  - Table: memory_episodic                                   |
+-------------------------------------------------------------+
                            | Pattern extraction
+-------------------------------------------------------------+
|  TIER 3: LONG-TERM MEMORY (weeks to months)                 |
|  - Persistent patterns, values, identity themes             |
|  - Soul state (shadow, light, conflicts)                    |
|  - Longitudinal learning                                     |
|  - Table: personal_model.long_term                          |
+-------------------------------------------------------------+
```

### Memory Consolidation Pipeline

**Worker:** `episodic_consolidation_v21` (runs after each turn)

**Process:**
1. Fetch recent journal entries (last 24h)
2. Summarize day using LLM (2-4 sentences, neutral/factual)
3. Embed summary (vector(1536))
4. Extract context tags (weak signals: sleep, stress, clarity, etc.)
5. Compute state vectors:
   - **Dosha vector**: `{vata, pitta, kapha}` from text signals
   - **Guna vector**: `{sattva, rajas, tamas}` from emotional tone
6. Store in `memory_episodic`

**File:** `sakhi/apps/worker/tasks/episodic_consolidation_v21.py`

---

## 6. Conversation Flow

**File:** `sakhi/apps/api/routes/turn_v2.py`

### Three-Phase Architecture

```
+---------------------------------------------------------------+
|                     USER MESSAGE                               |
+---------------------------------------------------------------+
                            |
+---------------------------------------------------------------+
|  PHASE 1: SYNCHRONOUS RESPONSE (< 500ms)                      |
|  |-- Load deterministic context (pre-computed intelligence)   |
|  |-- Run triage/intent extraction                             |
|  |-- Generate reply using context + orchestration             |
|  +-- Return response to user                                  |
+---------------------------------------------------------------+
                            |
+---------------------------------------------------------------+
|  PHASE 2: ASYNC WORKER QUEUE (background)                     |
|  |-- enqueue_turn_jobs() -> Redis Queue                       |
|  |-- RQ Workers process jobs asynchronously                   |
|  +-- Updates DB tables for next turn's deterministic context  |
+---------------------------------------------------------------+
                            |
+---------------------------------------------------------------+
|  PHASE 3: NEXT TURN                                           |
|  +-- Fresh deterministic context loaded with updated intel    |
+---------------------------------------------------------------+
```

### Deterministic Context Loader

**File:** `sakhi/apps/api/services/turn/deterministic_context_loader.py`

This shared module loads pre-computed intelligence for fast response generation:

| Category | Fields | Source |
|----------|--------|--------|
| **Friction Framework** | operating_system, life_context, decision_profile | personal_model |
| **Brain States** | forecast_state, coherence_state, alignment_state, nudge_state | personal_model |
| **Long-term Layers** | emotion, mind, soul | personal_model.long_term |
| **State Vectors** | state_vector, guna_vector | memory_episodic (recent) |
| **Continuity** | continuity_state | continuity_state |
| **Daily Context** | daily_reflection, evening_closure | daily_*_cache |
| **Morning Context** | morning_preview, morning_ask, morning_momentum | morning_*_cache |
| **Micro Context** | micro_momentum, micro_recovery | micro_*_cache |

### Worker Pipeline

**File:** `sakhi/apps/worker/pipelines/turn_updates/runner.py`

**Active Workers (as of January 2026):**

| Worker | Purpose | Updates | Frequency |
|--------|---------|---------|-----------|
| `turn_memory_update` | Ingests user message | memory_short_term | Every turn |
| `ayurvedic_pipeline` | Full Ayurvedic signal extraction | elemental_*, energy_*, personal_model | Every turn |
| `episodic_consolidation_v21` | Creates episodic episodes | memory_episodic (state_vector, guna_vector) | Every turn |
| `rhythm_forecast` | Updates rhythm state | personal_model.rhythm_state | Every turn |
| `identity_momentum_deep` | Tracks identity evolution | Identity Momentum state | Every turn |
| `emotion_soul_rhythm_deep` | Deep ESR integration | Emotion x Soul x Rhythm state | Every turn |
| `esr` | Emotion State Refresh | Current emotional state | Every turn |
| `soul_refresh` | Updates soul/prakriti state | Soul state | Every turn |
| `longitudinal_update` | Weekly learning | Longitudinal state | Every turn |
| `rhythm_soul_deep` | Deep rhythm-soul integration | Rhythm Soul state | Every turn |

---

## 7. Adaptive Response Pipeline

**Documentation:** `docs/ADAPTIVE_RESPONSE_FRAMEWORK.md`

The Adaptive Response Framework is Sakhi's 5-stage pipeline for forming intelligent, personalized responses:

### The 5-Stage Pipeline

```
+---------------------------------------------------------------+
|  STAGE 1: SENSING LAYER                                        |
|  |-- Domain Classification (Body/Mind/Life/General)           |
|  |-- Symptom/Topic Extraction                                  |
|  |-- Temporal Markers (recently, always, sometimes)           |
|  |-- Tone Detection (seeking help, venting, exploring)        |
|  +-- Specificity Assessment (vague vs detailed)               |
|  Output: SenseFrame                                            |
+---------------------------------------------------------------+
                            |
+---------------------------------------------------------------+
|  STAGE 2: KNOWLEDGE GAP ANALYSIS                               |
|  |-- Load user's Operating System (constitution)              |
|  |-- Determine diagnostic questions for symptom + constitution|
|  |-- Query memory sources for each question                   |
|  |-- Check state vectors for inferences                       |
|  +-- Compile: KNOWN / INFERRED / UNKNOWN                      |
|  Output: KnowledgeGap { known, inferred, to_ask }             |
+---------------------------------------------------------------+
                            |
+---------------------------------------------------------------+
|  STAGE 3: RESPONSE STRATEGY SELECTION                          |
|  |-- If UNKNOWN is empty -> RESPOND mode (enough info)        |
|  |-- If UNKNOWN has items -> INQUIRE mode (need more info)    |
|  |-- Select max 2 questions to ask (prioritized by dosha)     |
|  +-- Choose response template                                  |
|  Output: ResponseStrategy { mode, questions, template }        |
+---------------------------------------------------------------+
                            |
+---------------------------------------------------------------+
|  STAGE 4: CONTEXT SYNTHESIS                                    |
|  |-- Compress known facts into prompt-ready format            |
|  |-- Frame inferences with appropriate confidence             |
|  |-- Include constitution-specific guidance                   |
|  +-- Add response guardrails                                   |
|  Output: SynthesizedContext                                    |
+---------------------------------------------------------------+
                            |
+---------------------------------------------------------------+
|  STAGE 5: RESPONSE FORMATION                                   |
|  |-- Apply template: ACKNOWLEDGE -> CONNECT -> INQUIRE/RESPOND|
|  |-- Tone calibration based on SenseFrame                     |
|  +-- LLM generation with synthesized context                  |
|  Output: Response                                              |
+---------------------------------------------------------------+
```

### Memory Sources Queried

1. **Foundational (Onboarding)** - `personal_model.operating_system`, `life_context`, `decision_profile`
2. **State Vectors (Recent)** - `memory_episodic.state_vector`, `guna_vector`
3. **Episodic Memory** - `memory_episodic`, `memory_short_term`, semantic search
4. **Derived Intelligence** - Deep worker outputs in `personal_model`

### Response Modes

| Mode | When | Template |
|------|------|----------|
| **INQUIRE** | First interaction, little data | [ACKNOWLEDGE] -> [FRAME] -> [ASK 2 questions] |
| **CONNECT_AND_INQUIRE** | Has history | [ACKNOWLEDGE] -> [CONNECT known facts] -> [ASK 1 question] |
| **RESPOND** | Enough info | [ACKNOWLEDGE] -> [INSIGHT] -> [SUGGESTION] -> [CHECK] |

**Core Principle:** Never ramble with 10 possibilities. Pick the most likely 2-3 based on constitution and ask targeted questions.

---

## 8. Personal Model Structure

The `personal_model` table is the **single source of truth** for all user intelligence.

### Complete Field Structure

```sql
CREATE TABLE personal_model (
    person_id UUID PRIMARY KEY,

    -- === FRICTION FRAMEWORK (MVP) ===
    operating_system JSONB,        -- Prakruti: dosha baseline, type
    life_context JSONB,             -- Age, roles, life phase
    decision_profile JSONB,         -- Decision-making patterns

    -- === SHORT-TERM STATE ===
    short_term JSONB DEFAULT '{}',  -- Current dosha, guna, drift

    -- === LONG-TERM PATTERNS ===
    long_term JSONB DEFAULT '{}',   -- emotion, mind, soul layers

    -- === LONGITUDINAL LEARNING ===
    longitudinal_state JSONB DEFAULT '{}',  -- Weekly/monthly trends

    -- === RHYTHM & ENERGY ===
    rhythm_state JSONB,             -- Energy, stress, fatigue
    energy_state JSONB,             -- Activation load, grounding

    -- === ELEMENTAL & AYURVEDIC ===
    elemental_state JSONB,          -- 5 elements per dimension
    dosha_baseline JSONB,           -- Baseline dosha (prakruti)

    -- === SOUL & IDENTITY ===
    soul_state JSONB,               -- Values, shadow, light, conflicts
    identity_state JSONB,           -- Identity themes, momentum

    -- === BRAIN STATES ===
    forecast_state JSONB,           -- Future state predictions
    coherence_state JSONB,          -- Identity coherence
    alignment_state JSONB,          -- Value-goal alignment
    nudge_state JSONB,              -- Nudge recommendations

    -- === TIMESTAMPS ===
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

### Field Details

#### `operating_system` (Prakruti / Constitutional Type)

```json
{
  "type": "Adaptive-Performance",
  "primary": "Adaptive",
  "secondary": "Performance",
  "dosha_baseline": {
    "vata": 0.45,
    "pitta": 0.35,
    "kapha": 0.20
  },
  "computed_at": "2026-01-22T10:00:00Z",
  "source": "full_onboarding"
}
```

**Translation:**
- **Vata-dominant** -> "Adaptive OS" (creative, variable, quick-thinking)
- **Pitta-dominant** -> "Performance OS" (driven, intense, sharp)
- **Kapha-dominant** -> "Conservation OS" (steady, grounded, enduring)
- **Dual-dominant** -> Combination (e.g., "Adaptive-Performance")

#### `life_context` (Demographics & Constraints)

```json
{
  "age_range": "35-44",
  "location": "San Francisco, USA",
  "active_roles": ["professional", "partner_family"],
  "life_phase": "building",
  "responsibility_load": "shared",
  "allergies": "dairy",
  "foods_avoided": "gluten"
}
```

#### `decision_profile` (Decision-Making Patterns)

```json
{
  "primary_driver": "make_progress",
  "risk_tendency": "calculated_risk",
  "time_horizon": "year_two",
  "energy_tradeoff": "case_by_case",
  "flexibility_style": "reorganize"
}
```

#### `short_term` (Current State / Vikriti)

```json
{
  "current_dosha": {"vata": 0.6, "pitta": 0.3, "kapha": 0.1},
  "current_guna": {"sattva": 0.3, "rajas": 0.6, "tamas": 0.1},
  "baseline_drift": 0.3,
  "friction_state": "Chaos Friction",
  "operating_mode": "Activation Mode",
  "last_updated": "2026-01-22T14:00:00Z"
}
```

#### `long_term` (Persistent Patterns)

```json
{
  "emotion": {
    "baseline_mood": 0.65,
    "volatility": 0.3,
    "patterns": ["morning_dips", "afternoon_peaks"]
  },
  "mind": {
    "clarity_baseline": 0.7,
    "focus_capacity": 0.75,
    "patterns": ["morning_peak_focus"]
  },
  "soul": {
    "core_values": ["growth", "connection", "creativity"],
    "longing": ["more balance", "deeper relationships"],
    "aversions": ["conflict", "uncertainty"],
    "identity_themes": ["builder", "helper"],
    "commitments": ["daily meditation", "weekly reviews"],
    "shadow_patterns": ["perfectionism", "people-pleasing"],
    "light_patterns": ["resilience", "curiosity"],
    "conflicts": ["ambition vs rest"],
    "friction": ["work-life balance"],
    "confidence": 0.75,
    "updated_at": "2026-01-15T10:30:00Z"
  }
}
```

#### `longitudinal_state` (Trends)

```json
{
  "emotion": {
    "direction": "stable",
    "volatility": 0.25,
    "confidence": 0.7,
    "window": "30d"
  },
  "energy": {
    "direction": "declining",
    "magnitude": -0.1,
    "confidence": 0.65,
    "window": "14d"
  },
  "sleep": {
    "direction": "improving",
    "magnitude": 0.15,
    "confidence": 0.8,
    "window": "14d"
  }
}
```

---

## 9. Data Flow Diagrams

### End-to-End Conversation Flow

```
+-------------+
|    USER     |
+------+------+
       | "I keep getting headaches"
       v
+---------------------------------------------------------------+
|  FRONTEND (Next.js)                                            |
|  POST /v2/turn { text: "I keep getting headaches" }           |
+---------------------------------------------------------------+
       |
       v
+---------------------------------------------------------------+
|  BACKEND: /v2/turn (FastAPI)                                   |
|  +-----------------------------------------------------------+ |
|  | 1. Load Deterministic Context                              | |
|  |    |-- personal_model.operating_system                     | |
|  |    |-- personal_model.long_term.soul                       | |
|  |    |-- memory_episodic (recent state_vector)               | |
|  |    |-- morning_preview_cache                               | |
|  |    +-- continuity_state                                    | |
|  +-----------------------------------------------------------+ |
|  +-----------------------------------------------------------+ |
|  | 2. Run Adaptive Response Pipeline                          | |
|  |    |-- Sensing: Classify domain (Body)                     | |
|  |    |-- Knowledge Gap: Query memory for sleep, meals        | |
|  |    |-- Strategy: INQUIRE mode (missing pain details)       | |
|  |    |-- Synthesis: Build prompt with constitution           | |
|  |    +-- Formation: Generate reply                           | |
|  +-----------------------------------------------------------+ |
|  +-----------------------------------------------------------+ |
|  | 3. Generate Reply                                          | |
|  |    +-- LLM chat with synthesized context                   | |
|  +-----------------------------------------------------------+ |
|  +-----------------------------------------------------------+ |
|  | 4. Enqueue Workers (async)                                 | |
|  |    |-- turn_memory_update                                  | |
|  |    |-- ayurvedic_pipeline                                  | |
|  |    |-- episodic_consolidation_v21                          | |
|  |    +-- [8 deep workers...]                                 | |
|  +-----------------------------------------------------------+ |
|  +-----------------------------------------------------------+ |
|  | 5. Return Response                                         | |
|  |    { reply, entry_id, context, queued_jobs, ... }         | |
|  +-----------------------------------------------------------+ |
+---------------------------------------------------------------+
       |
       v
+---------------------------------------------------------------+
|  REDIS QUEUE (turn_updates)                                    |
|  +-------------------+  +-------------------+                  |
|  | turn_memory_update|  | ayurvedic_pipeline|  ...             |
|  +-------------------+  +-------------------+                  |
+---------------------------------------------------------------+
       |
       v
+---------------------------------------------------------------+
|  RQ WORKERS (Background)                                       |
|  +-----------------------------------------------------------+ |
|  | Worker 1: turn_memory_update                               | |
|  |   +-- INSERT INTO memory_short_term                        | |
|  +-----------------------------------------------------------+ |
|  +-----------------------------------------------------------+ |
|  | Worker 2: ayurvedic_pipeline (8 sub-workers)               | |
|  |   |-- INSERT INTO elemental_signal_stm                     | |
|  |   |-- INSERT INTO elemental_summary_weekly                 | |
|  |   +-- UPDATE personal_model SET elemental_state = ...      | |
|  +-----------------------------------------------------------+ |
|  +-----------------------------------------------------------+ |
|  | Worker 3: episodic_consolidation_v21                       | |
|  |   |-- Summarize day with LLM                               | |
|  |   |-- Compute state_vector (dosha)                         | |
|  |   |-- Compute guna_vector (sattva/rajas/tamas)             | |
|  |   +-- INSERT INTO memory_episodic                          | |
|  +-----------------------------------------------------------+ |
+---------------------------------------------------------------+
       |
       v
+---------------------------------------------------------------+
|  POSTGRESQL                                                    |
|  |-- memory_short_term (new entry)                            |
|  |-- memory_episodic (new episode with state_vector)          |
|  |-- elemental_signal_stm (new signals)                       |
|  |-- personal_model (updated state)                           |
|  +-- ... (all updated tables)                                 |
+---------------------------------------------------------------+
       |
       v
+---------------------------------------------------------------+
|  NEXT TURN (User's next message)                               |
|  +-- Load deterministic context with fresh intelligence        |
+---------------------------------------------------------------+
```

---

## 10. Key Technologies

### Backend Stack

- **Language:** Python 3.11+
- **Framework:** FastAPI (async web framework)
- **Database:** PostgreSQL 15+ with extensions:
  - `pgvector` - Vector embeddings (1536-dim)
  - `pg_trgm` - Trigram text search
  - `pgcrypto` - Encryption
- **Queue:** Redis + RQ (Redis Queue)
- **LLM Providers:** OpenAI, OpenRouter, Web (multi-provider routing)

### Frontend Stack

- **Framework:** Next.js 14 (React)
- **Language:** TypeScript
- **State:** React hooks, context
- **Auth:** Supabase Auth integration

### Infrastructure

- **Hosting:** Vercel (frontend), custom backend
- **Database:** Supabase (managed PostgreSQL)
- **Queue:** Redis Cloud or self-hosted
- **Monitoring:** Prometheus metrics (via `starlette_exporter`)

### File Structure

```
sakhi/
├── apps/
│   ├── api/              # FastAPI backend
│   │   ├── main.py       # Application entry point
│   │   ├── routes/       # API route modules (60+)
│   │   ├── services/     # Business logic services
│   │   ├── core/         # Core utilities (db, llm, utils)
│   │   ├── deps/         # Dependency injection
│   │   └── middleware/   # Middleware (auth, telemetry)
│   ├── worker/           # Background workers
│   │   ├── pipelines/    # Worker pipelines
│   │   └── tasks/        # Individual worker tasks (85+)
│   ├── engine/           # Computation engines
│   └── logic/            # Business logic
├── core/                 # Core domain logic
│   ├── soul/             # Soul state engines
│   ├── rhythm/           # Rhythm & energy engines
│   └── emotion/          # Emotion engines
├── libs/                 # Shared libraries
│   ├── embeddings/       # Embedding generation
│   ├── llm_router/       # LLM provider routing
│   ├── retrieval/        # Memory retrieval
│   ├── schemas/          # Pydantic schemas
│   └── ayurveda/         # Ayurvedic rules
├── infra/
│   └── scripts/
│       └── migrations/   # Database migrations (34+)
└── tests/                # Test suite

apps/web/                 # Next.js frontend
├── app/                  # App router pages
│   ├── experience/       # User experience flows
│   ├── api/              # API routes
│   └── auth/             # Auth pages
└── lib/                  # Frontend utilities
    ├── hooks/            # React hooks
    └── supabase/         # Supabase client
```

---

## Summary

Sakhi is a sophisticated AI companion built on a three-layer architecture (User-Facing Framework -> Scientific Bridge -> Ayurvedic Engine) with:

1. **60+ API routes** organized by functionality
2. **Comprehensive service layer** with memory, conversation, soul, planning, and rhythm services
3. **Three-tier memory system** (short-term -> episodic -> long-term)
4. **Personal model** as central intelligence hub with 15+ state dimensions
5. **10+ background workers** updating intelligence after each turn
6. **5-stage adaptive response pipeline** for personalized, constitution-aware responses
7. **PostgreSQL with pgvector** for semantic search and embeddings
8. **Redis Queue** for async worker processing

The system processes each conversation turn in three phases:
1. **Synchronous** (< 500ms): Load deterministic context -> generate reply -> return
2. **Async** (background): 10 workers update intelligence
3. **Next turn**: Fresh context with updated intelligence

All user intelligence is stored in the `personal_model` table, which acts as the single source of truth for doshas, gunas, elements, soul state, rhythm, energy, and longitudinal patterns.

---

## Related Documents

- [Pattern Crystallization Layer](./PATTERN_CRYSTALLIZATION_LAYER.md) - Design for threshold-based pattern promotion
- [Worker Audit](./WORKER_AUDIT.md) - Complete worker inventory and scheduler configurations
- [Adaptive Response Framework](./ADAPTIVE_RESPONSE_FRAMEWORK.md) - Response pipeline details
- [Conversation Flow](./Conversation-Flow.md) - Conversation architecture
- [Friction Framework API](./FRICTION_FRAMEWORK_API.md) - User-facing framework API
