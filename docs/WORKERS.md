# Sakhi Workers Architecture

> **Last Updated:** 2026-01-28
> **Version:** v2.0 (Turn workers optimized)

This document describes the worker architecture for Sakhi's background processing.

---

## Overview

Sakhi uses two types of background workers:

1. **Turn Workers** - Run after each conversation turn (`/v2/turn`) - **only 2 essential workers**
2. **Scheduled Workers** - Run on a time-based schedule (hourly/daily/weekly)

### v2 Optimization

Previously, 10+ workers ran on every conversation turn. This was reduced to **2 essential workers** because:

- **Context is preserved via**: conversation_history + memory_recall + memory_graph + personal_model
- **State workers moved to daily schedule**: They compute slowly-changing state that doesn't need per-turn updates
- **Result**: Faster turn processing, same intelligence depth

---

## Turn Workers (2 active)

These run after each `/v2/turn` via Redis queue (or inline with `SAKHI_DISABLE_QUEUE=1`).

| Worker | Purpose | Writes To |
|--------|---------|-----------|
| `turn_memory_update` | Captures turn text into memory | `memory_episodic`, `memory_short_term` |
| `episodic_consolidation_v21` | Creates episodes + state vectors + feeds memory graph | `memory_episodic`, `personal_model.*` |

**Source:** `sakhi/apps/api/routes/turn_v2.py` (queued_jobs list)

### Context Available Without Per-Turn Workers

The LLM still has rich context for every turn:

```
Per-Turn Context:
├── conversation_history     ← Recent turns verbatim
├── session_summary          ← Compressed older turns
├── memory_recall            ← Semantic search on memories
├── memory_graph             ← Relationships (goals, patterns, conflicts)
├── episodes + state_vectors ← From episodic_consolidation
├── ayurvedic_graph          ← Dosha/element knowledge (300+ nodes)
└── personal_model.*         ← Refreshed by daily workers
```

---

## Scheduled Workers

### Daily Workers (13 active)

| Worker | Hour | Purpose |
|--------|------|---------|
| `schedule_rhythm_soul_daily` | 06:00 | Ayurvedic rhythm-soul sync |
| `schedule_emotion_loop_daily` | 04:00 | Emotional state update |
| `schedule_forecast_jobs` | 07:00 | Capacity/mood forecast |
| `schedule_crystallization_daily` | 03:00 | Pattern crystallization |
| `schedule_theme_uprank_daily` | 06:00 | Theme ranking |
| `schedule_task_weaver_daily` | 06:00 | Task auto-priority |
| `schedule_intent_decay_daily` | 07:00 | Intent strength decay |
| `schedule_nudge_checks` | :00 | Hourly nudge evaluation |
| `schedule_ayurvedic_pipeline_daily` | 06:00 | Dosha/elemental state (moved from turn) |
| `schedule_identity_momentum_daily` | 06:00 | Identity evolution (moved from turn) |
| `schedule_emotion_soul_rhythm_daily` | 04:00 | Emotion integration (moved from turn) |
| `schedule_esr_daily` | 04:00 | Emotion state refresh (moved from turn) |
| `schedule_soul_refresh_daily` | 06:00 | Soul/prakriti state (moved from turn) |

### Weekly Workers (9 active)

| Worker | Day | Hour | Purpose |
|--------|-----|------|---------|
| `schedule_rhythm_forecast_jobs` | Mon | - | Rhythm forecast |
| `schedule_rhythm_soul_weekly` | Mon | 08:00 | Rhythm-soul deep |
| `schedule_theme_inference` | Sun | - | Theme consolidation |
| `schedule_theme_rhythm_links` | Sun | - | Theme-rhythm correlation |
| `schedule_weekly_learning` | Mon | 06:00 | Longitudinal learning |
| `schedule_rhythm_rollup_weekly` | Mon | 05:00 | Rhythm rollup |
| `schedule_weekly_signals` | Mon | 03:00 | Signals aggregation |
| `schedule_goal_evolver_weekly` | Mon | 08:00 | Goal evolution |
| `schedule_crystallization_weekly` | Mon | 04:00 | Weekly crystallization |

### Monthly Workers (1 active)

| Worker | When | Purpose |
|--------|------|---------|
| `schedule_crystallization_monthly` | 1st | Monthly pattern crystallization |

**Source:** `sakhi/apps/worker/scheduler.py`

---

## Workers Moved from Turn to Daily

The following workers were moved from per-turn to daily schedule in v2:

| Worker | Old Trigger | New Schedule | Reason |
|--------|-------------|--------------|--------|
| `ayurvedic_pipeline` | Per-turn | Daily 06:00 | Dosha changes slowly |
| `identity_momentum_deep` | Per-turn | Daily 06:00 | Identity evolves slowly |
| `emotion_soul_rhythm_deep` | Per-turn | Daily 04:00 | Deep integration, not real-time |
| `esr` | Per-turn | Daily 04:00 | Emotion state can be daily |
| `soul_refresh` | Per-turn | Daily 06:00 | Soul/prakriti changes over weeks |
| `rhythm_soul_deep` | Per-turn | Daily 06:00 | Already had daily schedule |
| `rhythm_forecast` | Per-turn | Weekly | Already had weekly schedule |
| `longitudinal_update` | Per-turn | Weekly | Already weekly via weekly_learning |

---

## Archived Workers

The following workers were archived on 2026-01-28 as they did not serve the core v1 vision.

**Location:** `sakhi/apps/worker/tasks/_archive/daily_v1/`

### Abstract/Vague Purpose (7 workers)

| File | Original Purpose | Reason Archived |
|------|------------------|-----------------|
| `alignment_refresh.py` | Value-behavior alignment | Too abstract, not core |
| `narrative_arc_refresh.py` | Life narrative arcs | Too abstract |
| `pattern_sense_refresh.py` | Pattern sensing | Vague purpose |
| `inner_dialogue_refresh.py` | Internal voice state | Too abstract |
| `identity_drift_refresh.py` | Identity drift | Duplicate of turn worker |
| `inner_conflict.py` | Inner conflict state | Too abstract |
| `coherence.py` | Coherence state | Too abstract |

### Proactive Outreach - Never Wired (10 workers)

These were developed but never connected to the scheduler's main block:

| File | Original Purpose | Reason Archived |
|------|------------------|-----------------|
| `evening_closure_worker.py` | Evening closure ritual | Never wired, proactive outreach |
| `morning_preview_worker.py` | Morning snapshot | Never wired |
| `morning_ask_worker.py` | Morning question | Never wired |
| `morning_momentum_worker.py` | Morning momentum | Never wired |
| `micro_momentum_worker.py` | Mid-morning nudge | Never wired |
| `micro_recovery_worker.py` | Afternoon recovery | Never wired |
| `focus_path_worker.py` | Focus guidance | Never wired |
| `mini_flow_worker.py` | Mini-flow session | Never wired |
| `micro_journey_worker.py` | Micro-journey | Never wired |
| `planner_auto_summary.py` | Daily planner summary | Low value |

### Weekly Workers Archive

**Location:** `sakhi/apps/worker/tasks/_archive/weekly_v1/` and `sakhi/apps/worker/_archive/weekly_v1/`

| File | Original Purpose | Reason Archived |
|------|------------------|-----------------|
| `meta_reflection.py` | Weekly reflection quality | Low value for v1 |
| `meta_audit.py` | Reflection bias checking | Too abstract |
| `collective_patterns.py` | Aggregate patterns across users | Multi-user feature |
| `rhythm_adjustments.py` | Adjust rhythm from collective | Depends on collective |
| `weekly_planner_pressure_worker.py` | Planner pressure rollup | Low value |
| `turn_personal_model_update.py` | PM trends update | Overlaps with weekly_learning |
| `esr_deep.py` | ESR weekly deep sync | Duplicate - daily covers |
| `decision_graph_deep.py` | Decision graph refresh | Too abstract |
| `identity_timeline_deep.py` | Identity timeline | Too abstract |

---

## Configuration

### Environment Variables

```bash
# Queue control
SAKHI_DISABLE_QUEUE=1          # 1 = inline workers (dev only), 0 = Redis queue (production)

# Redis
REDIS_URL=redis://localhost:6379/0

# Worker safety gates
ENABLE_IDENTITY_WORKERS=true
ENABLE_REFLECTIVE_STATE_WRITES=true
ENABLE_RHYTHM_FORECAST_WRITES=true

# Daily schedule hours (optional overrides)
AYURVEDIC_PIPELINE_HOUR=6
IDENTITY_MOMENTUM_HOUR=6
EMOTION_SOUL_RHYTHM_HOUR=4
ESR_DAILY_HOUR=4
SOUL_REFRESH_HOUR=6
```

### Running Workers

**Simple Mode (inline - dev only):**
```bash
SAKHI_DISABLE_QUEUE=1 uvicorn apps.api.main:app --port 8080
```

**Full Mode (with Redis - production):**
```bash
# Terminal 1: Redis
redis-server

# Terminal 2: API
uvicorn apps.api.main:app --port 8080

# Terminal 3: Worker
python -m sakhi.apps.worker.main
```

---

## Data Flow

```
User Message
      │
      ▼
  /v2/turn API
      │
      ├─── Response generated (LLM)
      │    └── Context: history + recall + memory_graph + personal_model
      │
      ▼
  Turn saved to DB
      │
      └─── QUEUED (production)
           └── 2 workers: turn_memory_update, episodic_consolidation_v21
               └── Memory captured, episodes created

Daily Schedule (overnight)
      │
      └── 13 daily workers refresh personal_model state
          └── ayurvedic, soul, identity, emotion, etc.
```

---

## Core v1 Vision

The active workers support these core capabilities:

1. **Memory & Episodic Consolidation** - Understanding what was shared (per-turn)
2. **Memory Graph** - Relationships between goals, patterns, activities (built over time)
3. **Ayurvedic State Tracking** - Dosha/elemental balance (daily refresh)
4. **Pattern Crystallization** - What keeps coming up (daily/weekly)
5. **Rhythm Forecasting** - Energy patterns by time of day (weekly)
6. **Identity Evolution** - How the person is changing (daily refresh)
7. **Goal/Intent Tracking** - Actionable items (daily decay)

Workers that didn't directly serve these capabilities were archived.

---

## Architecture Summary

| Category | Count | Frequency |
|----------|-------|-----------|
| Turn Workers | 2 | Every turn |
| Daily Workers | 13 | Once per day |
| Weekly Workers | 9 | Once per week |
| Monthly Workers | 1 | Once per month |
| **Total Active** | **25** | |
| Archived | 26 | Never |
