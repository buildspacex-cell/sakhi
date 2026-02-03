# The Friction Framework: Complete Ayurvedic Mapping
## Technical Implementation Guide

**Purpose:** This document maps the Friction Framework (user-facing terminology) to the underlying Ayurvedic intelligence layer (backend implementation) in Sakhi.

**Status:** Implementation Analysis & Integration Roadmap
**Date:** January 2026
**Updated:** February 2026 - Verified against current codebase

---

## Executive Summary

Sakhi now implements **~75-80% of the Friction Framework** through its Ayurvedic intelligence layer. The system computes doshas, gunas, elements, and soul states. Causal reasoning, pattern learning, and graph reasoning services have been built.

**The Hidden Engine Strategy:** Ayurveda powers everything, users see "Operating Systems" and "Friction States."

**Implemented Services (since Jan 2026):**
- `services/ayurveda/causal_reasoning.py` - "Why am I feeling X?" queries
- `services/ayurveda/pattern_learning.py` - Personal behavior → symptom correlations
- `services/ayurveda/graph_reasoning.py` - Graph-based recommendation logic
- `services/ayurveda/prakruti.py` + `vikriti.py` - Baseline vs current state
- `services/ayurveda/food_recommendations.py` - Dosha-aware food suggestions

**REMAINING GAP:** Knowledge Graph seed data (500 Ayurvedic nodes, 2000 edges) needs to be populated for full multi-hop reasoning. Seasonal/circadian adjustments and contraindication rules are partial.

---

## Table of Contents

1. [Core Framework Translation](#core-framework-translation)
2. [What's Already Built](#whats-already-built)
3. [Integration Gaps](#integration-gaps)
4. [Complete Mapping Tables](#complete-mapping-tables)
5. [API Design for User-Facing Framework](#api-design-for-user-facing-framework)
6. [Implementation Roadmap](#implementation-roadmap)

---

## Core Framework Translation

### The Three-Layer Model

```
┌─────────────────────────────────────────────┐
│  USER-FACING LAYER (Friction Framework)    │
│  - Operating Systems (Adaptive/Performance) │
│  - Operating Modes (Clarity/Activation)     │
│  - Friction States (Chaos/Intensity)        │
│  - Coherence Score, Alignment Score         │
└─────────────────────────────────────────────┘
                    ↕ Translation
┌─────────────────────────────────────────────┐
│  SCIENTIFIC BRIDGE LAYER                    │
│  - Autonomic nervous system dominance       │
│  - Chronobiology, circadian rhythms         │
│  - Allostatic load, HPA axis                │
│  - Polyvagal theory states                  │
└─────────────────────────────────────────────┘
                    ↕ Computation
┌─────────────────────────────────────────────┐
│  AYURVEDIC ENGINE LAYER (Internal)          │
│  - Doshas (Vata, Pitta, Kapha)             │
│  - Gunas (Sattva, Rajas, Tamas)            │
│  - Prakruti vs Vikriti                      │
│  - Pancha Mahabhutas (5 elements)          │
│  - Agni, Ama, Ojas, Prana                  │
└─────────────────────────────────────────────┘
```

---

## What's Already Built

### ✅ Fully Implemented

#### 1. Dosha Computation
**File:** `/apps/worker/enrich/state_vector.py` (lines 66-73)

**Current Implementation:**
```python
def compute_dosha_vector(text: str) -> Dict[str, float]:
    """
    Returns: {"vata": float, "pitta": float, "kapha": float}
    Range: -2.0 to 2.0 (relative imbalance)
    """
```

**Keywords tracked:**
- **Vata:** scattered, anxious, restless, irregular, dry, light, cold, mobile
- **Pitta:** intense, sharp, hot, critical, focused, driven, irritable, inflamed
- **Kapha:** heavy, slow, steady, stable, grounded, lethargic, attached, cool

**Storage:**
- Per-entry: `observation.state_vector['dosha']`
- Baseline: Should be in `personal_model_elemental.baseline` (currently computed but not explicitly stored as prakruti)

---

#### 2. Guna Tracking
**File:** Same as above (lines 79-98)

**Current Implementation:**
```python
def compute_gunas(text: str, valence: float, stress: float) -> Dict[str, float]:
    """
    Returns: {"sattva": float, "rajas": float, "tamas": float}
    All values 0-1, normalized to sum to 1.0
    """
```

**Keywords tracked:**
- **Sattva:** clarity, peace, calm, balanced, centered, aware, mindful, harmonious
- **Rajas:** active, restless, driven, passionate, intense, excited, agitated
- **Tamas:** tired, dull, foggy, heavy, inert, stuck, numb, depressed

**Storage:** `observation.state_vector['guna']`

---

#### 3. Five Elements (Pancha Mahabhutas)
**Files:**
- `/core/rhythm/elemental_projection_engine.py`
- `/db/migrations/2026_01_XX_elemental_rhythm_engine.sql`

**Current Implementation:**

**Three-Tier Temporal Architecture:**

1. **STM (Short-Term Memory)** - `elemental_signal_stm`
   - Per-signal projections with TTL
   - Dimensions: body, mind, emotion
   - Elements: earth, water, fire, air, ether (0-1 each)
   - Magnitude + confidence scores

2. **Weekly Summaries** - `elemental_summary_weekly`
   - Immutable rollups by week
   - Average element distribution per dimension
   - Volatility scores

3. **Monthly Summaries** - `elemental_summary_monthly`
   - Long-range trends
   - Monthly averages per dimension

4. **Personal Model Baseline** - `personal_model_elemental`
   ```json
   {
     "baseline": {
       "body": {"earth": 0.25, "water": 0.2, ...},
       "mind": {...},
       "emotion": {...}
     },
     "volatility": {"body": 0.15, "mind": 0.25, "emotion": 0.3},
     "recovery_rate": {"body": 0.8, "mind": 0.6, "emotion": 0.7},
     "coupling": {"body_mind": 0.4, "mind_emotion": 0.6, ...}
   }
   ```

**Projection Rules** (from signals):
- `dryness` → body.air +0.2
- `overactivation` → mind.fire +0.2, emotion.air +0.1
- `recovery_gap` → body.earth +0.1, emotion.water +0.1
- `evening_clustering` → mind.air +0.15

---

#### 4. Soul State Model
**Files:**
- `/sakhi/apps/brain/engines/soul_engine.py`
- `/infra/sql/20251201_build57_soul_engine.sql`

**Schema:**
```json
{
  "core_values": ["growth", "connection", "creativity"],
  "longing": ["more balance", "deeper relationships"],
  "aversions": ["conflict", "uncertainty"],
  "identity_themes": ["builder", "helper"],
  "commitments": ["daily meditation", "weekly reviews"],
  "shadow_patterns": ["perfectionism", "people-pleasing"],
  "light_patterns": ["resilience", "curiosity"],
  "confidence": 0.75,
  "updated_at": "2026-01-15T10:30:00Z"
}
```

**Extraction Methods:**
- **Deterministic (keyword-based):** Values, identity themes, commitments
- **LLM-powered:** Shadow/light/conflict/friction extraction from multiple entries

**Storage:** `personal_model.soul_state` (JSONB)

---

#### 5. Soul Analytics
**File:** `/sakhi/apps/api/routes/soul_analytics.py`

**Current Endpoints:**

**GET `/soul/state/{person_id}`**
```json
{
  "core_values": ["growth", "connection"],
  "identity_themes": ["builder", "helper"],
  "shadow": ["perfectionism", "avoidance"],
  "light": ["resilience", "creativity"],
  "conflicts": ["ambition vs rest"],
  "friction": ["work-life balance"],
  "confidence": 0.75
}
```

**GET `/soul/timeline/{person_id}`**
```json
{
  "timeline": [
    {
      "date": "2026-01-15",
      "shadow": ["perfectionism"],
      "light": ["resilience"],
      "conflict": ["ambition vs rest"],
      "friction": ["work-life balance"]
    }
  ]
}
```

**GET `/soul/summary/{person_id}`**
```json
{
  "top_shadow": ["perfectionism", "people-pleasing", "avoidance"],
  "top_light": ["resilience", "curiosity", "empathy"],
  "dominant_friction": "work-life balance",
  "identity_instability_index": 0.35,
  "coherence_score": 0.65
}
```

**Coherence Calculation:**
```python
identity_instability_index = len(shadow) / (len(light) + len(shadow))
coherence_score = 1.0 - identity_instability_index
```

---

#### 6. Energy Layer
**Files:**
- `/core/rhythm/energy/energy_computation.py`
- `/db/migrations/2026_01_XX_energy_layer.sql`

**Energy Primitives** (computed from elements):
- `activation_load`: How much you're "doing" (derived from fire + air)
- `grounding`: Stability and presence (derived from earth + water)
- `circulation`: Movement between states (derived from ether + element transitions)
- `recovery_efficiency`: How quickly you restore (inverse of recovery_rates)

**Tables:**
- `energy_summary_weekly`: Weekly energy primitives
- `energy_summary_monthly`: Monthly smoothing
- `personal_model_energy`: Baseline energy profile

---

#### 7. Rhythm-Soul Integration
**File:** `/sakhi/core/rhythm/rhythm_soul_engine.py`

**Fast Frame** (deterministic, <3ms):
```python
{
  "coherence_score": (values + 1) / (conflicts + 2) * energy_factor,
  "identity_momentum": (light + 1) / (shadow + conflicts + 2),
  "shadow_disruption": (shadow + conflicts) / ((light + 1) * 3),
  "rhythm_tone_adjustment": "soft" | "energized" | "steady"
}
```

**Deep Frame** (LLM-powered):
```python
{
  "alignment_level": energy - load + recovery - strain,
  "dominant_tension": "first tension zone signal",
  "tension_zones": [{value, time_slot, reason}],
  "coherence_zones": [{value, time_slot, support}]
}
```

---

#### 8. Pattern Detection
**File:** `/sakhi/apps/engine/pattern_sense/engine.py`

**Detections:**
- Emotional patterns (volatility, negative runs, weekday/hour groupings)
- Intent couplings (correlation between intent strength and sentiment)
- Task effects (completion rates, energy costs)
- Wellness correlations (body-emotion, mind-emotion)
- Rhythm signatures
- Seasonality patterns

---

#### 9. Inner Conflict Detection
**File:** `/sakhi/apps/engine/inner_conflict/engine.py`

**Conflict Sources:**
1. Anchor alignment mismatches (suppressed vs elevated)
2. Intent contradictions (opposing trends)
3. Emotional divergence (high intent + negative emotion)
4. Discipline vs comfort (undone high-priority tasks + negative mood)
5. Low coherence (coherence confidence <0.4)
6. Alignment map conflicts (avoid vs recommended)
7. Pattern couplings (mixed intent-pattern relationships)

**Output:**
```python
{
  "conflict_score": 0.65,  # Mean force of all conflicts
  "conflicts": [{"a": "ambition", "b": "rest", "force": 0.8, "evidence": [...]}],
  "dominant_conflict": {"anchor": "work-life balance", "force": 0.8}
}
```

---

#### 10. Identity Momentum & Timeline
**Files:**
- `/sakhi/core/soul/identity_momentum_engine.py`
- `/sakhi/core/soul/identity_timeline_engine.py`

**Identity Momentum (Fast Frame):**
```python
{
  "momentum_score": (light + values + 1) / (shadow + friction + 3),
  "emotional_drag": (shadow + friction) * 0.1 + (0.5 - mood_score * 0.5),
  "shadow_interference": shadow_count * 0.1,
  "momentum_direction": "forward" | "regressing" | "stagnant",
  "identity_push_pull": "push" | "pull" | "neutral"
}
```

**Identity Timeline (Fast Frame):**
```python
{
  "current_phase": "exploration" | "transition" | "renewal" | "steady",
  "phase_intensity": momentum_score,
  "persona_shift_tendency": "expanding" | "contracting" | "stable",
  "shadow_pressure": (shadow + friction) * 0.1,
  "emerging_identity_signal": "first theme or light pattern"
}
```

---

#### 11. Alignment Engine
**File:** `/sakhi/core/soul/alignment_engine.py`

**Computation:**
```python
value_goal_alignment = count_goals_mentioning_values() / total_goals
friction_penalty = min(0.5, len(friction) * 0.05)
conflict_penalty = min(0.5, len(conflicts) * 0.05)

alignment_score = value_goal_alignment - friction_penalty - conflict_penalty
```

**Output:**
```python
{
  "alignment_score": 0.65,
  "conflict_zones": friction + conflicts + aversions,
  "action_suggestions": ["context-aware recommendations"]
}
```

---

#### 12. Dosha Diagnosis Endpoint
**File:** `/sakhi/apps/api/diagnose.py`

**Function:** Takes user description → returns:
```json
{
  "dosha_vector": {"vata": 0.6, "pitta": 0.3, "kapha": 0.1},
  "primary": "vata",
  "rationale": "High mobility, irregular patterns, anxiety mentioned",
  "lifestyle_suggestions": [
    "Establish consistent daily routine",
    "Warm, grounding foods",
    "Gentle, restorative practices"
  ]
}
```

---

---

## Integration Gaps

### 🔴 CRITICAL CLARIFICATION: Knowledge Graph Status

**What EXISTS (Schema Only):**
- ✅ Database tables: `ay_nodes`, `ay_edges` (from `/infra/scripts/migrations/0006_ayurveda.sql`)
- ✅ Basic schema structure for graph representation

**What DOES NOT EXIST (Not Built):**
- ❌ **NO node data** - tables are empty or minimally populated
- ❌ **NO edge relationships** - no pacifies/aggravates/balances connections
- ❌ **NO reasoning engine** - no graph traversal or query logic
- ❌ **NO graph-driven recommendations** - current recommendations are hardcoded

**Impact:**
The Knowledge Graph was envisioned in the original "Rhythm Companion" architecture as the intelligent reasoning layer connecting the Five Element Matrix to personalized recommendations. **This layer is NOT built.** The Five Element Matrix ([elemental_signal_stm](elemental_signal_stm)) exists and tracks elemental states, but the graph that would reason over this data to generate intelligent recommendations does not exist.

**What This Means:**
- Current dosha-based recommendations in `/diagnose` endpoint are hardcoded if-then logic
- No intelligent food/habit recommendations based on multi-factor reasoning (dosha + season + time + personal preferences)
- Missing the "unfair advantage" reasoning engine that would make Sakhi's recommendations uniquely sophisticated

**Priority:** This should be elevated to a critical early-phase implementation (Phase 6, Week 11-14) as it's the reasoning engine that differentiates Sakhi from basic journaling apps.

---

### ❌ Not Yet Implemented

#### 1. Prakruti (Constitutional Type) Storage
**What's Missing:**
- Explicit storage of baseline dosha type as "Operating System"
- User profile field: `operating_system: "Adaptive" | "Performance" | "Conservation" | "Adaptive-Performance"`

**Current State:**
- Doshas computed per-entry
- Baseline exists in `personal_model_elemental` but not labeled as prakruti

**Implementation Needed:**
- Compute prakruti at signup from initial assessment
- Store in `personal_model.operating_system`
- API endpoint: `GET /profile/operating-system`

---

#### 2. Vikriti (Current Imbalance) Tracking
**What's Missing:**
- Explicit "current state vs baseline" deviation metric
- User dashboard showing "You're 30% off your natural baseline"

**Current State:**
- Current dosha computed per-entry
- Baseline elemental distribution exists
- No explicit comparison API

**Implementation Needed:**
- Compute daily/weekly vikriti from recent entries
- Compare to prakruti baseline
- API endpoint: `GET /state/current-vs-baseline`
- Return: `{"drift_score": 0.3, "dominant_imbalance": "vata_excess"}`

---

#### 3. Friction State Classification
**What's Missing:**
- Explicit mapping: Vata excess → "Chaos Friction"
- User-facing label on dashboard

**Current State:**
- Dosha imbalances computed
- Friction patterns tracked in soul state
- No explicit "friction state" classification

**Implementation Needed:**
- Add function: `classify_friction_state(dosha_vector, soul_friction)`
- Rules:
  - `vata > 0.4 above baseline → "Chaos Friction"`
  - `pitta > 0.4 above baseline → "Intensity Friction"`
  - `kapha > 0.4 above baseline → "Stagnation Friction"`
- API endpoint: `GET /state/friction-state`

---

#### 4. Operating Mode from Gunas
**What's Missing:**
- User-facing "Operating Mode" label
- Real-time mode display: "You're in Activation Mode"

**Current State:**
- Gunas computed per-entry
- Not exposed in user-facing APIs

**Implementation Needed:**
- Map guna proportions to modes:
  - `sattva > 0.5 → "Clarity Mode"`
  - `rajas > 0.5 → "Activation Mode"`
  - `tamas > 0.5 → "Recovery Mode"`
- API endpoint: `GET /state/operating-mode`

---

#### 5. Agni (Processing Capacity) Metric
**What's Missing:**
- Unified "processing capacity" score (0-100)
- Dashboard display: "Your processing capacity is at 65%"

**Current State:**
- `activation_load` exists in energy layer
- Not framed as "processing capacity"

**Implementation Needed:**
- Compute: `processing_capacity = 100 - (activation_load * 100)`
- Factor in recovery efficiency
- API endpoint: `GET /state/processing-capacity`

---

#### 6. Ama (Cognitive Residue) Tracking
**What's Missing:**
- Cumulative "unprocessed stress" metric
- Builds up over time, reduces with recovery

**Current State:**
- Friction tracked but not cumulative
- No decay mechanism

**Implementation Needed:**
- Track cumulative friction score
- Decay based on recovery activities (journaling, rest, etc.)
- API endpoint: `GET /state/cognitive-residue`
- Formula: `residue = sum(daily_friction) * (1 - recovery_efficiency)`

---

#### 7. Time-of-Day Dosha Windows
**What's Missing:**
- Explicit Vata/Pitta/Kapha time windows for recommendations
- "It's Kapha time (6-10am) — good for routine tasks"

**Current State:**
- Dosha rules exist (`dosha_rules.py`) but not time-based recommendations
- Chronobiology research cited but not implemented

**Implementation Needed:**
- Define time windows:
  - **Vata:** 2-6am, 2-6pm (movement, creativity)
  - **Pitta:** 10am-2pm, 10pm-2am (focus, intensity)
  - **Kapha:** 6-10am, 6-10pm (routine, grounding)
- API endpoint: `GET /recommendations/current-time-window`

---

#### 8. Seasonal Rhythm Adjustments (Ritucharya)
**What's Missing:**
- Seasonal dosha aggravation tracking
- Protocol adjustments by season

**Current State:**
- Seasons tracked in Ayurvedic graph (foods linked to seasons)
- Not applied to user protocols

**Implementation Needed:**
- Detect current season
- Adjust dosha baseline by season:
  - Summer → Pitta aggravation risk
  - Fall/Winter → Vata aggravation risk
  - Spring → Kapha aggravation risk
- API endpoint: `GET /recommendations/seasonal-protocol`

---

#### 9. Knowledge Graph & Food/Habit Recommendations
**What's Missing:**
- **Knowledge Graph implementation** (only schema exists)
- Active reasoning engine connecting doshas → foods → habits → outcomes
- "Try these foods to balance your Vata" with graph-based recommendations

**Current State:**
- ❌ **Knowledge Graph NOT built** (schema exists in `ay_nodes`, `ay_edges` tables but not implemented)
- ❌ Graph tables exist from `/infra/scripts/migrations/0006_ayurveda.sql` but not populated or queried
- ⚠️ Lifestyle suggestions are currently hardcoded in diagnosis endpoint, not graph-driven
- ✅ Five Element Matrix exists in `elemental_signal_stm` but graph reasoning layer missing

**What Knowledge Graph Needs:**
1. **Node population:**
   - Doshas (Vata, Pitta, Kapha) with qualities
   - Foods with elemental properties (heavy/light, hot/cold, oily/dry)
   - Habits/practices with time-of-day + dosha effects
   - Symptoms with dosha signatures

2. **Edge relationships:**
   - `food --[pacifies]--> dosha` (e.g., warm_oil_massage pacifies Vata)
   - `food --[aggravates]--> dosha` (e.g., cold_salad aggravates Vata)
   - `symptom --[indicates]--> dosha_imbalance`
   - `season --[aggravates]--> dosha`
   - `time_window --[favors]--> dosha`

3. **Reasoning engine:**
   - Graph traversal: Current imbalance → balancing foods/habits
   - Multi-hop reasoning: "User has Vata imbalance in winter during Vata time → 3x amplification → strong grounding protocol"
   - Personalization: Filter recommendations by user preferences, restrictions, location

**Implementation Needed:**
- Build and populate Knowledge Graph (see Phase 6 below)
- Query graph for personalized recommendations:
  - Foods that pacify current dominant dosha
  - Habits that balance detected imbalance
  - Time-appropriate activities
  - Seasonal adjustments
- API endpoint: `GET /recommendations/dosha-balancing`

---

#### 10. Ojas (Vitality Reserve) Tracking
**What's Missing:**
- Long-term vitality/resilience metric
- Builds with good practices, depletes with chronic stress

**Current State:**
- Not currently measured
- Could derive from long-term energy baselines

**Implementation Needed:**
- Compute from monthly energy summaries
- Factor in: sleep consistency, recovery patterns, chronic friction
- API endpoint: `GET /state/vitality-reserve`
- Scale: 0-100

---

#### 11. Coherence Score Refinement
**What's Missing:**
- More sophisticated coherence calculation using full framework

**Current State:**
```python
coherence_score = 1.0 - (len(shadow) / (len(light) + len(shadow)))
```

**Implementation Needed:**
- Enhanced formula:
```python
coherence_score = (
  (1.0 - identity_instability_index) * 0.4 +  # shadow/light balance
  alignment_score * 0.3 +                      # value-goal alignment
  (1.0 - baseline_drift) * 0.2 +               # prakruti-vikriti alignment
  energy_coherence * 0.1                        # rhythm stability
)
```

---

#### 12. Daily Rhythm Protocol Generator
**What's Missing:**
- Personalized daily schedule based on:
  - Operating system (prakruti)
  - Current state (vikriti)
  - Time-of-day dosha windows
  - Personal energy patterns

**Current State:**
- `/routines` endpoint exists but uses generic dosha modulation
- Not personalized to individual

**Implementation Needed:**
- Combine:
  - Personal baseline (prakruti)
  - Current imbalance (vikriti)
  - Time-of-day windows (Vata/Pitta/Kapha times)
  - Personal energy curves (from elemental_summary_weekly)
- API endpoint: `GET /protocols/daily-rhythm`
- Return: Hour-by-hour schedule with activity recommendations

---

## Complete Mapping Tables

### Table 1: Doshas → Operating Systems

| Ayurvedic | Framework | Scientific | Characteristics | Friction State | Current Tracking |
|-----------|-----------|-----------|----------------|----------------|------------------|
| **Vata** | **Adaptive OS** | Sympathetic-dominant, high neuroplasticity | Creative, variable, quick-thinking, prone to scatter | **Chaos Friction** (when excess) | ✅ Computed in `state_vector['dosha']` |
| **Pitta** | **Performance OS** | High metabolic output, precision-focused | Driven, intense, sharp, prone to burnout | **Intensity Friction** (when excess) | ✅ Computed in `state_vector['dosha']` |
| **Kapha** | **Conservation OS** | Parasympathetic-dominant, stability-focused | Steady, grounded, enduring, prone to stagnation | **Stagnation Friction** (when excess) | ✅ Computed in `state_vector['dosha']` |

**User-Facing Translation:**
- Backend: `{"vata": 0.5, "pitta": 0.3, "kapha": 0.2}`
- User sees: "You're an **Adaptive-Performance type** (creative and driven)"

---

### Table 2: Gunas → Operating Modes

| Ayurvedic | Framework | Scientific | Characteristics | User Experience | Current Tracking |
|-----------|-----------|-----------|----------------|-----------------|------------------|
| **Sattva** | **Clarity Mode** | PFC-dominant, low cortisol, parasympathetic tone | Balanced, clear, calm, focused, flow state | "You're in your optimal state" | ✅ Computed in `state_vector['guna']` |
| **Rajas** | **Activation Mode** | High dopamine, sympathetic activation | Energized, active, restless, passionate, unsustainable | "You're running high—great for execution" | ✅ Computed in `state_vector['guna']` |
| **Tamas** | **Recovery Mode** | Adenosine-dominant, low arousal | Heavy, tired, foggy, inert, restorative | "Your body is asking for rest" | ✅ Computed in `state_vector['guna']` |

**User-Facing Translation:**
- Backend: `{"sattva": 0.6, "rajas": 0.3, "tamas": 0.1}`
- User sees: "You're in **Clarity Mode** (optimal cognitive function)"

---

### Table 3: Prakruti vs Vikriti → Baseline vs Current

| Ayurvedic | Framework | Scientific | Meaning | Implementation Status |
|-----------|-----------|-----------|---------|---------------------|
| **Prakruti** | **Baseline State** | Constitutional set-point, genetic + early environment | Your natural dosha balance when healthy | ❌ Computed but not stored as distinct type |
| **Vikriti** | **Current State** | Adaptive response to stressors | Your current dosha balance (may be imbalanced) | ✅ Computed per-entry in `state_vector` |
| **Prakruti - Vikriti** | **Baseline Drift** | Allostatic load, deviation from homeostasis | How far you are from your natural state | ❌ Not explicitly computed |

**User-Facing Translation:**
- Backend: Prakruti = `{"vata": 0.4, "pitta": 0.35, "kapha": 0.25}`, Vikriti = `{"vata": 0.6, "pitta": 0.3, "kapha": 0.1}`
- User sees: "You're **30% off your natural baseline** (elevated Vata)"

---

### Table 4: Pancha Mahabhutas → Element Distribution

| Ayurvedic | Scientific | Characteristics | Dimension | Current Tracking |
|-----------|-----------|----------------|-----------|------------------|
| **Prithvi (Earth)** | Stability, structure | Grounded, stable, heavy, solid | Body/Mind/Emotion | ✅ `elemental_signal_stm` |
| **Jala (Water)** | Flow, cohesion | Fluid, smooth, cool, adaptive | Body/Mind/Emotion | ✅ `elemental_signal_stm` |
| **Agni (Fire)** | Transformation, metabolism | Hot, sharp, intense, light | Body/Mind/Emotion | ✅ `elemental_signal_stm` |
| **Vayu (Air)** | Movement, change | Mobile, light, dry, quick | Body/Mind/Emotion | ✅ `elemental_signal_stm` |
| **Akasha (Ether)** | Space, potential | Subtle, expansive, pervasive | Body/Mind/Emotion | ✅ `elemental_signal_stm` |

**User-Facing Translation:**
- Backend: `{"body": {"earth": 0.25, "water": 0.2, "fire": 0.35, "air": 0.15, "ether": 0.05}}`
- User sees: "Your body shows **high fire** (metabolic activation) and **moderate air** (movement)"

---

### Table 5: Agni, Ama, Ojas → Processing Metrics

| Ayurvedic | Framework | Scientific | User-Facing | Implementation Status |
|-----------|-----------|-----------|------------|---------------------|
| **Agni** | **Processing Capacity** | Metabolic bandwidth, HPA axis efficiency | "Your capacity to handle stress: 75%" | ❌ Derived from `activation_load` but not exposed |
| **Ama** | **Cognitive Residue** | Unprocessed stress accumulation, allostatic load | "Accumulated mental backlog: 35%" | ❌ Friction tracked but not cumulative |
| **Ojas** | **Vitality Reserve** | Immune resilience, nervous system capacity | "Your resilience reserve: 80%" | ❌ Not currently measured |
| **Prana** | **Life Force Energy** | Nervous system vitality, arousal | "Your fundamental aliveness: 70%" | ✅ Partially tracked in energy layer |
| **Tejas** | **Metabolic Fire** | Mitochondrial function, transformation ability | "Your inner drive: 65%" | ✅ Partially tracked in fire element |

**User-Facing Translation:**
- Backend: `activation_load = 0.65`
- User sees: "**Processing capacity: 65%** (moderate cognitive load)"

---

### Table 6: Dinacharya & Ritucharya → Rhythm Protocols

| Ayurvedic | Framework | Scientific | User-Facing | Implementation Status |
|-----------|-----------|-----------|------------|---------------------|
| **Dinacharya** | **Daily Rhythm Protocol** | Chronobiological optimization, circadian entrainment | "Your personalized daily routine" | ✅ `/routines` endpoint exists |
| **Ritucharya** | **Seasonal Protocol** | Seasonal adaptation, photoperiod response | "Adjusting for winter (Vata season)" | ❌ Seasons tracked in graph but not applied |
| **Vata Time** (2-6am, 2-6pm) | **Movement Energy Zone** | Circadian cortisol low, parasympathetic | "Best for creative work, light movement" | ❌ Not implemented |
| **Pitta Time** (10am-2pm, 10pm-2am) | **Intensity Energy Zone** | Peak cortisol, metabolic high | "Best for focused, challenging work" | ❌ Not implemented |
| **Kapha Time** (6-10am, 6-10pm) | **Grounded Energy Zone** | Building phase, stability | "Best for routine tasks, building" | ❌ Not implemented |

**User-Facing Translation:**
- Backend: Current time = 3pm (Vata time), User OS = Adaptive
- User sees: "It's **Movement Energy Zone** (3pm) — good time for a walk or light creative work"

---

### Table 7: Soul State → Identity Metrics

| Internal Field | Framework Term | User-Facing | Implementation Status |
|----------------|----------------|------------|---------------------|
| `core_values` | Values | "What you care about most" | ✅ Extracted & stored |
| `identity_themes` | Identity Themes | "How you see yourself" | ✅ Extracted & stored |
| `shadow_patterns` | Limiting Patterns | "Patterns holding you back" | ✅ Extracted & stored |
| `light_patterns` | Empowering Strengths | "Your natural gifts" | ✅ Extracted & stored |
| `conflicts` | Inner Conflicts | "Internal contradictions" | ✅ Detected & stored |
| `friction` | Friction | "Areas of tension" | ✅ Detected & stored |
| `longing` | Aspirations | "What you're reaching for" | ✅ Extracted & stored |
| `aversions` | Aversions | "What drains you" | ✅ Extracted & stored |
| `commitments` | Commitments | "What you're dedicated to" | ✅ Extracted & stored |

**User-Facing Translation:**
- Backend: `{"shadow": ["perfectionism", "people-pleasing"]}`
- User sees: "**Limiting patterns:** You tend toward perfectionism and over-accommodating others"

---

### Table 8: Coherence & Alignment Metrics

| Metric | Formula | Range | User-Facing | Implementation Status |
|--------|---------|-------|------------|---------------------|
| **Coherence Score** | `1.0 - (shadow / (light + shadow))` | 0-100% | "How aligned your identity is: 65%" | ✅ Computed in soul analytics |
| **Alignment Score** | `(value_goal_overlap) - (friction_penalty) - (conflict_penalty)` | 0-100% | "How aligned your actions are with values: 70%" | ✅ Computed in alignment engine |
| **Identity Momentum** | `(light + values + 1) / (shadow + friction + 3)` | 0-1+ | "Your growth momentum: 0.75 (forward)" | ✅ Computed in momentum engine |
| **Baseline Drift** | `distance(prakruti, vikriti)` | 0-100% | "You're 30% off your natural baseline" | ❌ Not computed |
| **Friction Score** | `(shadow + conflicts + friction_signals) / max_possible` | 0-100 | "Current friction: 35 (moderate)" | ❌ Not unified into single score |

---

### Table 9: Friction States (Dosha Imbalances)

| Ayurvedic Imbalance | Framework State | Scientific | Symptoms | Recommendations | Implementation |
|---------------------|----------------|-----------|----------|-----------------|----------------|
| **Vata Excess (Prakopa)** | **Chaos Friction** | Sympathetic overdrive, HPA axis dysregulation | Scattered, anxious, can't finish, insomnia, irregular | Routine, grounding, warm foods, oil massage, slow yoga | ✅ Detected, ❌ Not labeled |
| **Pitta Excess (Prakopa)** | **Intensity Friction** | Chronic cortisol, inflammation, allostatic load | Irritable, critical, perfectionism, burning out, heated | Cool down, rest, delegate, water, lunar practices | ✅ Detected, ❌ Not labeled |
| **Kapha Excess (Prakopa)** | **Stagnation Friction** | Metabolic slowdown, low arousal, low dopamine | Lethargic, stuck, unmotivated, heavy, resistant to change | Movement, stimulation, light foods, heat, novelty | ✅ Detected, ❌ Not labeled |

**Classification Logic (to implement):**
```python
def classify_friction_state(vikriti, prakruti):
    drift = {d: vikriti[d] - prakruti[d] for d in ["vata", "pitta", "kapha"]}

    if drift["vata"] > 0.4:
        return "Chaos Friction"
    elif drift["pitta"] > 0.4:
        return "Intensity Friction"
    elif drift["kapha"] > 0.4:
        return "Stagnation Friction"
    else:
        return None  # Balanced
```

---

## API Design for User-Facing Framework

### New Endpoints to Implement

#### 1. GET `/profile/operating-system`
**Returns user's constitutional type (prakruti)**

**Response:**
```json
{
  "operating_system": "Adaptive-Performance",
  "primary": "Adaptive",
  "secondary": "Performance",
  "dosha_baseline": {
    "vata": 0.45,
    "pitta": 0.35,
    "kapha": 0.20
  },
  "description": "You're naturally creative and driven, with high adaptability and strong execution capacity.",
  "strengths": [
    "Quick thinking and innovation",
    "Strong focus when engaged",
    "Adaptable to change"
  ],
  "vulnerabilities": [
    "Prone to scattered energy",
    "Risk of burnout from intensity",
    "Difficulty with routine"
  ],
  "optimal_conditions": [
    "Variety balanced with structure",
    "Challenging but not overwhelming work",
    "Regular movement and creative outlets"
  ]
}
```

**Implementation:**
- Compute prakruti from initial assessment or first 30 days of entries
- Store in `personal_model.operating_system`
- Translation:
  - Vata-dominant → "Adaptive"
  - Pitta-dominant → "Performance"
  - Kapha-dominant → "Conservation"
  - Dual-dominant → Combination (e.g., "Adaptive-Performance")

---

#### 2. GET `/state/current`
**Returns current state vs baseline (vikriti vs prakruti)**

**Response:**
```json
{
  "timestamp": "2026-01-15T14:30:00Z",
  "operating_mode": "Activation",
  "operating_mode_details": {
    "sattva": 0.3,
    "rajas": 0.6,
    "tamas": 0.1,
    "description": "You're in high-energy execution mode—good for getting things done, but unsustainable long-term."
  },
  "current_dosha": {
    "vata": 0.6,
    "pitta": 0.3,
    "kapha": 0.1
  },
  "baseline_drift": 0.3,
  "drift_direction": "vata_elevated",
  "friction_state": "Chaos Friction",
  "friction_score": 35,
  "description": "You're running 30% above your natural baseline—elevated Vata is creating scattered energy.",
  "immediate_actions": [
    "Take a 10-minute grounding break",
    "Close open loops (finish 1-2 small tasks)",
    "Breathwork: Nadi Shodhana for 5 minutes"
  ]
}
```

**Implementation:**
- Compute from last 7 days of entries
- Compare to prakruti baseline
- Classify friction state using dosha drift
- Return mode from latest guna state

---

#### 3. GET `/state/processing-capacity`
**Returns Agni (processing bandwidth)**

**Response:**
```json
{
  "processing_capacity": 65,
  "status": "moderate",
  "trend": "declining",
  "components": {
    "activation_load": 0.35,
    "recovery_efficiency": 0.7,
    "cognitive_residue": 0.25
  },
  "description": "You have moderate capacity right now. You're handling 35% load with 70% recovery efficiency, but 25% accumulated residue is reducing bandwidth.",
  "recommendations": [
    "Clear cognitive residue with a brain dump (5-minute journal)",
    "Delegate or defer low-priority tasks",
    "Schedule recovery time before taking on more"
  ]
}
```

**Implementation:**
```python
processing_capacity = 100 * (
  (1.0 - activation_load) * recovery_efficiency - (cognitive_residue * 0.5)
)
```

---

#### 4. GET `/state/cognitive-residue`
**Returns Ama (unprocessed stress)**

**Response:**
```json
{
  "cognitive_residue": 35,
  "status": "moderate",
  "trend": "accumulating",
  "sources": [
    {"type": "unresolved_conflict", "weight": 0.4, "description": "ambition vs rest"},
    {"type": "friction", "weight": 0.3, "description": "work-life balance tension"},
    {"type": "shadow_pattern", "weight": 0.2, "description": "perfectionism creating backlog"},
    {"type": "incomplete_task", "weight": 0.1, "description": "3 high-priority tasks undone"}
  ],
  "description": "You have moderate accumulated stress from unresolved conflicts and friction. This is reducing your processing capacity.",
  "clearing_actions": [
    "Journal about your ambition vs rest conflict",
    "Make a decision on one work-life balance issue",
    "Complete one high-priority task"
  ]
}
```

**Implementation:**
```python
cognitive_residue = sum([
  len(conflicts) * 0.4,
  len(friction) * 0.3,
  len(shadow_interference) * 0.2,
  incomplete_high_priority_tasks * 0.1
]) * (1 - recovery_efficiency)
```

---

#### 5. GET `/state/vitality-reserve`
**Returns Ojas (long-term resilience)**

**Response:**
```json
{
  "vitality_reserve": 75,
  "status": "good",
  "trend": "stable",
  "components": {
    "sleep_consistency": 0.8,
    "recovery_pattern": 0.75,
    "chronic_friction": 0.25,
    "baseline_energy": 0.7
  },
  "description": "Your long-term resilience is good. You're maintaining consistent practices and managing friction well.",
  "building_actions": [
    "Continue your current sleep routine",
    "Maintain weekly recovery practices",
    "Address chronic friction points before they compound"
  ],
  "depletion_risks": [
    "Work-life balance friction (25%) could become chronic stress"
  ]
}
```

**Implementation:**
```python
vitality_reserve = 100 * (
  (sleep_consistency * 0.3) +
  (recovery_pattern * 0.3) +
  ((1 - chronic_friction) * 0.2) +
  (baseline_energy * 0.2)
)
```

---

#### 6. GET `/recommendations/time-window`
**Returns current time-of-day recommendations**

**Response:**
```json
{
  "current_time": "2026-01-15T15:30:00Z",
  "time_window": {
    "name": "Movement Energy Zone",
    "ayurvedic_name": "Vata Time",
    "hours": "2pm - 6pm",
    "dominant_element": "air",
    "characteristics": ["mobile", "light", "changeable"]
  },
  "optimal_activities": [
    "Creative brainstorming",
    "Light physical movement (walk, stretch)",
    "Connecting with others (social energy high)",
    "Exploring new ideas"
  ],
  "avoid": [
    "Deep focused work requiring sustained concentration",
    "Complex decision-making",
    "Sedentary desk work"
  ],
  "personalized_tip": "As an Adaptive OS, this is your natural peak creativity window. Use it for ideation or problem-solving.",
  "next_window": {
    "name": "Grounded Energy Zone",
    "hours": "6pm - 10pm",
    "best_for": "Routine tasks, winding down, grounding practices"
  }
}
```

**Implementation:**
- Define 6 time windows per 24h cycle
- Map to Vata/Pitta/Kapha times
- Personalize based on user's OS (prakruti)

---

#### 7. GET `/recommendations/seasonal-protocol`
**Returns current season adjustments**

**Response:**
```json
{
  "current_season": "Winter",
  "season_dates": "Dec 21 - Mar 20",
  "dominant_dosha_risk": "Vata",
  "season_characteristics": ["cold", "dry", "light", "irregular"],
  "aggravation_signs": [
    "Increased anxiety or restlessness",
    "Dry skin, joints",
    "Irregular sleep or appetite",
    "Scattered focus"
  ],
  "protocol_adjustments": {
    "foods": [
      "Emphasize warm, cooked, oily foods",
      "Soups, stews, root vegetables",
      "Warm spices (ginger, cinnamon)",
      "Avoid cold, raw, dry foods"
    ],
    "practices": [
      "Oil massage (Abhyanga) before shower",
      "More grounding practices (less intense movement)",
      "Consistent daily routine (counter irregularity)",
      "Earlier bedtime (compensate for less daylight)"
    ],
    "rhythm": [
      "Wake time: 7am (slightly later than summer)",
      "Wind-down: 9pm (earlier to counter Vata)",
      "Movement: Gentle, restorative (not high-intensity)"
    ]
  },
  "personalized_tip": "As an Adaptive OS, winter amplifies your natural Vata. Extra grounding and routine are essential.",
  "next_season": {
    "name": "Spring",
    "dominant_risk": "Kapha",
    "starts": "Mar 21"
  }
}
```

**Implementation:**
- Detect current season from date + hemisphere
- Query Ayurvedic graph for seasonal recommendations
- Personalize based on user's OS

---

#### 8. GET `/protocols/daily-rhythm`
**Returns personalized daily schedule**

**Response:**
```json
{
  "date": "2026-01-15",
  "operating_system": "Adaptive-Performance",
  "current_state": {
    "friction_state": "Chaos Friction",
    "baseline_drift": 0.3,
    "processing_capacity": 65
  },
  "schedule": [
    {
      "time": "6:00 - 7:00",
      "window": "Grounded Energy Zone (Kapha)",
      "recommended": [
        "Wake gently (Adaptive OS benefits from gradual start)",
        "Warm water + lemon",
        "10-min grounding meditation",
        "Light stretching or yoga"
      ],
      "avoid": ["Checking phone immediately", "Rushing into tasks"],
      "energy_forecast": {"capacity": 60, "load": 10, "tone": "building"}
    },
    {
      "time": "7:00 - 10:00",
      "window": "Grounded Energy Zone (Kapha)",
      "recommended": [
        "Warm, nourishing breakfast",
        "Routine morning tasks (email, admin)",
        "Gradual ramp-up to focused work"
      ],
      "avoid": ["High-intensity creative work yet", "Skipping breakfast"],
      "energy_forecast": {"capacity": 75, "load": 30, "tone": "steady"}
    },
    {
      "time": "10:00 - 14:00",
      "window": "Intensity Energy Zone (Pitta)",
      "recommended": [
        "**Peak performance window**",
        "Complex, challenging work",
        "Important decisions",
        "Performance OS strengths shine here"
      ],
      "avoid": ["Scattered multitasking", "Low-value tasks"],
      "energy_forecast": {"capacity": 90, "load": 60, "tone": "peak"},
      "personalized_note": "This is your sweet spot—Pitta time + your Performance OS. Use it wisely."
    },
    {
      "time": "14:00 - 18:00",
      "window": "Movement Energy Zone (Vata)",
      "recommended": [
        "Creative work, brainstorming (Adaptive OS peak)",
        "Movement break (walk, stretch)",
        "Social connection, collaboration",
        "Lighter tasks, exploration"
      ],
      "avoid": ["Deep focused work", "Complex analysis"],
      "energy_forecast": {"capacity": 70, "load": 40, "tone": "light"},
      "personalized_note": "Natural creativity peak for Adaptive OS. Use for ideation."
    },
    {
      "time": "18:00 - 22:00",
      "window": "Grounded Energy Zone (Kapha)",
      "recommended": [
        "Wind-down routine (key for Chaos Friction)",
        "Warm dinner (grounding)",
        "Journaling (process the day)",
        "Gentle movement or restorative practice",
        "No screens after 21:00"
      ],
      "avoid": ["Intense work", "Stimulating content", "Complex problems"],
      "energy_forecast": {"capacity": 50, "load": 20, "tone": "settling"},
      "personalized_note": "Crucial recovery window—your Chaos Friction needs extra grounding."
    },
    {
      "time": "22:00 - 6:00",
      "window": "Sleep (Pitta then Vata)",
      "recommended": [
        "Aim for 7-8 hours",
        "Cool, dark room",
        "Consistent bedtime (22:30 ideal for Chaos Friction)"
      ],
      "energy_forecast": {"capacity": "recovery", "load": 0, "tone": "restoration"}
    }
  ],
  "adjustments_made": [
    "Extra grounding in evening (Chaos Friction protocol)",
    "Emphasized Pitta window for Performance OS",
    "Added movement in Vata window for Adaptive OS"
  ]
}
```

**Implementation:**
- Combine time-of-day windows
- User's prakruti (OS)
- Current vikriti (friction state)
- Personal energy baselines (from `personal_model_energy`)
- Output hour-by-hour schedule

---

#### 9. GET `/recommendations/dosha-balancing`
**Returns foods, habits, practices to balance current state**

**Response:**
```json
{
  "current_imbalance": "Vata Excess",
  "friction_state": "Chaos Friction",
  "recommendations": {
    "foods": [
      {
        "item": "Warm oatmeal with ghee and cinnamon",
        "reason": "Grounding, warm, oily—pacifies Vata",
        "ayurvedic_properties": ["warm", "heavy", "oily", "sweet"],
        "best_time": "Breakfast"
      },
      {
        "item": "Kitchari (mung dal + rice)",
        "reason": "Easy to digest, balancing, nourishing",
        "ayurvedic_properties": ["warm", "grounding", "moist"],
        "best_time": "Lunch or dinner"
      },
      {
        "item": "Golden milk (turmeric + milk + honey)",
        "reason": "Calming, warming, sleep-promoting",
        "ayurvedic_properties": ["warm", "soothing", "grounding"],
        "best_time": "Before bed"
      }
    ],
    "habits": [
      {
        "practice": "Abhyanga (self-oil massage)",
        "frequency": "Daily, before shower",
        "reason": "Nourishes tissues, calms nervous system, grounds Vata",
        "duration": "10-15 minutes"
      },
      {
        "practice": "Consistent routine",
        "frequency": "Daily",
        "reason": "Regularity counters Vata's irregularity",
        "specifics": ["Same wake time", "Same meal times", "Same bedtime"]
      },
      {
        "practice": "Nadi Shodhana (alternate nostril breathing)",
        "frequency": "2x daily",
        "reason": "Balances left/right brain, calms nervous system",
        "duration": "5-10 minutes"
      }
    ],
    "activities": [
      {
        "activity": "Gentle, grounding yoga",
        "frequency": "Daily",
        "reason": "Movement without aggravation—avoid vinyasa",
        "style": "Restorative, Yin, or slow Hatha"
      },
      {
        "activity": "Walking in nature",
        "frequency": "Daily",
        "reason": "Grounding through feet, calming, rhythmic",
        "duration": "20-30 minutes"
      }
    ],
    "avoid": [
      {
        "item": "Cold, raw foods (salads, smoothies)",
        "reason": "Aggravates Vata (cold, light, dry)"
      },
      {
        "item": "Excessive travel or change",
        "reason": "Increases irregularity and scatter"
      },
      {
        "item": "Multitasking",
        "reason": "Fragments attention—amplifies Chaos Friction"
      }
    ]
  },
  "source": "Ayurvedic graph database + dosha balancing principles"
}
```

**Implementation:**
- Query `ay_nodes` and `ay_edges` tables
- Filter by:
  - Current imbalance (vikriti)
  - Season
  - Time of day
  - User preferences (dietary restrictions, etc.)
- Return structured recommendations

---

#### 10. GET `/state/friction-score`
**Returns unified friction metric**

**Response:**
```json
{
  "friction_score": 35,
  "status": "moderate",
  "trend": "increasing",
  "breakdown": {
    "dosha_imbalance": 0.3,
    "soul_friction": 0.25,
    "conflicts": 0.2,
    "cognitive_residue": 0.15,
    "low_coherence": 0.1
  },
  "description": "You have moderate friction from multiple sources. The primary driver is dosha imbalance (30%).",
  "impact": "Friction is reducing your processing capacity by ~25% and coherence by ~15%.",
  "reduction_priorities": [
    {
      "source": "Dosha imbalance (Chaos Friction)",
      "action": "Implement grounding routine",
      "potential_reduction": "10-15 points"
    },
    {
      "source": "Soul friction (work-life balance)",
      "action": "Make one clear boundary decision",
      "potential_reduction": "8-10 points"
    },
    {
      "source": "Conflicts (ambition vs rest)",
      "action": "Journal to integrate both needs",
      "potential_reduction": "5-7 points"
    }
  ]
}
```

**Implementation:**
```python
friction_score = 100 * (
  (dosha_drift * 0.3) +           # Prakruti-vikriti distance
  (len(soul_friction) * 0.05) +   # Soul friction points
  (len(conflicts) * 0.04) +        # Inner conflicts
  (cognitive_residue * 0.25) +     # Accumulated ama
  ((1 - coherence_score) * 0.2)   # Identity instability
)
```

---

## Implementation Roadmap

### Phase 1: Foundation (Week 1-2)
**Goal:** Store prakruti, expose basic friction framework

**Tasks:**
1. Add `operating_system` field to `personal_model` table
2. Implement prakruti calculation from initial assessment or first 30 days
3. Store baseline dosha in `personal_model.operating_system_baseline`
4. Create `/profile/operating-system` endpoint
5. Create `/state/friction-state` classification function
6. Expose friction state in `/state/current` endpoint

**Deliverables:**
- ✅ Users can see their Operating System type
- ✅ Users can see if they're in a Friction State

---

### Phase 2: Current State (Week 3-4)
**Goal:** Show users their current state vs baseline

**Tasks:**
1. Implement vikriti calculation (7-day rolling average)
2. Compute baseline drift (prakruti - vikriti distance)
3. Create `/state/current` endpoint with full state
4. Map gunas to Operating Modes
5. Expose Operating Mode in API

**Deliverables:**
- ✅ Users see "You're 30% off your baseline"
- ✅ Users see "You're in Activation Mode"

---

### Phase 3: Processing Metrics (Week 5-6)
**Goal:** Expose Agni, Ama, Ojas as user-facing metrics

**Tasks:**
1. Compute Processing Capacity from activation_load
2. Implement Cognitive Residue accumulation + decay
3. Implement Vitality Reserve from long-term baselines
4. Create endpoints:
   - `/state/processing-capacity`
   - `/state/cognitive-residue`
   - `/state/vitality-reserve`

**Deliverables:**
- ✅ Users see processing bandwidth
- ✅ Users see accumulated stress
- ✅ Users see long-term resilience

---

### Phase 4: Time-Based Recommendations (Week 7-8)
**Goal:** Implement Vata/Pitta/Kapha time windows

**Tasks:**
1. Define 6 time windows (6h each, repeating)
2. Map to dosha dominance + characteristics
3. Create `/recommendations/time-window` endpoint
4. Generate optimal activities per window
5. Personalize based on user's OS

**Deliverables:**
- ✅ Users see "It's Movement Energy Zone—good for creative work"
- ✅ Time-aware recommendations

---

### Phase 5: Daily Rhythm Protocol (Week 9-10)
**Goal:** Generate personalized daily schedule

**Tasks:**
1. Combine time windows + OS + current state + energy baselines
2. Generate hour-by-hour schedule
3. Adjust for friction states (e.g., more grounding for Chaos Friction)
4. Create `/protocols/daily-rhythm` endpoint
5. Include energy forecasts per time block

**Deliverables:**
- ✅ Users get full daily rhythm protocol
- ✅ Personalized to their OS + current state

---

### Phase 6: Knowledge Graph Implementation (Week 11-14) 🔴 CRITICAL
**Goal:** Build the Ayurvedic Knowledge Graph for intelligent recommendations

**Priority:** HIGH - This is the reasoning engine that connects everything

**Tasks:**
1. **Populate ay_nodes table:**
   - Add ~200 food nodes with Ayurvedic properties (heavy/light, hot/cold, oily/dry, taste)
   - Add ~50 habit/practice nodes with time-of-day + dosha effects
   - Add ~30 symptom nodes with dosha signatures
   - Add season nodes (6 seasons in Ayurveda)
   - Add time window nodes (Vata/Pitta/Kapha times)

2. **Populate ay_edges table:**
   - Create pacifies/aggravates edges (food → dosha)
   - Create indicates edges (symptom → dosha_imbalance)
   - Create seasonal_risk edges (season → dosha)
   - Create optimal_time edges (activity → time_window)
   - Weight edges by strength (0.0-1.0)

3. **Build reasoning engine:**
   - Graph traversal functions (PostgreSQL queries or graph library)
   - Multi-hop reasoning (user_state → imbalance → balancing_foods → filtered_by_season_and_preferences)
   - Scoring algorithm for recommendation ranking

4. **Create `/recommendations/dosha-balancing` endpoint:**
   - Query graph for foods that pacify current imbalance
   - Query graph for habits that balance dosha
   - Filter by season, time of day, user preferences
   - Structure output: foods, habits, activities, avoid

5. **Testing & validation:**
   - Test recommendations against classical Ayurvedic texts
   - Validate multi-hop reasoning
   - Performance optimization (caching, indexing)

**Deliverables:**
- ✅ Knowledge Graph fully populated with ~300 nodes, ~1000 edges
- ✅ Reasoning engine operational
- ✅ Users get intelligent, context-aware balancing recommendations
- ✅ Graph database actively driving all recommendations (not hardcoded)

---

### Phase 7: Seasonal Adjustments (Week 15-16)
**Goal:** Implement Ritucharya

**Tasks:**
1. Detect current season from date + hemisphere
2. Map season → dominant dosha risk
3. Query graph for seasonal recommendations
4. Create `/recommendations/seasonal-protocol` endpoint
5. Adjust dosha baseline by season

**Deliverables:**
- ✅ Users get seasonal protocol adjustments
- ✅ "Winter is Vata season—here's how to adapt"

---

### Phase 8: Unified Friction Score (Week 17-18)
**Goal:** Create single friction metric

**Tasks:**
1. Combine dosha drift + soul friction + conflicts + residue + coherence
2. Weighted formula for friction score (0-100)
3. Create `/state/friction-score` endpoint
4. Breakdown by source
5. Prioritized reduction actions

**Deliverables:**
- ✅ Users see unified friction score
- ✅ Clear priorities for reduction

---

### Phase 9: Enhanced Coherence (Week 19-20)
**Goal:** Refine coherence calculation

**Tasks:**
1. Update coherence formula to include:
   - Shadow/light balance (40%)
   - Value-goal alignment (30%)
   - Baseline drift (20%)
   - Energy coherence (10%)
2. Update `/soul/summary` endpoint
3. Expose detailed breakdown

**Deliverables:**
- ✅ More sophisticated coherence score
- ✅ Multi-dimensional alignment metric

---

### Phase 10: Dashboard Integration (Week 21-22)
**Goal:** Update frontend to display new framework

**Tasks:**
1. Update user profile to show Operating System
2. Add "Current State" card (Mode + Friction State + Drift)
3. Add "Processing Metrics" section (Capacity, Residue, Reserve)
4. Add "Daily Rhythm" view
5. Add "Recommendations" section (time-based + balancing)
6. Update soul dashboard to show enhanced coherence

**Deliverables:**
- ✅ Full Friction Framework visible in UI
- ✅ Ayurvedic engine fully translated to user-facing language

---

## Summary

### What We Have

**Sakhi has already built ~70% of the Friction Framework:**

✅ **Doshas** computed and stored
✅ **Gunas** computed and stored
✅ **Five elements** tracked across 3 dimensions with temporal aggregation
✅ **Soul state** extracted (values, shadow, light, friction, conflicts)
✅ **Energy layer** with primitives (activation_load, grounding, circulation, recovery)
✅ **Rhythm-soul integration** with coherence and momentum
✅ **Pattern detection** across multiple dimensions
✅ **Inner conflict detection** with 7 sources
✅ **Identity momentum & timeline** tracking
✅ **Alignment scoring**
✅ **Soul analytics APIs** (state, timeline, summary)
⚠️ **Ayurvedic graph database schema** (tables exist but NOT populated/implemented)
✅ **Dosha diagnosis endpoint**
✅ **Personal model with baselines**

### What We Need

❌ **Prakruti (baseline) storage** as explicit Operating System type
❌ **Vikriti (current) comparison** to show baseline drift
❌ **Friction State classification** (Chaos/Intensity/Stagnation)
❌ **Operating Mode mapping** from gunas (Clarity/Activation/Recovery)
❌ **Processing Capacity** unified metric (Agni)
❌ **Cognitive Residue** cumulative tracking (Ama)
❌ **Vitality Reserve** long-term resilience (Ojas)
❌ **Knowledge Graph** implementation (only schema exists - CRITICAL MISSING PIECE)
❌ **Time-of-day windows** (Vata/Pitta/Kapha times)
❌ **Seasonal protocols** (Ritucharya)
❌ **Dosha balancing recommendations** using graph (depends on Knowledge Graph)
❌ **Daily Rhythm Protocol generator**
❌ **Unified Friction Score**
❌ **Enhanced Coherence calculation**

### The Path Forward

**We're not starting from scratch.** The engine is built. We just need to:

1. **Add ~10 new API endpoints** exposing existing computations
2. **Store prakruti explicitly** as Operating System
3. **Classify friction states** from dosha imbalances
4. **Implement time-based recommendations** (already have dosha rules)
5. **🔴 BUILD the Knowledge Graph** - populate nodes/edges, create reasoning engine (CRITICAL - currently only schema exists)
6. **Connect graph database** to recommendation engine
7. **Update frontend** to display Friction Framework terminology

**Timeline:** 21-22 weeks to full implementation (all phases)

**Immediate value (Phase 1-3):** 4-6 weeks to expose Operating System, Friction State, and Current State vs Baseline

**CRITICAL PATH:** Knowledge Graph implementation (Phase 6, Week 11-14) is the reasoning engine that unlocks intelligent recommendations. Without it, recommendations remain hardcoded.

---

## Conclusion

Sakhi's "Friction Framework" is **not a rebranding exercise**—it's a translation layer that makes 5000 years of Ayurvedic wisdom accessible to modern professionals who need preventive wellness but won't engage with traditional Ayurvedic terminology.

**The brilliance of this approach:**

1. **Ancient → Modern:** Ayurveda → Neuroscience/Chronobiology terminology
2. **Complex → Simple:** Doshas → Operating Systems, Gunas → Modes
3. **Diagnostic → Actionable:** Imbalances → Friction States with clear protocols
4. **Mystical → Scientific:** Prana/Ojas → Processing Capacity/Vitality Reserve
5. **Cultural → Universal:** Sanskrit terms → Plain English

**The result:** Users experience the power of Ayurvedic personalization without needing to learn Ayurveda. They just see: "You're an Adaptive OS experiencing Chaos Friction—here's your protocol."

**This is the strategy.** And it's already 70% built.

---

*Document version: 1.0*
*Created: January 2026*
*Authors: Technical analysis by Claude based on Sakhi codebase*
