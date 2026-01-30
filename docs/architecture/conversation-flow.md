# Conversation Flow Architecture

This document describes the `/v2/turn` endpoint architecture, worker pipeline, and the flow of data through the Sakhi system during a conversation turn.

## Overview

When a user sends a message, it flows through three phases:
1. **Synchronous Response** - Immediate reply generation using deterministic context
2. **Async Worker Queue** - Background processing to update intelligence
3. **Next Turn Load** - Fresh deterministic context loaded for subsequent turns

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           CONVERSATION TURN FLOW                             │
└─────────────────────────────────────────────────────────────────────────────┘

User Message
     │
     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  1. SYNCHRONOUS PHASE (Response Generation)                                  │
│     ├── Load deterministic context (pre-computed intelligence)               │
│     ├── Run triage/intent extraction                                         │
│     ├── Generate reply using context + orchestration                         │
│     └── Return response to user                                              │
└─────────────────────────────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  2. ASYNC PHASE (Worker Queue)                                               │
│     ├── enqueue_turn_jobs() → Redis Queue                                    │
│     ├── RQ Workers process jobs asynchronously                               │
│     └── Updates DB tables for next turn's deterministic context              │
└─────────────────────────────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  3. NEXT TURN                                                                │
│     └── Fresh deterministic context loaded with updated intelligence         │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Endpoint: `/v2/turn`

**File:** `sakhi/apps/api/routes/turn_v2.py`

### Request Schema

```python
class TurnIn(BaseModel):
    text: str                      # User's message
    clarity_phrase: str | None     # Optional clarity hint
    capture_only: bool = False     # If true, only stores message (no reply)
    source: str = "text"           # Input source: "text" or "voice"
```

### Response Fields

| Field | Description |
|-------|-------------|
| `reply` | Generated response text |
| `entry_id` | UUID of stored journal entry |
| `context` | Memory context snapshot |
| `emotion` | Detected emotion state |
| `tone_blueprint` | Tone guidance for response |
| `queued_jobs` | List of workers triggered |
| `debug` | Diagnostic information |
| `narrative` | Unified narrative trace |

---

## Deterministic Context Loader

**File:** `sakhi/apps/api/services/turn/deterministic_context_loader.py`

This shared module loads pre-computed intelligence that informs the response. It's used by both `/v2/turn` and `/lab/live-turn` to ensure consistency.

### Context Fields Loaded

| Category | Fields | Source Table |
|----------|--------|--------------|
| **Friction Framework** | `operating_system`, `life_context`, `decision_profile` | `personal_model` |
| **Friction State** | `friction_state`, `friction_info`, `drift_percentage`, `energy_mode` | Computed from prakruti/vikriti |
| **Body State** | `body_state`, `body_state_translated` | `personal_model.body_state` |
| **Brain States** | `forecast_state`, `coherence_state`, `alignment_state`, `nudge_state` | `personal_model` |
| **Long-term Layers** | `emotion`, `mind`, `soul` | `personal_model.long_term` |
| **State Vectors** | `state_vector`, `guna_vector` | `memory_episodic` |
| **Continuity** | `continuity_state` | `continuity_state` |
| **Daily Context** | `daily_reflection`, `evening_closure` | `daily_*_cache` |
| **Morning Context** | `morning_preview`, `morning_ask`, `morning_momentum` | `morning_*_cache` |
| **Micro Context** | `micro_momentum`, `micro_recovery` | `micro_*_cache` |
| **Scaffolds** | `focus_path`, `mini_flow`, `micro_journey` | `*_cache` |
| **Reflection** | `reflection_trace` | `reflection_trace` |

---

## Worker Pipeline

### Queue Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  /v2/turn       │────▶│  Redis Queue    │────▶│  RQ Workers     │
│  endpoint       │     │  (turn_updates) │     │  (runner.py)    │
└─────────────────┘     └─────────────────┘     └─────────────────┘
        │                                               │
        │  enqueue_turn_jobs()                          │  process_turn_job()
        │                                               │
        ▼                                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                     WORKER DISPATCH TABLE                        │
├─────────────────────────────────────────────────────────────────┤
│  Job Type                    │  Handler Function                 │
├─────────────────────────────────────────────────────────────────┤
│  turn_memory_update          │  _handle_memory_update()          │
│  ayurvedic_pipeline          │  run_ayurvedic_pipeline()         │
│  episodic_consolidation_v21  │  run_episodic_consolidation_v21() │
│  rhythm_forecast             │  _handle_rhythm_forecast()        │
│  intent_extraction           │  _handle_intent_extraction()      │
│  identity_momentum_deep      │  _handle_identity_momentum_deep() │
│  emotion_soul_rhythm_deep    │  _handle_emotion_soul_rhythm_deep()│
│  esr                         │  _handle_esr()                    │
│  soul_refresh                │  _handle_soul_refresh()           │
│  longitudinal_update         │  _handle_longitudinal_update()    │
│  rhythm_soul_deep            │  _handle_rhythm_soul_deep()       │
└─────────────────────────────────────────────────────────────────┘
```

### Queue Configuration

| Setting | Environment Variable | Default |
|---------|---------------------|---------|
| Queue Name | `TURN_JOBS_QUEUE` | `turn_updates` |
| Redis URL | `REDIS_URL` | `redis://localhost:6379/0` |
| Job Timeout | `TURN_JOBS_TIMEOUT` | `300` seconds |
| Disable Queue | `SAKHI_DISABLE_QUEUE` | `0` (enabled) |

When `SAKHI_DISABLE_QUEUE=1`, jobs run inline (synchronously) instead of being queued.

---

## Worker Details

### Core Workers (Always Enabled)

| Worker | Description | Updates |
|--------|-------------|---------|
| `turn_memory_update` | Ingests user message into memory | `memory_short_term` |
| `ayurvedic_pipeline` | Full Ayurvedic signal extraction | `elemental_*`, `energy_*`, `personal_model` |
| `episodic_consolidation_v21` | Creates episodic episodes with state vectors | `memory_episodic.state_vector`, `memory_episodic.guna_vector` |
| `rhythm_forecast` | Updates rhythm state | `personal_model.rhythm_state` |

### Optional Workers (Available but not default)

| Worker | Description | Updates |
|--------|-------------|---------|
| `intent_extraction` | Extracts actionable intents from turn text | `intents` table |

### Deep Workers (Deterministic Intelligence)

| Worker | Description | Updates | Lab Equivalent |
|--------|-------------|---------|----------------|
| `identity_momentum_deep` | Tracks identity evolution patterns | Identity Momentum state | `identity-momentum-deep` |
| `emotion_soul_rhythm_deep` | Deep ESR integration | Emotion × Soul × Rhythm state | `emotion-soul-rhythm-deep` |
| `esr` | Emotion State Refresh | Current emotional state | `esr` |
| `soul_refresh` | Updates soul/prakriti state | Soul state | `soul-refresh` |
| `longitudinal_update` | Weekly learning, long-term patterns | Longitudinal state | `longitudinal-update` |
| `rhythm_soul_deep` | Deep rhythm-soul integration | Rhythm Soul state | `rhythm-soul-deep` |

### Disabled Workers (Pending Review)

| Worker | Reason |
|--------|--------|
| `neutral_signal_extraction` | Part of ayurvedic_pipeline, may be redundant |
| `turn_planner_update` | Needs architecture review |
| `turn_rhythm_update` | Conflicts with rhythm_forecast |
| `turn_persona_update` | Needs review |
| `turn_insight_update` | Needs review |
| `brain_refresh` | Needs review |
| `journal_enrich` | Needs review |

---

## Ayurvedic Pipeline (Composite Worker)

**File:** `sakhi/apps/worker/tasks/ayurvedic_pipeline.py`

The Ayurvedic pipeline orchestrates multiple sub-workers in sequence:

```
run_ayurvedic_pipeline()
     │
     ├── 1. run_neutral_signal_extraction_worker()
     │        └── Extracts neutral signals from STM
     │
     ├── 2. run_elemental_stm_worker()
     │        └── Processes elemental signals
     │
     ├── 3. run_elemental_weekly_worker()
     │        └── Aggregates weekly elemental patterns
     │
     ├── 4. run_elemental_monthly_worker()
     │        └── Aggregates monthly elemental patterns
     │
     ├── 5. run_personal_model_elemental_worker()
     │        └── Updates personal_model.elemental_state
     │
     ├── 6. run_energy_weekly_worker()
     │        └── Aggregates weekly energy patterns
     │
     ├── 7. run_energy_monthly_worker()
     │        └── Aggregates monthly energy patterns
     │
     └── 8. run_personal_model_energy_worker()
              └── Updates personal_model.energy_state
```

---

## Data Flow: Turn to Next Turn

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              TURN N                                          │
└─────────────────────────────────────────────────────────────────────────────┘

1. User sends message
        │
        ▼
2. Load deterministic context ◄─────────────────────────────────────┐
   (from previous worker runs)                                       │
        │                                                            │
        ▼                                                            │
3. Generate reply                                                    │
        │                                                            │
        ▼                                                            │
4. Queue workers ──────────────────────────────────────────────┐     │
        │                                                      │     │
        ▼                                                      │     │
5. Return response to user                                     │     │
                                                               │     │
                                                               ▼     │
┌─────────────────────────────────────────────────────────────────────────────┐
│                           ASYNC PROCESSING                                   │
│                                                                              │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐              │
│  │ Memory Update   │  │ Ayurvedic       │  │ Episodic        │              │
│  │                 │  │ Pipeline        │  │ Consolidation   │              │
│  │ → memory_stm    │  │ → elemental_*   │  │ → state_vector  │              │
│  └─────────────────┘  │ → energy_*      │  │ → guna_vector   │              │
│                       │ → personal_model│  └─────────────────┘              │
│                       └─────────────────┘                                    │
│                                                                              │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐              │
│  │ Deep Workers    │  │                 │  │                 │              │
│  │                 │  │ Identity        │  │ ESR             │              │
│  │ → soul_refresh  │  │ Momentum        │  │ → emotion_state │              │
│  │ → rhythm_soul   │  │ → identity_state│  │                 │              │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘              │
│                                                                    │         │
└────────────────────────────────────────────────────────────────────┼─────────┘
                                                                     │
                                      Updates DB tables ─────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                              TURN N+1                                        │
└─────────────────────────────────────────────────────────────────────────────┘

1. User sends next message
        │
        ▼
2. Load deterministic context ◄── Now includes updates from Turn N workers
        │
        ▼
   ... (cycle continues)
```

---

## Key Files

| File | Purpose |
|------|---------|
| `sakhi/apps/api/routes/turn_v2.py` | Main endpoint, orchestration |
| `sakhi/apps/api/services/turn/deterministic_context_loader.py` | Shared context loading |
| `sakhi/apps/api/services/turn/async_triggers.py` | Queue job dispatch |
| `sakhi/apps/worker/pipelines/turn_updates/runner.py` | Worker execution |
| `sakhi/apps/worker/tasks/ayurvedic_pipeline.py` | Ayurvedic composite worker |
| `sakhi/apps/worker/tasks/episodic_consolidation_v21.py` | Episodic with state vectors |

---

## Testing

### Lab Endpoints

The `/lab/live-turn` endpoint mirrors `/v2/turn` behavior for testing:

```
GET /lab/live-turn?person_id={uuid}&message={text}
```

### Lab Worker Panel

Individual workers can be tested via `/lab/run-worker`:

```
POST /lab/run-worker
{
  "person_id": "565bdb63-124b-4692-a039-846fddceff90",
  "worker": "identity-momentum-deep"
}
```

### Memory Details

View all deterministic intelligence for a user:

```
GET /lab/memory-details?person_id={uuid}
```

Returns:
- Friction Framework (operating_system, life_context, decision_profile)
- State vectors (from memory_episodic)
- All cache tables (daily, morning, micro, scaffolds)
- Continuity state
- Reflection trace

---

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SAKHI_DISABLE_QUEUE` | Run workers inline (sync) | `0` |
| `REDIS_URL` | Redis connection string | `redis://localhost:6379/0` |
| `TURN_JOBS_QUEUE` | Queue name | `turn_updates` |
| `TURN_JOBS_TIMEOUT` | Job timeout (seconds) | `300` |

---

## Demo User

For testing, use the demo user:

```
User ID: 565bdb63-124b-4692-a039-846fddceff90
Name: Vidhya
```
