# Complete Personal Model Creation Logic & Components

**Document Version:** 1.0
**Last Updated:** January 7, 2026
**Analysis by:** Claude Sonnet 4.5

---

## Overview

This document provides a comprehensive mapping of how the `personal_model` table is created, updated, and maintained throughout the Sakhi system. It covers all 31 writers, 40+ state fields, complete data flow, scheduling, and architectural principles.

---

## 1. PERSONAL_MODEL TABLE STRUCTURE

The `personal_model` table is a **single-row-per-person** JSONB-heavy table storing the entire state:

### Core Columns:
- `person_id` (PRIMARY KEY)
- `short_term` (JSONB) - Recent observations, current state
- `long_term` (JSONB) - Consolidated identity synthesis
- `longitudinal_state` (JSONB) - **AUTHORITATIVE** structured trends
- `updated_at` (TIMESTAMP)

### 40+ State Fields (JSONB columns):
**Soul Layer**: `soul_state`, `soul_vector`, `soul_shadow`, `soul_light`, `soul_conflicts`, `soul_friction`, `soul_narrative`

**Emotion Layer**: `emotion`, `emotion_state`, `emotion_loop`

**Rhythm Layer**: `rhythm_state`, `rhythm_soul_state`, `emotion_soul_rhythm_state`

**Identity Layer**: `identity_state`, `identity_momentum_state`, `identity_timeline`, `persona_evolution_state`

**Alignment**: `alignment_state`, `coherence_state`, `coherence_report`, `conflict_state`

**Narrative**: `narrative_arcs`, `pattern_sense`, `inner_dialogue_state`

**Decision Support**: `internal_decision_graph`, `forecast_state`

**Daily Scaffolds**: `morning_preview_state`, `morning_ask_state`, `morning_momentum_state`, `micro_momentum_state`, `micro_recovery_state`, `daily_reflection_state`, `closure_state`

**Action Scaffolds**: `focus_path_state`, `mini_flow_state`, `micro_journey_state`, `nudge_state`

**Other**: `tone_state`, `empathy_state`, `microreg_state`, `relationship_state`, `goals_state`

---

## 2. DATA FLOW: FROM JOURNAL TO PERSONAL_MODEL

### Primary Pipeline:

```
USER WRITES JOURNAL
    ↓
POST /journal/v2
    ↓
unified_ingest.py → ingest_fast() + ingest_heavy()
    ↓
├─→ Create embeddings (text-embedding-3-small, 1536-dim)
├─→ Write to memory_short_term (text, vector, triage)
├─→ Write to journal_embeddings (with dedup)
├─→ Extract features:
│   ├─→ compute_emotion() → emotion summary
│   ├─→ compute_mind() → mind summary
│   └─→ compute_soul() → soul summary
├─→ build_identity_graph() → identity relationships
    ↓
update_personal_model()
    ↓
UPDATES personal_model:
├─→ short_term ← current observation
├─→ long_term.observations ← deduplicated history
├─→ long_term.merged_vector ← running average embedding
├─→ long_term.layers.emotion ← emotion summary
├─→ long_term.layers.mind ← mind summary
├─→ long_term.layers.soul ← soul summary
└─→ long_term.identity_graph ← patched separately
```

### Secondary Path: Episodic Promotion (Manual/Lab Only)

```
memory_short_term (20 recent entries)
    ↓
build_episodic_from_journals_v2() [EXPLICIT CALL ONLY]
    ↓
memory_episodic (1 journal = 1 episode)
    ├─→ record (summary, source_entry_ids)
    ├─→ vector_vec (embedded summary)
    ├─→ context_tags (dimension/polarity/intensity)
    ├─→ soul fields (conflict, friction, shadow, light)
    └─→ emotion_loop, rhythm_state snapshots
```

**Critical**: Episodic promotion is NOT automatic per journal entry—it's explicitly invoked by lab workers or debug routes.

---

## 3. ALL WRITERS TO PERSONAL_MODEL (31 Components)

### A. REAL-TIME WRITERS (Per Journal Entry)

#### 1. **personal_model.py** - Core Update
- **Function**: `update_personal_model()`
- **File**: `sakhi/apps/api/services/memory/personal_model.py`
- **Writes**: `short_term`, `long_term.observations`, `long_term.layers`, `long_term.merged_vector`
- **Trigger**: Every journal ingestion
- **Logic**:
  - Deduplicates observations by content hash
  - Maintains rolling average of embeddings
  - Syncs intents from `intent_evolution` table
  - Truncates to 50 observations max

#### 2. **unified_ingest.py** - Identity Graph
- **Function**: `ingest_heavy()`
- **File**: `sakhi/apps/api/services/ingestion/unified_ingest.py`
- **Writes**: `long_term.identity_graph`
- **Source**: `build_identity_graph()` - extracts relationships, roles, values

---

### B. WEEKLY DEEP WORKERS (Scheduled)

#### 3. **⭐ turn_personal_model_update.py** - AUTHORITATIVE TRENDS
- **Function**: `run_turn_personal_model_update()`
- **File**: `sakhi/apps/worker/tasks/turn_personal_model_update.py`
- **Writes**: `longitudinal_state` (ONLY this worker writes here)
- **Schedule**: Weekly Monday 7AM UTC
- **Sources**:
  - `rhythm_weekly_rollups` (body, mind, emotion, energy)
  - `planner_weekly_pressure` (work dimension)
  - `memory_episodic.context_tags` (polarity/intensity overlays)
- **Dimensions**: body, mind, emotion, energy, work
- **Schema per dimension**:
  ```json
  {
    "direction": "improving|stable|declining",
    "magnitude": 0.0-1.0,
    "volatility": "low|moderate|high",
    "confidence": 0.0-1.0,
    "window": "7d|30d|90d",
    "lifecycle": "emerging|stabilizing|established|decaying",
    "last_updated_at": "timestamp"
  }
  ```
- **Method**: Pure deterministic math, NO LLM

#### 4. **soul_refresh_worker.py** - Soul Aggregation
- **Function**: `soul_refresh_worker()`
- **File**: `sakhi/apps/worker/tasks/soul_refresh_worker.py`
- **Writes**: `soul_state`, `soul_vector`, `soul_shadow`, `soul_light`, `soul_conflicts`, `soul_friction`
- **Schedule**: Weekly + on-demand (keyword triggers)
- **Sources**: Aggregates from `memory_episodic` (1500 day window)
- **Logic**:
  - Set-based deduplication for core_values, identity_themes
  - List truncation for conflicts (top 10), friction (top 10)
  - Direction vector synthesis from all episodic soul vectors

#### 5. **brain_goals_themes_refresh.py** - Theme Clustering
- **Function**: `run_brain_goals_themes_refresh()`
- **File**: `sakhi/apps/worker/tasks/brain_goals_themes_refresh.py`
- **Writes**: `long_term.life_themes`, `long_term.active_goals_map`, `long_term.identity_alignment_score`
- **Schedule**: Episodic (after episodic memory builds)
- **Sources**: Clusters from `memory_episodic` (signal-first: soul_conflict, soul_friction, emotion_loop)
- **Method**: Vector clustering + semantic grouping
- **Also writes to**: `brain_goals_themes` table

#### 6. **narrative_deep.py** - Soul Narrative Synthesis
- **Function**: `generate_deep_soul_narrative()`
- **File**: `sakhi/apps/worker/narrative_deep.py`
- **Writes**: `soul_narrative`
- **Schedule**: Weekly
- **Sources**: Current `soul_state` + episodic retrieval (top 7 slices)
- **Method**: LLM synthesis (non-poetic, factual)
- **Output Schema**:
  ```json
  {
    "identity_arc": "string",
    "soul_archetype": "string",
    "life_phase": "string",
    "value_conflicts": ["string"],
    "healing_direction": "string",
    "narrative_tension": "string"
  }
  ```

#### 7. **identity_momentum_deep.py** - Directional Movement
- **Function**: `run_identity_momentum_deep()`
- **File**: `sakhi/apps/worker/identity_momentum_deep.py`
- **Writes**: `identity_momentum_state`
- **Schedule**: Weekly Wednesday 8AM
- **Sources**: `soul_state`, `emotion_state`, `rhythm_state` + 50 recent episodic
- **Output Schema**:
  ```json
  {
    "direction": "string",
    "magnitude": 0.0-1.0,
    "stability": "string",
    "confidence": 0.0-1.0,
    "evidence_summary": "string",
    "window_days": 90
  }
  ```

#### 8. **rhythm_soul_deep.py** - Energy-Meaning Alignment
- **Function**: `run_rhythm_soul_deep()`
- **File**: `sakhi/apps/worker/rhythm_soul_deep.py`
- **Writes**: `rhythm_soul_state`
- **Schedule**: Daily + Weekly
- **Sources**: 50 recent episodic + current `rhythm_state`, `soul_state`

#### 9. **esr_deep.py** - ESR Triangle Synthesis
- **Function**: `run_esr_deep()`
- **File**: `sakhi/apps/worker/esr_deep.py`
- **Writes**: `emotion_soul_rhythm_state`
- **Schedule**: Weekly Monday 9AM
- **Sources**: `emotion_state`, `soul_state`, `rhythm_state` + episodic

#### 10. **decision_graph_deep.py** - Internal Tensions
- **Function**: `run_decision_graph_deep()`
- **File**: `sakhi/apps/worker/decision_graph_deep.py`
- **Writes**: `internal_decision_graph`
- **Schedule**: Weekly Tuesday 9AM
- **Sources**: 50 recent episodic + `soul_state`, `goals_state`

#### 11. **identity_timeline_deep.py** - Persona Evolution
- **Function**: `run_identity_timeline_deep()`
- **File**: `sakhi/apps/worker/identity_timeline_deep.py`
- **Writes**: `identity_timeline`, `persona_evolution_state`
- **Schedule**: Weekly Sunday 10AM

---

### C. DAILY REFRESH WORKERS

#### 12. **narrative_arc_refresh.py**
- **File**: `sakhi/apps/worker/tasks/narrative_arc_refresh.py`
- **Writes**: `narrative_arcs`
- **Schedule**: Daily 7AM

#### 13. **pattern_sense_refresh.py**
- **File**: `sakhi/apps/worker/tasks/pattern_sense_refresh.py`
- **Writes**: `pattern_sense`
- **Schedule**: Daily 8AM

#### 14. **alignment_refresh.py**
- **File**: `sakhi/apps/worker/tasks/alignment_refresh.py`
- **Writes**: `alignment_state`
- **Schedule**: Daily 5AM
- **Logic**: Compares soul values vs active goals

#### 15. **emotion_loop_refresh.py**
- **File**: `sakhi/apps/worker/tasks/emotion_loop_refresh.py`
- **Writes**: `emotion_loop`
- **Schedule**: Daily 4AM

#### 16. **inner_dialogue_refresh.py**
- **File**: `sakhi/apps/worker/tasks/inner_dialogue_refresh.py`
- **Writes**: `inner_dialogue_state`
- **Schedule**: Daily 9AM

#### 17. **identity_drift_refresh.py**
- **File**: `sakhi/apps/worker/tasks/identity_drift_refresh.py`
- **Writes**: `identity_state` (drift indicators)
- **Schedule**: Daily 10AM

#### 18. **inner_conflict.py**
- **File**: `sakhi/apps/worker/tasks/inner_conflict.py`
- **Writes**: `conflict_state`
- **Schedule**: Daily 11AM

#### 19. **coherence.py**
- **File**: `sakhi/apps/worker/tasks/coherence.py`
- **Writes**: `coherence_state`
- **Schedule**: Daily 12PM

#### 20. **forecast.py**
- **File**: `sakhi/apps/worker/tasks/forecast.py`
- **Writes**: `forecast_state`
- **Schedule**: Daily + every 3 hours

---

### D. DAILY SCAFFOLD ENGINES (Mirrored to personal_model)

#### 21. **morning_preview/engine.py**
- **File**: `sakhi/apps/engine/morning_preview/engine.py`
- **Writes**: `morning_preview_state`
- **Schedule**: Daily 6AM

#### 22. **morning_ask/engine.py**
- **File**: `sakhi/apps/engine/morning_ask/engine.py`
- **Writes**: `morning_ask_state`
- **Schedule**: Daily 6:10AM

#### 23. **morning_momentum/engine.py**
- **File**: `sakhi/apps/engine/morning_momentum/engine.py`
- **Writes**: `morning_momentum_state`
- **Schedule**: Daily 6:15AM

#### 24. **micro_momentum/engine.py**
- **File**: `sakhi/apps/engine/micro_momentum/engine.py`
- **Writes**: `micro_momentum_state`
- **Schedule**: Daily 9AM

#### 25. **micro_recovery/engine.py**
- **File**: `sakhi/apps/engine/micro_recovery/engine.py`
- **Writes**: `micro_recovery_state`
- **Schedule**: Daily 2PM

#### 26. **focus_path/engine.py**
- **File**: `sakhi/apps/engine/focus_path/engine.py`
- **Writes**: `focus_path_state`
- **Schedule**: Daily 8AM

#### 27. **mini_flow/engine.py**
- **File**: `sakhi/apps/engine/mini_flow/engine.py`
- **Writes**: `mini_flow_state`, `mini_flow_rhythm_slot`
- **Schedule**: Daily 8:15AM

#### 28. **daily_reflection/engine.py**
- **File**: `sakhi/apps/engine/daily_reflection/engine.py`
- **Writes**: `daily_reflection_state`
- **Schedule**: Daily 9PM

#### 29. **evening_closure_worker.py**
- **File**: `sakhi/apps/worker/tasks/evening_closure_worker.py`
- **Writes**: `closure_state`
- **Schedule**: Daily 8PM

---

### E. PER-TURN ADAPTIVE ENGINES

#### 30. **tone/engine.py**
- **File**: `sakhi/apps/engine/tone/engine.py`
- **Writes**: `tone_state`
- **Trigger**: Per conversation turn

#### 31. **empathy/engine.py**
- **File**: `sakhi/apps/engine/empathy/engine.py`
- **Writes**: `empathy_state`
- **Trigger**: Per conversation turn

#### 32. **microreg/engine.py**
- **File**: `sakhi/apps/engine/microreg/engine.py`
- **Writes**: `microreg_state`
- **Trigger**: On-demand emotional regulation

---

## 4. COMPLETE SCHEDULING MAP

### Real-Time (Per Journal):
- `personal_model.update_personal_model()` → `short_term`, `long_term`

### Daily Schedule:
| Time | Worker | Field Updated |
|------|--------|---------------|
| 4AM | emotion_loop_refresh | emotion_loop |
| 5AM | alignment_refresh | alignment_state |
| 5AM | rhythm_rollup_weekly | (feeds longitudinal) |
| 6AM | morning_preview | morning_preview_state |
| 6AM | rhythm_soul_daily | rhythm_soul_state |
| 6:10AM | morning_ask | morning_ask_state |
| 6:15AM | morning_momentum | morning_momentum_state |
| 7AM | narrative_arc_refresh | narrative_arcs |
| 7AM | turn_personal_model_update | longitudinal_state |
| 8AM | pattern_sense_refresh | pattern_sense |
| 8AM | focus_path | focus_path_state |
| 8:15AM | mini_flow | mini_flow_state |
| 9AM | micro_momentum | micro_momentum_state |
| 9AM | inner_dialogue_refresh | inner_dialogue_state |
| 10AM | identity_drift_refresh | identity_state |
| 11AM | inner_conflict | conflict_state |
| 12PM | coherence | coherence_state |
| 2PM | micro_recovery | micro_recovery_state |
| 8PM | evening_closure | closure_state |
| 9PM | daily_reflection | daily_reflection_state |
| Every 3hr | forecast | forecast_state |

### Weekly Schedule:
| Day | Time | Worker | Field Updated |
|-----|------|--------|---------------|
| Monday | 7AM | turn_personal_model_update | longitudinal_state |
| Monday | 9AM | esr_deep | emotion_soul_rhythm_state |
| Monday | TBD | soul_refresh | soul_state, soul_vector |
| Tuesday | 9AM | decision_graph_deep | internal_decision_graph |
| Wednesday | 8AM | identity_momentum_deep | identity_momentum_state |
| Sunday | 10AM | identity_timeline_deep | identity_timeline |

---

## 5. FIELD-TO-WRITER COMPLETE MAPPING

| Field | Writer | Frequency | Data Source |
|-------|--------|-----------|-------------|
| `short_term` | personal_model.py | Per journal | Current observation |
| `long_term.observations` | personal_model.py | Per journal | Deduplicated history |
| `long_term.merged_vector` | personal_model.py | Per journal | Running avg embedding |
| `long_term.layers.emotion` | personal_model.py | Per journal | compute_emotion() |
| `long_term.layers.mind` | personal_model.py | Per journal | compute_mind() |
| `long_term.layers.soul` | personal_model.py | Per journal | compute_soul() |
| `long_term.identity_graph` | unified_ingest.py | Per journal | build_identity_graph() |
| `long_term.life_themes` | brain_goals_themes_refresh.py | Episodic | Clustered episodic |
| `long_term.active_goals_map` | brain_goals_themes_refresh.py | Episodic | Goal clustering |
| **`longitudinal_state`** | **turn_personal_model_update.py** | **Weekly Mon 7AM** | **rhythm_rollups + planner + episodic** |
| `soul_state` | soul_refresh_worker.py | Weekly + on-demand | memory_episodic.soul |
| `soul_vector` | soul_refresh_worker.py | Weekly + on-demand | Episodic direction vector |
| `soul_shadow` | soul_refresh_worker.py | Weekly + on-demand | memory_episodic.soul_shadow |
| `soul_light` | soul_refresh_worker.py | Weekly + on-demand | memory_episodic.soul_light |
| `soul_conflicts` | soul_refresh_worker.py | Weekly + on-demand | memory_episodic.soul_conflict |
| `soul_friction` | soul_refresh_worker.py | Weekly + on-demand | memory_episodic.soul_friction |
| `soul_narrative` | narrative_deep.py | Weekly | LLM synthesis of soul + episodic |
| `identity_momentum_state` | identity_momentum_deep.py | Weekly Wed 8AM | Episodic + soul/emotion/rhythm |
| `rhythm_soul_state` | rhythm_soul_deep.py | Daily 6AM + Weekly | Episodic + rhythm/soul states |
| `emotion_soul_rhythm_state` | esr_deep.py | Weekly Mon 9AM | ESR triangle synthesis |
| `internal_decision_graph` | decision_graph_deep.py | Weekly Tue 9AM | Episodic conflicts + soul/goals |
| `identity_timeline` | identity_timeline_deep.py | Weekly Sun 10AM | Persona evolution |
| `persona_evolution_state` | identity_timeline_deep.py | Weekly Sun 10AM | Persona tracking |
| `narrative_arcs` | narrative_arc_refresh.py | Daily 7AM | Narrative engine |
| `pattern_sense` | pattern_sense_refresh.py | Daily 8AM | Pattern engine |
| `alignment_state` | alignment_refresh.py | Daily 5AM | soul vs goals alignment |
| `coherence_state` | coherence.py | Daily 12PM | Multi-layer coherence |
| `conflict_state` | inner_conflict.py | Daily 11AM | Internal tension detection |
| `forecast_state` | forecast.py | Daily + 3hr | Risk/opportunity windows |
| `emotion_loop` | emotion_loop_refresh.py | Daily 4AM | Emotion regulation patterns |
| `inner_dialogue_state` | inner_dialogue_refresh.py | Daily 9AM | Internal dialogue tracking |
| `identity_state` | identity_drift_refresh.py | Daily 10AM | Drift indicators |
| `morning_preview_state` | morning_preview/engine.py | Daily 6AM | goals + rhythm snapshot |
| `morning_ask_state` | morning_ask/engine.py | Daily 6:10AM | Contextual question |
| `morning_momentum_state` | morning_momentum/engine.py | Daily 6:15AM | Day starter |
| `micro_momentum_state` | micro_momentum/engine.py | Daily 9AM | Intra-day boost |
| `micro_recovery_state` | micro_recovery/engine.py | Daily 2PM | Energy recovery |
| `focus_path_state` | focus_path/engine.py | Daily 8AM | Task prioritization |
| `mini_flow_state` | mini_flow/engine.py | Daily 8:15AM | Flow state support |
| `daily_reflection_state` | daily_reflection/engine.py | Daily 9PM | Day closure |
| `closure_state` | evening_closure_worker.py | Daily 8PM | Evening wrap-up |
| `tone_state` | tone/engine.py | Per turn | Conversation context |
| `empathy_state` | empathy/engine.py | Per turn | Emotional attunement |
| `microreg_state` | microreg/engine.py | On-demand | Emotion regulation |

---

## 6. DATA SOURCES FEEDING PERSONAL_MODEL

### Primary Sources:
1. **journal_entries** → Short-term memory → personal_model.long_term
2. **memory_episodic** → All deep workers → Various state fields
3. **rhythm_weekly_rollups** → longitudinal_state.body/mind/emotion/energy
4. **planner_weekly_pressure** → longitudinal_state.work
5. **intent_evolution** → long_term.intents
6. **brain_goals_themes** → long_term.life_themes, active_goals_map

### Supporting Sources:
- **memory_short_term** - Recent 20 entries for context
- **journal_embeddings** - Vector similarity retrieval
- **goals**, **milestones**, **planned_items** - Planning state
- **rhythm_state** (separate table) - Current rhythm snapshot
- **emotion_state** (separate table) - Current emotion snapshot

---

## 7. HOW PERSONAL_MODEL IS CONSUMED

### Primary Consumers:

**1. Conversation Turn Context** (`conversation_context_builder.py`)
- Reads: ALL state fields
- Usage: Assembles context for reply generation
- Includes: tone, empathy, soul, rhythm, goals, conflicts, coherence

**2. Daily/Micro Engine Context**
- Morning engines read: `goals_state`, `rhythm_state`, `alignment_state`
- Micro engines read: `emotion_state`, `forecast_state`, `conflict_state`
- Focus engines read: `coherence_state`, `focus_path_state`

**3. Weekly Workers (Self-Reference)**
- Deep workers read current states as reference frames
- Example: `identity_momentum_deep` reads `soul_state` to measure drift

**4. LLM Context Assembly** (`llm_router/context_builder.py`)
- Injects state snapshots into system prompts
- Provides grounding for LLM responses

**5. API Endpoints**
- `/brain` - Returns full brain state
- `/soul/*` - Soul/identity views
- `/alignment` - Alignment calculations
- `/coherence` - Coherence checks
- `/forecast` - Risk windows

---

## 8. DEPENDENCY CHAIN

### Sequential Dependencies:

```
1. Journal Entry (real-time)
    ↓
2. Short-Term Memory + Embeddings (real-time)
    ↓
3. personal_model.long_term update (real-time)
    ↓
4. [Manual] Episodic Promotion (explicit call)
    ↓
5. Weekly Aggregations (scheduled)
    ├─→ soul_refresh → soul_state
    ├─→ brain_goals_themes → life_themes
    └─→ turn_personal_model_update → longitudinal_state
    ↓
6. Weekly Deep Analysis (scheduled)
    ├─→ identity_momentum (depends on soul_state)
    ├─→ rhythm_soul (depends on rhythm + soul)
    ├─→ ESR (depends on emotion + soul + rhythm)
    └─→ decision_graph (depends on soul + goals)
    ↓
7. Daily Scaffolds (scheduled)
    └─→ Read all states, generate daily experiences
```

### Soft Dependencies:
- Per-turn engines (tone, empathy) read multiple states but don't block if missing
- Daily scaffolds generate even with partial state
- Forecast uses coherence + conflict but has fallbacks

---

## 9. AGGREGATION & CONSOLIDATION METHODS

### 1. **Longitudinal State** (Pure Deterministic Math)
- **File**: `turn_personal_model_update.py`
- **Method**:
  - Moving averages from weekly rollups
  - Volatility = standard deviation
  - Direction = threshold-based delta comparison
  - Confidence = sample size × consistency
  - Lifecycle promotion: emerging → stabilizing → established → decaying
- **NO LLM** - Pure SQL + Python math

### 2. **Soul State** (Set-Based Aggregation)
- **File**: `soul_refresh_worker.py`
- **Method**:
  - Set union with deduplication for core_values, identity_themes
  - Frequency-based ranking for conflicts/friction (top 10)
  - Vector averaging for direction synthesis
  - 1500-day rolling window

### 3. **Brain Goals/Themes** (Vector Clustering)
- **File**: `brain_goals_themes_refresh.py`
- **Method**:
  - Semantic clustering of episodic entries
  - Signal-first selection (prioritizes soul_conflict, emotion_loop entries)
  - Confidence scoring based on cluster density
  - Theme labeling via LLM

### 4. **Narrative Deep** (LLM Synthesis)
- **File**: `narrative_deep.py`
- **Method**:
  - Retrieval-grounded (top 7 episodic by similarity)
  - Structured JSON output schema
  - Non-poetic, factual stance
  - Grounded in current soul_state

---

## 10. CRITICAL ARCHITECTURE INSIGHTS

### Design Principles:

1. **Single Source of Authority**: `longitudinal_state` is the ONLY authoritative learning layer—all other states are provisional

2. **No LLM Identity Writes**: Only deterministic workers write to soul/identity fields (except narrative synthesis which is explicitly labeled as synthesis)

3. **Rolling State**: personal_model is overwrite-safe—always recomputable from source data

4. **Episodic as Evidence**: memory_episodic feeds analysis but isn't truth itself—it's compressed evidence

5. **Cache ≠ Memory**: Daily scaffolds are ephemeral support, not identity

### Safety Guarantees:

- ✅ No fixed personality labels
- ✅ All states are provisional and reversible
- ✅ Confidence decays without reinforcement
- ✅ Trends can reverse direction
- ✅ Human agency always preserved
- ✅ No diagnosis, no manipulation

### Known Architectural Gaps:

1. **Episodic promotion is manual** - Not automatic per journal entry
2. **person_id missing from episodic** - Uses user_id instead
3. **Some cache overlap** - Narrative caches vs pattern caches have similar roles
4. **Identity graph under-utilized** - Built per turn but not actively used by workers

---

## 11. COMPLETE FILE REFERENCE

### Core Infrastructure:
- `sakhi/apps/api/services/memory/personal_model.py` - Core update logic
- `sakhi/apps/api/services/memory/personal_model_repo.py` - Repository pattern
- `sakhi/apps/api/services/ingestion/unified_ingest.py` - Journal ingestion
- `sakhi/apps/api/services/memory/memory_episodic.py` - Episodic promotion

### Authoritative Worker:
- `sakhi/apps/worker/tasks/turn_personal_model_update.py` ⭐ **AUTHORITATIVE TRENDS**

### Weekly Deep Workers:
- `sakhi/apps/worker/tasks/soul_refresh_worker.py`
- `sakhi/apps/worker/tasks/brain_goals_themes_refresh.py`
- `sakhi/apps/worker/identity_momentum_deep.py`
- `sakhi/apps/worker/rhythm_soul_deep.py`
- `sakhi/apps/worker/esr_deep.py`
- `sakhi/apps/worker/decision_graph_deep.py`
- `sakhi/apps/worker/narrative_deep.py`
- `sakhi/apps/worker/identity_timeline_deep.py`

### Daily Refresh Workers:
- `sakhi/apps/worker/tasks/narrative_arc_refresh.py`
- `sakhi/apps/worker/tasks/pattern_sense_refresh.py`
- `sakhi/apps/worker/tasks/alignment_refresh.py`
- `sakhi/apps/worker/tasks/emotion_loop_refresh.py`
- `sakhi/apps/worker/tasks/inner_dialogue_refresh.py`
- `sakhi/apps/worker/tasks/identity_drift_refresh.py`
- `sakhi/apps/worker/tasks/inner_conflict.py`
- `sakhi/apps/worker/tasks/coherence.py`
- `sakhi/apps/worker/tasks/forecast.py`

### Scheduler:
- `sakhi/apps/worker/scheduler.py` - Orchestrates all scheduled jobs

---

## Summary

This is the complete personal model architecture:
- **32 writers** (31 active + 1 reader)
- **40+ state fields**
- **Fully traceable data lineage**
- **Deterministic where it matters most** (longitudinal_state)
- **LLM only for language synthesis** (narrative_deep)
- **Evidence-based with safety boundaries**

Every field has a clear owner, every update is scheduled or triggered explicitly, and the entire model is designed to be recomputable and reversible while respecting human agency.
