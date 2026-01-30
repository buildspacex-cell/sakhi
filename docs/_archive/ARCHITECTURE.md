# Sakhi Architecture: The Complete Picture

> **A friend who gets you — powered by Ayurvedic wisdom, delivered in everyday language.**

---

## Overview

Sakhi is a **personal intelligence companion** that understands your patterns and helps you find balance. The Ayurvedic science runs deep — but you never see the jargon. Just a friend who really gets you.

### The Three Pillars

1. **Onboarding** → Figures out how you're wired (your baseline)
2. **Conversation** → Talks like a friend, knows your patterns, gives you what helps
3. **Workers** → Continuously learns about you in the background

### The Philosophy

```
The wisdom is Ayurvedic. The language is everyday.

Internal: "Pitta elevated, 32% drift, Intensity Friction"
User sees: "You're running hot. Maybe ease off a bit?"

Internal: "Vata imbalance, recommend grounding practices"
User sees: "You seem scattered. A walk might help."
```

---

## 1. The Intelligence Loop

```
┌─────────────────────────────────────────────────────────────────────┐
│                         USER MESSAGE                                 │
│            "I've been trying to do yoga in the morning"              │
└───────────────────────────────┬─────────────────────────────────────┘
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│  CONTEXT LOADING                                                     │
│  ├─ Who they are: "Driven" (sharp, driven)                          │
│  ├─ Right now: "all over the place" (noticeably off)                │
│  ├─ Energy: "active" (on the go)                                    │
│  ├─ Their life: people, work, concerns                              │
│  ├─ What we know: past conversations, patterns                      │
│  └─ Connections: yoga competes with work for morning time           │
└───────────────────────────────┬─────────────────────────────────────┘
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│  MEMORY GRAPH (cross-entity relationships)                           │
│  ├─ Goals ←→ Activities ←→ Time Slots                               │
│  ├─ Competing: yoga vs work (both want morning)                     │
│  ├─ Supporting: meditation supports sleep goal                      │
│  └─ Patterns: stress → triggers overwork                            │
└───────────────────────────────┬─────────────────────────────────────┘
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│  TRANSLATION LAYER                                                   │
│  Converts all Ayurvedic data → friendly, simple language            │
│  No jargon ever reaches the response                                │
└───────────────────────────────┬─────────────────────────────────────┘
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│  RESPONSE GENERATION                                                 │
│  LLM talks like a friend — warm, direct, real                       │
│  Knows what's competing for attention. Offers real tradeoffs.       │
└───────────────────────────────┬─────────────────────────────────────┘
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│  BACKGROUND WORKERS (learning while you talk)                        │
│  ├─ Memory → what they shared                                       │
│  ├─ Patterns → what keeps coming up                                 │
│  ├─ State → how they're doing right now                             │
│  ├─ Rhythm → their natural energy patterns                          │
│  └─ Graph → update cross-entity relationships                       │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 2. The Translation Layer (NEW)

**The heart of jargon-free responses.**

Located at: `sakhi/apps/api/services/response/translation.py`

### What Gets Translated

| Internal (Never Shown) | User Sees |
|------------------------|-----------|
| Vata-dominant | Quick-moving — creative, loves variety |
| Pitta-dominant | Driven — focused, gets things done |
| Kapha-dominant | Steady — grounded, reliable |
| Chaos Friction | all over the place |
| Intensity Friction | running hot |
| Stagnation Friction | stuck |
| Sattva mode | clear — mind's quiet |
| Rajas mode | active — on the go |
| Tamas mode | low — turned inward |
| 25% drift | a bit off |
| 40% drift | noticeably off |
| Pranayama | breathing |
| Abhyanga | self-massage |

### Operating System Types

| Type | Name | Description |
|------|------|-------------|
| Adaptive-Flow | Quick-moving | "You're the type who gets excited by new ideas and needs variety to feel alive. Your mind moves fast — that's your superpower." |
| Adaptive-Performance | Driven | "You're wired to achieve. Sharp, clear, and you know what you want. That intensity is a gift." |
| Adaptive-Endurance | Steady | "You've got natural stamina — you're the person others lean on. That stability is rare." |

### Friction States

| State | Name | What It Means | What Helps |
|-------|------|---------------|------------|
| chaos | all over the place | Mind's racing, hard to land on anything | Slow it down. Warmth helps. |
| intensity | running hot | Pushing hard, maybe irritated | Cool it down. Less doing, more being. |
| stagnation | stuck | Everything feels heavy | Move. Anything new. |
| balanced | good | In your rhythm | Keep doing what's working. |

---

## 3. The Unified Response Layer

**How Sakhi talks like a friend.**

Located at: `sakhi/apps/api/services/response/synthesizer.py`

### The Prompt Structure

```
You are Sakhi — a friend who really gets this person.

VOICE: Talk like a friend. Not a therapist, not formal. Just real.
- Simple words. Short sentences. Say what matters.
- No Ayurvedic jargon ever.
- Warm but direct. Skip fluff.

───────────────────────────────────────────────────────────────────────
THEM: Driven — sharp, driven
───────────────────────────────────────────────────────────────────────
You're wired to achieve. Sharp, clear, and you know what you want.

Right now: running hot (noticeably off)
You're pushing hard. Maybe getting irritated more easily.

That drive is yours — but right now it's turned up a bit too high.

Watch for: irritable, impatient, overheating
Energy: active — Lots of energy, wanting to do things.

───────────────────────────────────────────────────────────────────────
WHAT COULD HELP
───────────────────────────────────────────────────────────────────────
Cool it down. Less doing, more being. Play, not productivity.

Quick things:
  → 5 min breathing
  → Step outside

Good to eat: Cucumber, Coconut Water, Mint Tea
Try: gentle stretching (10 min)

───────────────────────────────────────────────────────────────────────
RULES
───────────────────────────────────────────────────────────────────────
• Talk like a friend, not a therapist or doctor
• NEVER use Ayurvedic terms
• Keep it short. 30-50 words usually.
• Be warm, direct, real. Skip filler.
```

### Guardrails

```python
JARGON_FREE_GUARDRAILS = [
    "Talk like a friend, not a therapist or doctor. Simple words.",
    "NEVER use Ayurvedic terms (vata, pitta, kapha, dosha, etc.).",
    "Be warm, direct, real. Skip the filler words.",
    "Pick the 1-2 most likely things, don't list options.",
    "Max 2 questions. Make them feel natural, not like an interview.",
    "If we already know something, reference it — don't re-ask.",
    "No diagnosis. You're a friend, not a doctor.",
    "Keep it short. 30-50 words usually. Say what matters.",
]
```

---

## 4. Friction State (Loaded Every Turn)

**Always know where they're at.**

Located at: `sakhi/apps/api/services/turn/deterministic_context_loader.py`

### How It Works

```python
# Every turn, we compute friction state
friction = await load_friction_state(person_id)

# Returns:
{
    "friction_state": "intensity",      # chaos, intensity, stagnation, balanced
    "drift_percentage": 28.0,           # how far from baseline
    "energy_mode": "rajas",             # sattva, rajas, tamas
    "friction_info": {...}              # full details
}
```

### The Computation

```
1. Get baseline (from onboarding)
   → {vata: 0.30, pitta: 0.45, kapha: 0.25}

2. Get current state (from last 7 days of conversations)
   → {vata: 0.25, pitta: 0.58, kapha: 0.17}

3. Calculate drift
   → Pitta elevated by 29%

4. Classify
   → "intensity" (running hot)
```

---

## 5. Knowledge Graph & Recommendations

**Personalized suggestions from Ayurvedic wisdom.**

### Graph Structure

Located at: `sakhi/apps/api/services/ayurveda/graph_reasoning.py`

```
ay_nodes (300+ nodes)
├── 3 doshas (vata, pitta, kapha)
├── 20 qualities (light, heavy, warm, cool, etc.)
├── 6 seasons
├── 6 time windows
├── 100 foods (with rasa, virya, season)
├── 80 practices (with type, intensity, duration)
└── 60 symptoms

ay_edges (1000+ edges)
├── food → PACIFIES → dosha
├── food → AGGRAVATES → dosha
├── practice → PACIFIES → dosha
├── symptom → INDICATES → dosha
├── season → AMPLIFIES → dosha
└── practice → OPTIMAL_TIME → time_window
```

### Recommendation Flow

```
User is "running hot" (intensity/pitta elevated)
        ↓
Query graph: foods that PACIFY pitta
        ↓
Filter by: current season, time of day, dietary preferences
        ↓
Rank by: pacification_strength × context_match
        ↓
Translate to friendly language:
  "Good to eat: Cucumber, Coconut Water, Mint Tea"
```

### API Endpoint

```
GET /recommendations/now/{person_id}

Returns:
{
    "friction_state": "intensity",
    "drift_percentage": 28,
    "recommendations": {
        "immediate_actions": [
            {"action": "5 min breathing", "why": "Calms the nervous system"}
        ],
        "foods_now": [
            {"name": "Cucumber", "score": 0.85}
        ],
        "practices_today": [
            {"name": "gentle stretching", "score": 0.82}
        ]
    }
}
```

---

## 6. Memory Graph (Cross-Entity Relationships)

**Understanding how things in your life connect.**

Located at: `sakhi/apps/api/services/memory_graph/`

### The Problem It Solves

Traditional memory stores facts in isolation. But life is interconnected:
- Your yoga goal competes with your work habit for morning time
- Stress triggers overwork, which triggers more stress
- Meditation supports your sleep goal

The Memory Graph tracks these relationships so Sakhi can make intelligent suggestions.

### Graph Structure

```
memory_nodes (entities)
├── goal: "get better sleep", "exercise more"
├── pattern: "overworks when stressed", "skips meals"
├── activity: "yoga", "meditation", "deep work"
├── time_slot: "morning", "afternoon", "evening", "night"
├── person: "partner", "boss", "mom"
├── theme: "work-life balance", "health"
└── emotion: "anxious", "motivated", "stuck"

memory_edges (relationships)
├── supports: meditation → sleep goal
├── blocks: overwork → exercise goal
├── competes_with: yoga ↔ deep work (both want morning)
├── scheduled_for: yoga → morning time slot
├── enables: exercise → energy
└── crystallized_from: pattern → repeated occurrences
```

### How It's Used in Conversations

```
User: "I've been trying to do yoga in the morning but work keeps getting in the way"
                                    ↓
┌─────────────────────────────────────────────────────────────────────┐
│  1. TOPIC EXTRACTION                                                 │
│     extract_topic_labels_from_text() → ["yoga", "morning", "work"]  │
└─────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────┐
│  2. MEMORY GRAPH QUERY                                               │
│     load_memory_graph_context(["yoga", "morning", "work"])          │
│       → matched_nodes: yoga, morning, work                          │
│       → competing_entities: yoga competes_with work for morning     │
│       → supporting_entities: meditation supports yoga               │
└─────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────┐
│  3. CONTEXT FOR LLM (in prompt)                                      │
│     ───────────────────────────────────────────────────────────────  │
│     CONNECTIONS                                                      │
│     ───────────────────────────────────────────────────────────────  │
│     - Tension: yoga and work both need morning                       │
│     - Connection: meditation supports yoga                           │
└─────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────┐
│  4. INTELLIGENT RESPONSE                                             │
│     "Yeah, that morning time crunch is real. You've got yoga and    │
│      work both fighting for the same slot. What if you tried        │
│      evening yoga instead — or even just 10 minutes before work?"   │
└─────────────────────────────────────────────────────────────────────┘
```

### Node Types

| Type | Purpose | Example |
|------|---------|---------|
| `goal` | User objectives | "sleep better", "exercise daily" |
| `pattern` | Recurring behaviors | "skips lunch when busy" |
| `activity` | Things they do | "yoga", "meditation", "running" |
| `time_slot` | Time windows | "morning", "evening" |
| `person` | People in their life | "partner", "manager" |
| `theme` | Life topics | "work-life balance" |
| `emotion` | Emotional states | "anxious", "motivated" |
| `value` | Core values | "health", "family" |
| `plan` | Planned actions | "start journaling" |
| `insight` | Realizations | "I overwork when anxious" |

### Edge Types

| Relation | Meaning | Example |
|----------|---------|---------|
| `supports` | A helps B | meditation → sleep goal |
| `blocks` | A prevents B | overwork → exercise |
| `competes_with` | A and B want same resource | yoga ↔ work (morning) |
| `enables` | A makes B possible | exercise → energy |
| `scheduled_for` | Activity linked to time | yoga → morning |
| `crystallized_from` | Pattern emerged from occurrences | pattern → entries |
| `influences` | A affects B's state | stress → sleep |

### Database Schema

```sql
memory_nodes
├── id UUID
├── person_id UUID          -- User
├── node_kind TEXT          -- goal, pattern, activity, etc.
├── label TEXT              -- Human-readable name
├── data JSONB              -- Kind-specific metadata
├── weight FLOAT            -- Importance (0-1)
├── created_at TIMESTAMPTZ
├── updated_at TIMESTAMPTZ
└── last_referenced_at      -- For recency ranking

memory_edges
├── id UUID
├── person_id UUID
├── from_node UUID          -- Source node
├── to_node UUID            -- Target node
├── relation TEXT           -- supports, blocks, etc.
├── weight FLOAT            -- Strength (0-1), reinforced over time
├── evidence JSONB          -- Why this edge exists
├── occurrence_count INT    -- How often observed
├── created_at TIMESTAMPTZ
└── updated_at TIMESTAMPTZ
```

### How Graph Gets Populated

1. **From Crystallization** — When patterns are confirmed:
   ```
   Pattern "overworks when stressed" crystallized
     → Create pattern node
     → Create edges to stress (triggers), work (activity)
   ```

2. **From Episodic Consolidation** — When daily summaries are created:
   ```
   Entry mentions "yoga in the morning"
     → Create/update yoga node
     → Create edge yoga → morning time slot
   ```

3. **From Intent Extraction** — When goals are detected:
   ```
   User says "I want to sleep better"
     → Create goal node "better sleep"
     → Link to relevant activities/patterns
   ```

---

## 7. Complete Data Flow

### Message Flow (End-to-End)

```
1. USER: "I can't stop thinking about work, especially in the mornings"
   │
   ▼
2. LOAD FRICTION STATE
   ├─ Baseline: {vata: 0.30, pitta: 0.45, kapha: 0.25}
   ├─ Current: {vata: 0.38, pitta: 0.52, kapha: 0.10}
   ├─ Drift: +16% pitta, +27% vata
   ├─ State: "running hot" (pitta elevated)
   └─ Energy: "active" (rajas)
   │
   ▼
3. LOAD MEMORY GRAPH CONTEXT
   ├─ Topics extracted: ["work", "morning"]
   ├─ Matched nodes: work (activity), morning (time_slot)
   ├─ Competing: work vs meditation (both scheduled for morning)
   └─ Supporting: morning routine supports productivity goal
   │
   ▼
4. TRANSLATION LAYER
   ├─ Operating System: "Driven" → "sharp, driven"
   ├─ Friction: "intensity" → "running hot"
   ├─ Drift: 28% → "noticeably off"
   ├─ Mode: "rajas" → "active — on the go"
   └─ Connections: "work and meditation both want morning"
   │
   ▼
5. LOAD RECOMMENDATIONS (if not balanced)
   ├─ Graph query: PACIFY pitta
   ├─ Filter: winter, evening
   └─ Translate: "Good to eat: warm soup, herbal tea"
   │
   ▼
6. BUILD FRIENDLY PROMPT
   ├─ Who they are (no jargon)
   ├─ Where they're at (no jargon)
   ├─ Connections (what's competing/supporting)
   ├─ What helps (no jargon)
   └─ Rules: talk like a friend
   │
   ▼
7. GENERATE RESPONSE
   LLM: "Yeah, that driven part of you doesn't have an off switch.
         Mornings are tricky — you've got work pulling at you hard.
         Maybe try 5 minutes of quiet before you open the laptop?
         Sometimes that's enough to keep the whole day from running hot."
   │
   ▼
8. QUEUE WORKERS (background)
   ├─ Memory: store what they shared
   ├─ Episodic: update state vectors
   ├─ Patterns: track "work thoughts" theme
   ├─ Rhythm: note morning energy
   └─ Graph: reinforce work → morning edge
```

---

## 8. The Worker Pipeline (Background Intelligence)

**How Sakhi learns continuously about you.**

Located at: `sakhi/apps/worker/pipelines/turn_updates/runner.py`

### 12 Core Workers

Every conversation turn dispatches background jobs via RQ (Redis Queue):

| Worker | Job Type | What It Does | Writes To |
|--------|----------|--------------|-----------|
| **Memory Ingest** | `turn_memory_update` | Stores what you shared | `memory_episodic` |
| **Episodic Consolidation** | `episodic_consolidation_v21` | Daily summaries + pattern detection | `memory_episodic`, `pattern_occurrences` |
| **Ayurvedic Pipeline** | `ayurvedic_pipeline` | Computes dosha state from conversations | `elemental_signal_stm` |
| **Body Refresh** | `body_refresh` | Physical state from health data | `personal_model.body_state` |
| **Rhythm Forecast** | `rhythm_forecast` | Predicts energy patterns | `personal_model.rhythm_state` |
| **Intent Extraction** | `intent_extraction` | Detects goals/tasks from text | `intents` |
| **ESR** | `esr` | Emotion State Refresh | `personal_model.emotion_state` |
| **Soul Refresh** | `soul_refresh` | Updates values/identity | `personal_model.soul_state` |
| **Identity Momentum** | `identity_momentum_deep` | Tracks identity evolution | `personal_model.identity_momentum_state` |
| **Emotion Soul Rhythm** | `emotion_soul_rhythm_deep` | Integrates emotion + soul + rhythm | `personal_model` |
| **Rhythm Soul** | `rhythm_soul_deep` | Deep rhythm-soul patterns | `personal_model` |
| **Longitudinal Update** | `longitudinal_update` | Weekly learning + long-term patterns | `personal_model.longitudinal_state` |

### Worker Execution Flow

```
USER MESSAGE
     │
     ▼
┌─────────────────────────────────────────────────────────────────────┐
│  /v2/turn endpoint (synchronous response)                            │
│  ├─ Load context (friction state, memory graph)                     │
│  ├─ Generate response (LLM)                                         │
│  └─ Return to user immediately                                      │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
                                ▼ (async via RQ)
┌─────────────────────────────────────────────────────────────────────┐
│  BACKGROUND WORKERS (run after response)                             │
│  ├─ turn_memory_update      → memory_episodic                       │
│  ├─ episodic_consolidation  → pattern detection                     │
│  ├─ ayurvedic_pipeline      → dosha state                           │
│  ├─ esr                     → emotion state                         │
│  └─ intent_extraction       → goals/tasks                           │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                ▼ (scheduled daily/weekly)
┌─────────────────────────────────────────────────────────────────────┐
│  SCHEDULED WORKERS                                                   │
│  ├─ rhythm_forecast         → energy predictions (weekly)           │
│  ├─ longitudinal_update     → long-term patterns (weekly)           │
│  ├─ identity_momentum_deep  → identity evolution (weekly)           │
│  └─ pattern_crystallization → confirm patterns (daily/weekly)       │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 9. The Person Memory Map

**Everything Sakhi knows about a person.**

Stored in: `personal_model` table (single row per person)

### Operating System (Who They Are)

```json
{
  "type": "Adaptive-Performance",       // Vata/Pitta/Kapha dominant
  "type_label": "Driven",               // Friendly name
  "dosha_baseline": {                   // Constitutional baseline
    "vata": 0.30,
    "pitta": 0.45,
    "kapha": 0.25
  },
  "life_context": {                     // From onboarding
    "work_type": "creative",
    "relationships": ["partner", "manager"],
    "priorities": ["health", "career"]
  }
}
```

### Emotion State (How They Feel Right Now)

```json
{
  "primary_emotion": "anxious",
  "intensity": 0.65,
  "triggers": ["work deadline"],
  "guna_mode": "rajas",                 // sattva/rajas/tamas
  "updated_at": "2026-01-28T10:30:00Z"
}
```

### Soul State (Who They're Becoming)

```json
{
  "core_values": ["authenticity", "growth"],
  "identity_themes": ["creator", "caregiver"],
  "conflicts": ["work vs family time"],
  "trajectory": "expanding"
}
```

### Rhythm State (Their Energy Patterns)

```json
{
  "chronotype": "morning_person",
  "peak_hours": [9, 10, 11],
  "low_hours": [14, 15],
  "sleep_window": ["22:30", "06:30"],
  "weekly_pattern": {
    "mon": "high",
    "fri": "low"
  }
}
```

### Longitudinal State (Long-Term Patterns)

```json
{
  "recurring_themes": ["overwork", "health goals"],
  "growth_areas": ["boundaries", "rest"],
  "trajectory_30d": "improving",
  "key_insights": ["stress → overwork cycle"]
}
```

### Identity Momentum State (How They're Evolving)

```json
{
  "momentum_direction": "growth",
  "active_transitions": ["career shift"],
  "stability_score": 0.72,
  "key_moments": ["started meditation habit"]
}
```

### Body State (Physical/Somatic Intelligence) — NEW

**Grounded in Ayurveda and Yoga. Integrates with Apple Health and Android Health Connect.**

Located at: `sakhi/apps/api/services/body/`

```json
{
  // Core vitals (from health apps)
  "vitals": {
    "heart_rate_resting": 62,
    "heart_rate_variability": 45,
    "blood_oxygen": 98,
    "respiratory_rate": 14
  },

  // Sleep (critical for restoration)
  "sleep": {
    "duration_hours": 7.2,
    "quality_score": 0.75,
    "deep_sleep_percent": 18,
    "sleep_debt_hours": 3.5,
    "consistency_score": 0.6
  },

  // Energy & Activity
  "energy": {
    "level": 0.65,
    "trend": "declining",
    "peak_hours": [9, 10, 11, 16, 17]
  },
  "activity": {
    "steps_today": 6500,
    "active_minutes": 45,
    "sedentary_hours": 6
  },

  // Ayurvedic Body Assessment
  "dosha_body": {
    "vata_signs": {
      "score": 0.4,
      "signals": ["cold_hands", "dry_skin", "restless_legs"]
    },
    "pitta_signs": {"score": 0.2, "signals": []},
    "kapha_signs": {"score": 0.3, "signals": ["morning_sluggishness"]},
    "dominant_imbalance": "vata"
  },

  // Agni (Digestive Fire)
  "agni": {
    "strength": "variable",
    "hunger_level": 0.6,
    "digestion_quality": "good"
  },

  // Ojas (Vital Essence / Immunity)
  "ojas": {
    "level": 0.7,
    "indicators": {"well_rested": true, "immunity_strong": true}
  },

  // Tension Map (Yogic)
  "tension_map": {
    "neck_shoulders": 0.6,
    "back": 0.4,
    "jaw": 0.2,
    "primary_holding": "neck_shoulders"
  },

  // Prana (Breath/Life Force)
  "prana": {
    "breath_quality": "shallow",
    "breath_location": "chest",
    "capacity_score": 0.6
  },

  // Summary
  "summary": {
    "overall_score": 0.68,
    "primary_need": "grounding",
    "top_recommendations": ["warm_oil_massage", "earlier_bedtime"]
  }
}
```

### Translation to Friendly Language

| Internal Body State | User Sees |
|---------------------|-----------|
| vata_elevated: 0.6 | "Your body's been running on overdrive" |
| pitta_elevated: 0.7 | "You're running hot — body's working hard" |
| kapha_elevated: 0.5 | "Body feels heavy, wants to slow down" |
| low_ojas | "You're running on empty" |
| weak_agni | "Digestion's sluggish today" |
| high_tension_shoulders | "Carrying a lot in your shoulders" |
| shallow_breathing | "Breath's up in your chest" |
| sleep_debt: 5 | "Sleep's been short — body's asking for rest" |

### Health Data Integration

```
┌─────────────────────────────────────────────────────────────────┐
│  Mobile App (React Native / Expo)                                │
│  ├─ Apple HealthKit SDK                                          │
│  ├─ Android Health Connect SDK                                   │
│  └─ Self-report inputs (tension, cravings, digestion)           │
└───────────────────────────┬─────────────────────────────────────┘
                            │ POST /api/health/sync
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│  Health Data API                                                 │
│  └─ Stores raw data in health_data_sync table                   │
└───────────────────────────┬─────────────────────────────────────┘
                            │ Triggers worker
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│  body_refresh_worker                                             │
│  ├─ Aggregates health data                                       │
│  ├─ Applies Ayurvedic mappings                                   │
│  ├─ Computes dosha imbalances                                    │
│  ├─ Generates recommendations                                    │
│  └─ Updates personal_model.body_state                           │
└─────────────────────────────────────────────────────────────────┘
```

### API Endpoints

```
POST /health/sync/{person_id}
  - Sync health data from mobile app

POST /health/self-report/{person_id}
  - Submit self-reported body sensations

GET /health/body-state/{person_id}
  - Get current body state

GET /health/recommendations/{person_id}
  - Get body-specific recommendations
```

---

## 10. Key Files Reference

### Translation & Response

| File | Purpose |
|------|---------|
| `services/response/translation.py` | All jargon-free translations (including body state) |
| `services/response/synthesizer.py` | Builds friendly prompts, includes CONNECTIONS section |
| `services/response/pipeline.py` | Orchestrates response generation |

### Body State (Physical Intelligence)

| File | Purpose |
|------|---------|
| `services/body/state_engine.py` | Computes body_state from health data |
| `services/body/dosha_inference.py` | Detects Vata/Pitta/Kapha imbalances in body |
| `services/body/health_aggregator.py` | Processes raw health app data |
| `routes/health.py` | Health sync + body state API |
| `worker/tasks/body_refresh.py` | Updates body_state from health data |
| `infra/scripts/migrations/0040_body_state.sql` | Schema for body intelligence |

### Memory Graph

| File | Purpose |
|------|---------|
| `services/memory_graph/graph.py` | Core graph operations, `get_context_for_topic()` |
| `services/memory_graph/wiring.py` | Wire patterns/entries to graph nodes/edges |
| `services/turn/deterministic_context_loader.py` | `load_memory_graph_context()`, `extract_topic_labels_from_text()` |
| `infra/scripts/migrations/0037_memory_graph.sql` | Schema + helper functions |

### Friction & Recommendations

| File | Purpose |
|------|---------|
| `services/turn/deterministic_context_loader.py` | Loads friction state every turn |
| `services/ayurveda/vikriti.py` | Computes current state + drift |
| `services/ayurveda/prakruti.py` | Constitutional baseline |
| `services/ayurveda/graph_reasoning.py` | Ayurvedic knowledge graph queries |
| `routes/recommendations.py` | Recommendations API |

### Planning & Goals

| File | Purpose |
|------|---------|
| `services/planner/goal_suggester.py` | Suggests goals from intents |
| `services/planner/rhythm_scheduler.py` | Schedules tasks by energy |
| `worker/tasks/intent_extraction_worker.py` | Extracts intents from conversations |
| `worker/tasks/goal_evolver.py` | Evolves goals over time |

### Workers

| File | Purpose |
|------|---------|
| `worker/pipelines/turn_updates/runner.py` | Dispatches per-turn jobs (11 core workers) |
| `worker/tasks/episodic_consolidation_v21.py` | Creates episodes + wires to graph |
| `worker/tasks/pattern_crystallization_worker.py` | Confirms patterns, wires to graph |
| `worker/tasks/ayurvedic_pipeline.py` | Computes dosha state |
| `worker/tasks/esr_worker.py` | Emotion state refresh |
| `worker/tasks/soul_refresh_worker.py` | Soul state updates |
| `worker/tasks/body_refresh.py` | Physical state from health data |
| `worker/identity_momentum_deep.py` | Identity evolution tracking |
| `worker/rhythm_soul_deep.py` | Rhythm-soul integration |

---

## 11. Database Schema (Essential Tables Only)

**After cleanup (Jan 2026), these are the core tables for personal intelligence:**

### Central Intelligence (Single Source of Truth)

```sql
personal_model
├── person_id UUID (PK)
├── operating_system JSONB        -- Who they are: {type, dosha_baseline, life_context}
├── emotion_state JSONB           -- How they feel: {primary, intensity, triggers}
├── soul_state JSONB              -- Who they're becoming: {values, themes, conflicts}
├── rhythm_state JSONB            -- Energy patterns: {chronotype, peaks, lows}
├── body_state JSONB              -- Physical state: {vitals, sleep, dosha_body, agni, ojas} ← NEW
├── longitudinal_state JSONB      -- Long-term: {recurring_themes, trajectory}
├── identity_momentum_state JSONB -- Evolution: {direction, transitions}
├── created_at TIMESTAMPTZ
└── updated_at TIMESTAMPTZ
```

### Health Data (Body Intelligence)

```sql
health_data_sync              -- Raw data from health apps
├── id UUID (PK)
├── person_id UUID (FK)
├── source TEXT               -- apple_health, android_health, wearable
├── data_type TEXT            -- sleep, activity, heart, respiratory
├── data JSONB                -- The health data payload
├── recorded_at TIMESTAMPTZ   -- When measurement was taken
├── synced_at TIMESTAMPTZ     -- When we received it
├── processed BOOLEAN         -- Has worker processed it?
└── processed_at TIMESTAMPTZ

body_state_history            -- Snapshots for longitudinal tracking
├── id UUID (PK)
├── person_id UUID (FK)
├── body_state JSONB          -- Full state snapshot
├── overall_score FLOAT       -- Quick lookup
├── vata_score FLOAT
├── pitta_score FLOAT
├── kapha_score FLOAT
├── ojas_level FLOAT
├── sleep_quality FLOAT
├── energy_level FLOAT
└── computed_at TIMESTAMPTZ

self_report_body              -- User check-ins
├── id UUID (PK)
├── person_id UUID (FK)
├── energy_level FLOAT
├── fatigue_level FLOAT
├── tension_neck_shoulders FLOAT
├── tension_back FLOAT
├── digestion_quality TEXT
├── breath_quality TEXT
├── cravings TEXT[]
└── recorded_at TIMESTAMPTZ
```

### Memory & Conversations

```sql
memory_episodic                -- Daily consolidated memories
├── user_id UUID (FK)
├── content TEXT               -- Day summary
├── state_vector JSONB         -- {dosha: {vata, pitta, kapha}}
├── guna_vector JSONB          -- {sattva, rajas, tamas}
├── themes TEXT[]              -- Detected themes
└── created_at TIMESTAMPTZ

journal_entries                -- Raw conversation turns
├── id UUID (PK)
├── user_id UUID (FK)
├── content TEXT
├── facets_v2 JSONB           -- Classification metadata
└── created_at TIMESTAMPTZ
```

### Pattern Detection

```sql
pattern_occurrences           -- Individual pattern sightings
├── person_id UUID (FK)
├── pattern_key TEXT          -- e.g., "overwork_when_stressed"
├── evidence JSONB            -- What triggered detection
├── source_entry_id UUID
└── created_at TIMESTAMPTZ

crystallized_patterns         -- Confirmed patterns (5+ occurrences)
├── person_id UUID (FK)
├── pattern_key TEXT
├── occurrence_count INT
├── first_seen TIMESTAMPTZ
├── last_seen TIMESTAMPTZ
├── confidence FLOAT          -- 0-1, increases with occurrences
└── status TEXT               -- emerging, crystallized, archived
```

### Memory Graph (Cross-Entity Relationships)

```sql
memory_nodes                  -- Entities in your life
├── id UUID (PK)
├── person_id UUID (FK)
├── node_kind TEXT            -- goal, pattern, activity, time_slot, person, theme
├── label TEXT                -- Human-readable name
├── data JSONB                -- Kind-specific metadata
├── weight FLOAT              -- Importance (0-1)
└── last_referenced_at TIMESTAMPTZ

memory_edges                  -- How entities connect
├── id UUID (PK)
├── person_id UUID (FK)
├── from_node UUID (FK)
├── to_node UUID (FK)
├── relation TEXT             -- supports, blocks, competes_with, enables
├── weight FLOAT              -- Strength (0-1)
├── evidence JSONB            -- Why this edge exists
└── occurrence_count INT      -- How often observed
```

### Planning System

```sql
intents                       -- Extracted from conversations
├── id SERIAL (PK)
├── person_id UUID (FK)
├── intent_type TEXT          -- goal, activity, habit, decision
├── summary TEXT
├── confidence FLOAT
└── created_at TIMESTAMPTZ

goals                         -- Promoted from intents
├── id UUID (PK)
├── person_id UUID (FK)
├── title TEXT
├── status TEXT               -- active, completed, paused
├── target_date DATE
└── created_at TIMESTAMPTZ
```

### Ayurvedic Knowledge Graph (Static Reference Data)

```sql
ay_nodes                      -- 300+ Ayurvedic concepts
├── id SERIAL (PK)
├── kind TEXT                 -- dosha, food, practice, symptom, quality
├── name TEXT
└── attrs JSONB               -- {rasa, virya, season, intensity, etc.}

ay_edges                      -- 1000+ relationships
├── src INT (FK ay_nodes)
├── dst INT (FK ay_nodes)
├── rel TEXT                  -- PACIFIES, AGGRAVATES, INDICATES, OPTIMAL_TIME
└── weight FLOAT
```

### Short-Term Memory

```sql
elemental_signal_stm          -- Recent ayurvedic signals (sliding window)
├── person_id UUID (FK)
├── signal_type TEXT
├── dosha_vector JSONB
├── guna_vector JSONB
├── created_at TIMESTAMPTZ
└── expires_at TIMESTAMPTZ    -- TTL for automatic cleanup
```

---

## 12. Implementation Status

| Phase | Status | What It Does |
|-------|--------|--------------|
| **1. Foundation** | ✅ Done | Goals tables, pattern tracking |
| **2. Ayurvedic Core** | ✅ Done | Prakruti/Vikriti, drift detection |
| **3. Crystallization** | ✅ Done | Pattern confirmation over time |
| **4. Planning** | ✅ Done | Intent extraction, rhythm scheduling |
| **5. Knowledge Graph** | ✅ Done | 300+ nodes, Ayurvedic graph reasoning |
| **6. Translation Layer** | ✅ Done | Jargon-free responses |
| **7. Memory Graph** | ✅ Done | Cross-entity relationships |
| **8. Worker Cleanup** | ✅ Done | 11 core workers, removed 6 redundant |
| **9. DB Cleanup** | ✅ Done | Dropped unused tables, documented legacy |

---

## 13. Legacy Tables (Future Cleanup)

These tables still have code references but are candidates for migration to `personal_model`:

| Table | Used By | Migration Path |
|-------|---------|----------------|
| `aw_*` (aw_event, aw_edge, aw_redaction) | awareness router | Migrate to memory_episodic |
| `body_metrics`, `breath_sessions` | breath router | Migrate to personal_model.rhythm_state |
| `dialog_states` | core/dialog_state.py | Migrate to conversation_state |
| `context_recalls` | conversation_v2 | Migrate to memory_graph |
| `emotional_tones` | sync_analytics_cache | Already in personal_model.emotion_state |
| `episodes` | soul router | Already replaced by memory_episodic |
| `environment_context` | environment router | Migrate to personal_model.life_context |
| `identity_signatures`, `life_arcs`, `conflict_records` | soul router | Migrate to personal_model.soul_state |

**Note:** These tables remain functional but represent technical debt. New features should use `personal_model` and `memory_graph` only.

---

## 14. The Tone

**What Sakhi sounds like:**

```
User: "I've been so anxious lately"

❌ Wrong (clinical):
"Based on your Vata elevation of 35% and current friction state,
I recommend grounding practices to pacify the nervous system."

✅ Right (friend):
"Yeah, I can feel that. When you're scattered like this,
everything feels harder than it should. Have you eaten today?
Sometimes that's all it is."
```

**Key principles:**

- Simple words. Short sentences.
- Warm but direct. Skip fluff.
- Talk like a friend who gets it.
- Never list options. Just say what helps.
- Reference what we know. Don't interview.

---

## 15. Summary

**Sakhi is a personal intelligence companion that truly understands you.**

### How Personal Intelligence Works

```
┌─────────────────────────────────────────────────────────────────────┐
│  CONVERSATION                                                        │
│  You talk to Sakhi like a friend                                    │
└───────────────────────────────────────┬─────────────────────────────┘
                                        ▼
┌─────────────────────────────────────────────────────────────────────┐
│  MEMORY LOADING (per-turn, ~50ms)                                    │
│  ├─ Operating System: who you are (baseline, wiring)                │
│  ├─ Current State: how you're doing right now (friction, energy)    │
│  ├─ Memory Graph: your life (goals, patterns, people, conflicts)    │
│  └─ Recommendations: what helps (from Ayurvedic knowledge graph)    │
└───────────────────────────────────────┬─────────────────────────────┘
                                        ▼
┌─────────────────────────────────────────────────────────────────────┐
│  RESPONSE (friend-like, jargon-free)                                 │
│  Translated from Ayurvedic → everyday language                      │
└───────────────────────────────────────┬─────────────────────────────┘
                                        ▼
┌─────────────────────────────────────────────────────────────────────┐
│  BACKGROUND WORKERS (11 core workers, async)                         │
│  ├─ Memory: store what you shared                                   │
│  ├─ Patterns: detect what keeps coming up                           │
│  ├─ State: update emotion/rhythm/soul                               │
│  └─ Learning: long-term patterns + identity evolution               │
└─────────────────────────────────────────────────────────────────────┘
```

### The Core Tables (After Cleanup)

| Table | What It Stores |
|-------|----------------|
| `personal_model` | Central truth: operating_system, emotion_state, soul_state, rhythm_state |
| `memory_episodic` | Daily consolidated memories with state vectors |
| `journal_entries` | Raw conversation turns |
| `pattern_occurrences` + `crystallized_patterns` | Pattern detection → confirmation |
| `memory_nodes` + `memory_edges` | Cross-entity knowledge graph |
| `intents` + `goals` | Planning system |
| `ay_nodes` + `ay_edges` | Ayurvedic knowledge (static reference data) |

### The Intelligence Runs Deep

- Constitutional baselines (who you are)
- Current state detection (where you're at)
- Ayurvedic knowledge graph (what helps)
- Pattern crystallization (what keeps coming up)
- Memory graph (how things in your life compete and support each other)

But you never see the complexity. Just a friend who really gets you.

```
Internal: "Pitta-dominant, 32% drift, Intensity Friction,
           yoga competes_with work for morning,
           meditation supports sleep goal,
           recommend cooling practices,
           11 workers updating state in background"

User sees: "You're running hot. And I notice you've got yoga and work
            both fighting for morning time. What if you tried evening yoga
            — or even just 10 minutes before work starts?"
```

That's Sakhi.
