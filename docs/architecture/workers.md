# Sakhi Workers Comprehensive Audit

> **Status:** Complete Audit
> **Created:** 2026-01-26
> **Purpose:** Document all workers, queues, schedulers, and their configurations

---

## Executive Summary

The Sakhi system uses **Redis RQ (Redis Queue)** for background job processing with a scheduler-based orchestration system. There are **12 distinct Redis queues**, **85+ worker task files**, and **2 pipeline runners** that handle both scheduled and event-triggered jobs.

---

## Redis Queue Architecture

### Queue Names & Environment Variables

| Queue Name | Env Variable | Default | Purpose |
|------------|-------------|---------|---------|
| **embeddings** | EMBEDDINGS_QUEUE | embeddings | Embedding generation jobs |
| **salience** | SALIENCE_QUEUE | salience | Salience detection |
| **reflection** | REFLECTION_QUEUE | reflection | Daily/weekly reflections, meta-analysis |
| **presence** | PRESENCE_QUEUE | presence | Presence outreach, insights delivery |
| **rhythm** | RHYTHM_QUEUE | rhythm | Rhythm inference and forecasting |
| **analytics** | ANALYTICS_QUEUE | analytics | Analytics cache, deep workers, forecasts |
| **patterns** | PATTERNS_QUEUE | patterns | Collective pattern learning |
| **learning** | LEARNING_QUEUE | learning | Longitudinal learning, personal model updates |
| **observe** | OBSERVE_PIPELINE_QUEUE | observe | Journal entry observation pipeline |
| **turn_updates** | TURN_JOBS_QUEUE | turn_updates | Turn-triggered async jobs (memory, planner, etc.) |
| **focus** | FOCUS_QUEUE | focus | Focus session management |
| **environment** | ENVIRONMENT_QUEUE | environment | Environment context refresh |

---

## Worker Orchestration

### Main Components

**File**: `sakhi/apps/worker/main.py`
- **Purpose**: Main RQ worker process
- **Registers all 12 queues**
- **Runs workers that listen to multiple queues simultaneously**
- **No built-in scheduler** - uses external scheduler calls

**File**: `sakhi/apps/worker/scheduler.py`
- **Purpose**: Centralized scheduler bridge
- **Called manually or via cron**
- **Enqueues jobs to appropriate queues based on time/day logic**
- **333 lines of scheduling logic**

---

## Pipeline Workers

### 1. Turn Updates Pipeline

**File**: `sakhi/apps/worker/pipelines/turn_updates/runner.py`
- **Function**: `process_turn_job(job_type, turn_id, person_id, payload)`
- **Queue**: `turn_updates`
- **Trigger**: Event-triggered (after /v2/turn API call)
- **Purpose**: Async processing after conversation turns

**Supported Job Types**:
| Job Type | Purpose |
|----------|---------|
| `turn_memory_update` | Memory ingestion via unified_ingest |
| `turn_planner_update` | Planner suggestion + commitment (disabled) |
| `turn_persona_update` | Session persona + soul + narrative updates (disabled) |
| `turn_rhythm_update` | Rhythm engine refresh (disabled) |
| `rhythm_forecast` | Rhythm forecasting |
| `turn_insight_update` | Insight generation (disabled) |
| `brain_refresh` | Brain state refresh (disabled) |
| `journal_enrich` | Journal enrichment + memory graph (disabled) |
| `episodic_consolidation_v21` | Episodic memory consolidation |
| `ayurvedic_pipeline` | Full Ayurvedic signal processing |
| `neutral_signal_extraction` | Neutral signal extraction (disabled) |
| `intent_extraction` | Extract actionable intents from turn text |
| `identity_momentum_deep` | Identity momentum tracking |
| `emotion_soul_rhythm_deep` | ESR deep integration |
| `esr` | Emotion state refresh |
| `soul_refresh` | Soul/prakriti state update |
| `longitudinal_update` | Weekly learning update |
| `rhythm_soul_deep` | Rhythm-soul deep sync |

**Dependencies**:
- Reads: journal_entries, personal_model, memory_episodic
- Writes: personal_model, memory_episodic, planner state, relationship state

### 2. Observe Pipeline

**File**: `sakhi/apps/worker/pipelines/observe_pipeline/runner.py`
- **Function**: `run_pipeline_job(payload)`
- **Queue**: `observe`
- **Trigger**: Event-triggered (after journal entry creation)
- **Purpose**: Process new journal entries through ingestion pipeline

**Processing Steps**:
1. Extract facets from journal content
2. Ingest via `ingest_journal_entry`
3. Run `ingest_fast` (lightweight processing)
4. Run `ingest_heavy` (full memory processing)
5. Mark entry as completed
6. Refresh context cache

**Dependencies**:
- Reads: journal_entries
- Writes: journal_entries, memory_short_term, memory_episodic, context caches

---

## Scheduled Workers

### Daily Workers

| Worker | File | Queue | Schedule | Purpose |
|--------|------|-------|----------|---------|
| Morning Preview | morning_preview_worker.py | reflection | 06:00 UTC | Morning snapshot generation |
| Morning Ask | morning_ask_worker.py | reflection | 06:10 UTC | Morning intention prompt |
| Morning Momentum | morning_momentum_worker.py | reflection | 06:15 UTC | Morning momentum builder |
| Micro Momentum | micro_momentum_worker.py | reflection | 09:00 UTC | Mid-morning nudge |
| Micro Recovery | micro_recovery_worker.py | reflection | 14:00 UTC | Afternoon recovery nudge |
| Focus Path | focus_path_worker.py | reflection | 08:00 UTC | Focus path generation |
| Mini Flow | mini_flow_worker.py | reflection | 08:15 UTC | Mini-flow generation |
| Micro Journey | micro_journey_worker.py | reflection | 06:00 UTC | Daily micro-journey |
| Evening Closure | evening_closure_worker.py | reflection | 20:00 UTC | Evening closure ritual |
| Daily Reflection | daily_reflection_worker.py | reflection | 21:00 UTC | Nightly reflection summary |
| Analytics Cache Sync | sync_analytics_cache.py | learning | 02:00 UTC | Nightly metrics refresh |
| Task Weaver Refresh | task_weaver_refresh.py | analytics | 06:00 UTC | Daily auto-priority recalc |
| Intent Decay | intent_evolution_decay.py | analytics | 07:00 UTC | Daily intent decay |
| Emotion Loop Refresh | emotion_loop_refresh.py | analytics | 04:00 UTC | Daily emotion loop update |
| Alignment Refresh | alignment_refresh.py | analytics | 05:00 UTC | Daily alignment map |
| Narrative Arc Refresh | narrative_arc_refresh.py | analytics | 07:00 UTC | Daily narrative arc |
| Pattern Sense Refresh | pattern_sense_refresh.py | analytics | 08:00 UTC | Daily pattern sense |
| Inner Dialogue Refresh | inner_dialogue_refresh.py | analytics | 09:00 UTC | Daily inner dialogue |
| Identity Drift Refresh | identity_drift_refresh.py | analytics | 10:00 UTC | Daily identity drift |
| Inner Conflict | inner_conflict.py | analytics | 11:00 UTC | Daily inner conflict |
| Coherence State | coherence.py | analytics | 12:00 UTC | Daily coherence |
| Forecast | forecast.py | analytics | 07:00 UTC + every 3h | Forecast refresh |
| Nudge Check | nudge_worker.py | analytics | Every hour :00 | Nudge eligibility check |
| Rhythm Soul Daily | rhythm_soul_deep.py | analytics | 06:00 UTC | Daily rhythm-soul sync |

### Weekly Workers

| Worker | File | Queue | Schedule | Purpose |
|--------|------|-------|----------|---------|
| Weekly Summary | jobs.py:run_weekly_summary | reflection | Mon 00:00 | Weekly reflection summary |
| Meta Audit | meta_audit.py | reflection | Sun 00:00 | Weekly meta-audit |
| Theme Inference | theme_inference.py | reflection | Sun 00:00 | Weekly theme consolidation |
| Meta Reflection | meta_reflection.py | reflection | Sun 06:00 | Weekly meta-reflection scoring |
| Collective Patterns | collective_patterns.py | patterns | Mon 00:00 | Weekly pattern aggregation |
| Theme Rhythm Links | update_theme_rhythm_links.py | analytics | Sun 00:00 | Theme-rhythm correlation |
| Rhythm Self-Adjustment | rhythm_adjustments.py | learning | Tue 00:00 | Rhythm self-adjustments |
| Rhythm Forecast | rhythm_forecast.py | rhythm | Mon 00:00 | Weekly rhythm forecasting |
| Rhythm Soul Weekly | rhythm_soul_deep.py | analytics | Mon 08:00 | Weekly rhythm-soul deep sync |
| ESR Weekly | esr_deep.py | analytics | Mon 09:00 | Weekly ESR deep sync |
| Identity Momentum | identity_momentum_deep.py | analytics | Wed 08:00 | Weekly identity momentum |
| Decision Graph | decision_graph_deep.py | analytics | Tue 09:00 | Weekly decision graph refresh |
| Identity Timeline | identity_timeline_deep.py | analytics | Sun 10:00 | Weekly identity timeline |
| Weekly Learning | weekly_learning_worker.py | learning | Mon 06:00 | Longitudinal learning update |
| Rhythm Rollup | weekly_rhythm_rollup_worker.py | analytics | Mon 05:00 | Weekly rhythm capacity patterns |
| Planner Pressure | weekly_planner_pressure_worker.py | analytics | Mon 04:00 | Weekly planner pressure rollup |
| Personal Model Update | turn_personal_model_update.py | learning | Mon 07:00 | Weekly trends-only PM update |
| Weekly Signals | weekly_signals_worker.py | analytics | Mon 03:00 | Weekly signals aggregation |

### Hourly Workers

| Worker | File | Queue | Schedule | Purpose |
|--------|------|-------|----------|---------|
| System Tempo | update_system_tempo.py | analytics | Every hour :00 | System tempo updates |
| Nudge Check | nudge_worker.py | analytics | Every hour :00 | Nudge eligibility check |

---

## Event-Triggered Workers

### Turn-Triggered (via /v2/turn API)

**Dispatcher**: `sakhi/apps/api/services/turn/async_triggers.py`

Default jobs enqueued after each turn (10 workers):
- `turn_memory_update` - Memory ingestion
- `ayurvedic_pipeline` - Full Ayurvedic signal processing
- `episodic_consolidation_v21` - Episodic with state vectors
- `rhythm_forecast` - Rhythm state update
- `identity_momentum_deep` - Identity momentum
- `emotion_soul_rhythm_deep` - Emotion × Soul × Rhythm
- `esr` - Emotion state refresh
- `soul_refresh` - Soul/prakriti state
- `longitudinal_update` - Weekly learning
- `rhythm_soul_deep` - Rhythm-soul sync

Optional (supported but not default):
- `intent_extraction` - Extracts actionable intents

### Journal Entry Triggered

**Dispatcher**: `sakhi/apps/api/services/observe/dispatcher.py`

Enqueues `observe` pipeline for every new journal entry.

### Focus Session Triggered

**Dispatcher**: `sakhi/apps/api/services/focus/engine.py`

Enqueues focus session tick jobs to `focus` queue during active focus sessions.

---

## Deep Workers (Lab-Tested, Production-Ready)

### Identity & Soul Deep Workers

| Worker | File | Purpose | Data Read | Data Write |
|--------|------|---------|-----------|------------|
| Identity Momentum Deep | identity_momentum_deep.py | Tracks identity evolution momentum | personal_model, memory_episodic | personal_model.identity_momentum_state |
| Rhythm Soul Deep | rhythm_soul_deep.py | Rhythm-soul alignment detection | personal_model.rhythm_state, soul_state | personal_model.rhythm_soul_state |
| ESR Deep | esr_deep.py | Emotion-soul-rhythm integration | memory_episodic, personal_model | personal_model.emotion_soul_rhythm_state |
| Decision Graph Deep | decision_graph_deep.py | Internal decision graph analysis | memory_episodic, personal_model | personal_model.internal_decision_graph |
| Identity Timeline Deep | identity_timeline_deep.py | Persona evolution tracking | memory_episodic, personal_model | personal_model (identity timeline) |
| Emotion Soul Rhythm Deep | emotion_soul_rhythm_deep.py | Deep ESR integration | memory_episodic, personal_model | personal_model.emotion_soul_rhythm_state |

---

## Ayurvedic Pipeline Workers

### Ayurvedic Pipeline Orchestrator

**File**: `ayurvedic_pipeline.py`
**Purpose**: Composite pipeline orchestrating elemental and energy sub-workers

**Sub-workers executed in sequence**:
1. `neutral_signal_extraction_worker` - Extracts neutral signals from STM
2. `elemental_stm_worker` - Elemental short-term memory processing
3. `elemental_weekly_worker` - Weekly elemental aggregation
4. `elemental_monthly_worker` - Monthly elemental aggregation
5. `personal_model_elemental_worker` - Updates personal model with elemental state
6. `energy_weekly_worker` - Weekly energy aggregation
7. `energy_monthly_worker` - Monthly energy aggregation
8. `personal_model_energy_worker` - Updates personal model with energy state

**Dependencies**:
- Reads: memory_short_term, elemental_signal_stm, personal_model
- Writes: elemental_signal_stm, elemental_weekly, elemental_monthly, energy_weekly, energy_monthly, personal_model

---

## Environment Variables for Timing

### Queue Names

```bash
REFLECTION_QUEUE=reflection
PRESENCE_QUEUE=presence
RHYTHM_QUEUE=rhythm
ANALYTICS_QUEUE=analytics
PATTERNS_QUEUE=patterns
LEARNING_QUEUE=learning
OBSERVE_PIPELINE_QUEUE=observe
TURN_JOBS_QUEUE=turn_updates
FOCUS_QUEUE=focus
ENVIRONMENT_QUEUE=environment
```

### Weekly Schedules (weekday: 0=Mon, 6=Sun)

```bash
WEEKLY_SUMMARY_WEEKDAYS=0
META_AUDIT_WEEKDAYS=6
THEME_INFERENCE_WEEKDAYS=6
META_REFLECTION_WEEKDAYS=6
COLLECTIVE_PATTERNS_WEEKDAYS=0
THEME_RHYTHM_LINKS_WEEKDAYS=6
RHYTHM_SELF_ADJUSTMENT_WEEKDAYS=1
RHYTHM_FORECAST_WEEKDAYS=0
RHYTHM_SOUL_WEEKLY_DAYS=0
LEARNING_WEEKLY_DAYS=0
RHYTHM_ROLLUP_WEEKLY_DAYS=0
PLANNER_ROLLUP_WEEKLY_DAYS=0
PM_UPDATE_WEEKLY_DAYS=0
WEEKLY_SIGNALS_DAYS=0
ESR_WEEKLY_DAYS=0
IDENTITY_MOMENTUM_DAYS=2
DECISION_GRAPH_DAYS=1
IDENTITY_TIMELINE_DAYS=6
```

### Hourly Schedules (0-23)

```bash
RHYTHM_SOUL_DAILY_HOUR=6
RHYTHM_SOUL_WEEKLY_HOUR=8
ESR_WEEKLY_HOUR=9
IDENTITY_MOMENTUM_HOUR=8
DECISION_GRAPH_HOUR=9
IDENTITY_TIMELINE_HOUR=10
LEARNING_WEEKLY_HOUR=6
RHYTHM_ROLLUP_WEEKLY_HOUR=5
PLANNER_ROLLUP_WEEKLY_HOUR=4
PM_UPDATE_WEEKLY_HOUR=7
WEEKLY_SIGNALS_HOUR=3
TASK_WEAVER_HOUR=6
ANALYTICS_CACHE_HOUR=2
INTENT_DECAY_HOUR=7
EMOTION_LOOP_HOUR=4
ALIGNMENT_REFRESH_HOUR=5
NARRATIVE_ARC_HOUR=7
PATTERN_SENSE_HOUR=8
INNER_DIALOGUE_HOUR=9
IDENTITY_DRIFT_HOUR=10
INNER_CONFLICT_HOUR=11
COHERENCE_STATE_HOUR=12
FORECAST_HOUR=7
FORECAST_INTERVAL_HOURS=3
MICRO_RECOVERY_HOUR=14
FOCUS_PATH_HOUR=8
MINI_FLOW_HOUR=8
MICRO_JOURNEY_HOUR=6
```

### Minute Schedules (0-59)

```bash
SYSTEM_TEMPO_MINUTE=0
NUDGE_CHECK_MINUTE=0
MORNING_ASK_MINUTE=10
MORNING_MOMENTUM_MINUTE=15
MICRO_MOMENTUM_MINUTE=0
MICRO_RECOVERY_MINUTE=0
FOCUS_PATH_MINUTE=0
MINI_FLOW_MINUTE=15
MICRO_JOURNEY_MINUTE=0
```

### Timeouts

```bash
TURN_JOBS_TIMEOUT=300
OBSERVE_PIPELINE_TIMEOUT=600
FOCUS_QUEUE_TIMEOUT=300
```

### Feature Flags

```bash
ENABLE_IDENTITY_WORKERS=true
ENABLE_REFLECTIVE_STATE_WRITES=true
ENABLE_RHYTHM_FORECAST_WRITES=false
ENABLE_WEEKLY_SYNTHESIS_WRITES=false
ENABLE_WEEKLY_SYNTHESIS_PERSONAL_MODEL_WRITES=false
SAKHI_DISABLE_QUEUE=0  # Set to 1 to run jobs inline (dev mode)
```

---

## Worker Task File Inventory (85+ files)

**Location**: `sakhi/apps/worker/tasks/`

### Complete List

1. alignment_refresh.py
2. ayurvedic_pipeline.py
3. brain_goals_themes_refresh.py
4. brain_update.py
5. check_inactive_users.py
6. coherence.py
7. collective_patterns.py
8. complete_task_enrichment.py
9. daily_reflection.py
10. daily_reflection_worker.py
11. embedding_consolidation.py
12. emotion_loop_refresh.py
13. emotion_soul_rhythm_deep.py
14. environment_refresh.py
15. episodic_consolidation_v21.py (37KB - largest worker)
16. esr_worker.py
17. evening_closure_worker.py
18. focus_path_worker.py
19. focus_session.py
20. forecast.py
21. generate_clarity_actions.py
22. goal_evolver.py
23. identity_drift_refresh.py
24. ingest_reflection_feedback.py
25. inner_conflict.py
26. inner_dialogue_refresh.py
27. intent_evolution_decay.py
28. learn_rhythm_profile.py
29. life_phase_mapper.py
30. memory_fanout.py
31. memory_synthesis.py
32. meta_audit.py
33. meta_reflection.py
34. meta_reflection_weekly.py
35. micro_journey_worker.py
36. micro_momentum_worker.py
37. micro_recovery_worker.py
38. mini_flow_worker.py
39. morning_ask_worker.py
40. morning_momentum_worker.py
41. morning_preview_worker.py
42. narrative_arc_refresh.py
43. nudge_worker.py
44. pattern_sense_refresh.py
45. pattern_trends.py
46. persona_mode_detector.py
47. persona_tuning.py
48. persona_updater.py
49. planner_auto_summary.py
50. presence_reflection.py
51. progressive_task_structuring.py
52. reflect_morning_presence.py
53. reflect_person_memory.py
54. reflect_value_alignment.py
55. reflective_loop.py
56. reinforcement_calibration.py
57. rhythm_adjustments.py
58. rhythm_forecast.py
59. rhythm_inference.py
60. rhythm_scheduler.py
61. send_rhythm_nudge.py
62. soul_extract_worker.py
63. soul_refresh_worker.py
64. soul_worker.py
65. summarize_evening_state.py
66. sync_analytics_cache.py
67. sync_breath_to_body.py
68. synthesize_meta_reflection.py
69. task_routing_worker.py
70. task_weaver_refresh.py
71. theme_inference.py
72. tone_continuity.py
73. turn_personal_model_update.py
74. update_conversation_state.py
75. update_emotional_context.py
76. update_prompt_profile.py
77. update_relationship_arcs.py
78. update_system_tempo.py
79. update_theme_rhythm_links.py
80. weekly_learning_worker.py
81. weekly_planner_pressure_worker.py
82. weekly_reflection.py (39KB - 2nd largest worker)
83. weekly_rhythm_rollup_worker.py
84. weekly_signals_worker.py (20KB)

---

## Data Dependencies Summary

### Primary Data Sources (Read)

- **journal_entries** - Raw journal text and metadata
- **memory_short_term** - Recent episodic memory
- **memory_episodic** - Consolidated episodic memory with state vectors
- **personal_model** - Central user state (soul, emotion, rhythm, identity, etc.)
- **rhythm_state** - Rhythm signals and forecasts
- **elemental_signal_stm** - Elemental signals (Ayurvedic)
- **forecast_cache** - Cached forecast state
- **tasks/planned_items** - Task and planner data
- **reflections** - Reflection history
- **focus_sessions** - Focus session data

### Primary Data Writes

- **personal_model** - All state updates (soul, emotion, rhythm, identity, etc.)
- **memory_episodic** - Episodic consolidations with vectors
- **memory_short_term** - STM updates
- **longitudinal_state** - Long-term learning patterns
- **elemental_weekly/monthly** - Ayurvedic aggregations
- **energy_weekly/monthly** - Energy aggregations
- **analytics_cache** - Cached analytics metrics
- **nudge_log** - Nudge delivery tracking
- **forecast_cache** - Forecast state
- **context caches** - Various context caches

---

## Suppression & Safety

### Suppression Framework

**Workers with suppression checks**:
- **nudge_worker.py** - HIGH sensitivity (requires very stable user state)

**Suppression Sensitivity Levels**:
- HIGH: Only runs when user is stable (nudges)
- MEDIUM: Standard protection
- LOW: Minimal protection

**Design Principle**: "Suppression First" - User agency > system initiative

---

## Scheduler Invocation

**Manual Execution**:
```bash
python sakhi/apps/worker/scheduler.py        # Runs all scheduled jobs
python sakhi/apps/worker/scheduler.py rhythm # Runs only rhythm jobs
```

**Expected Production Setup**:
- External cron job or process scheduler
- Calls scheduler.py on appropriate intervals
- Scheduler enqueues jobs to Redis queues
- Worker processes (main.py) pick up and execute jobs

---

## Recommendations

1. **Production Deployment**:
   - Set up cron jobs to call scheduler.py on appropriate intervals
   - Consider using systemd timers or Kubernetes CronJobs
   - Monitor Redis queue depth and worker lag

2. **Observability**:
   - Add metrics for queue depth per queue
   - Track worker execution times
   - Monitor failed job counts
   - Alert on stuck workers

3. **Configuration Management**:
   - Document all timing environment variables
   - Create environment-specific configs (dev/staging/prod)
   - Consider feature flags for expensive workers in development

4. **Safety**:
   - Expand suppression framework to more workers
   - Add circuit breakers for failing workers
   - Implement retry policies with exponential backoff

5. **Optimization**:
   - Review daily workers running in same hour (6:00-12:00 UTC cluster)
   - Consider staggering analytics workers
   - Profile long-running workers (episodic_consolidation_v21, weekly_reflection)

---

## Related Documents

- [Pattern Crystallization Layer](./PATTERN_CRYSTALLIZATION_LAYER.md) — Design for threshold-based pattern promotion
- [Conversation Turn Audit](./CONVERSATION_TURN_AUDIT.md) — Architecture audit findings (TBD)
