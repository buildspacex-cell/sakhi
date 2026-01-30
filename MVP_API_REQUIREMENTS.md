# MVP API Requirements
## What's Needed to Connect Prototype to Backend

**Purpose:** Map exactly which API endpoints exist vs. need to be built for the Friction Framework MVP
**Date:** January 2026

---

## Prototype Flow → API Mapping

### Screen-by-Screen Requirements

| Screen | What It Needs | API Status |
|--------|---------------|------------|
| 1. Welcome | None | N/A |
| 2. Intro to Assessment | None | N/A |
| 3-7. Quiz (5 questions) | Store responses, compute OS | ❌ **NEEDS BUILD** |
| 8. Calculating | Trigger computation | ❌ **NEEDS BUILD** |
| 9. OS Reveal | Get Operating System result | ❌ **NEEDS BUILD** |
| 10. OS Deep Dive | Get strengths/vulnerabilities | ❌ **NEEDS BUILD** |
| 11. Conversation Prompt | None | N/A |
| 12. Recording | Audio transcription | ✅ EXISTS (external/Whisper) |
| 13. Processing | Analyze entry, compute state | ⚠️ PARTIAL |
| 14. Today's State | Get mode, friction, drift | ❌ **NEEDS BUILD** |
| 15. Recommendations | Get personalized actions | ⚠️ PARTIAL |
| 16. Weekly View | Get coherence, week data | ⚠️ PARTIAL |

---

## API Gap Analysis

### ❌ MUST BUILD (New Endpoints)

#### 1. `POST /onboarding/assessment`
**Purpose:** Submit quiz answers, compute Operating System (Prakruti)

**Request:**
```json
{
  "person_id": "uuid",
  "responses": [
    {"question_id": "q1_challenge", "answer": "jump_in_quickly"},
    {"question_id": "q2_energy", "answer": "variable_bursts"},
    {"question_id": "q3_stress", "answer": "scattered_anxious"},
    {"question_id": "q4_environment", "answer": "dynamic_varied"},
    {"question_id": "q5_sleep", "answer": "light_irregular"}
  ]
}
```

**Response:**
```json
{
  "operating_system": {
    "primary": "Adaptive",
    "secondary": "Performance",
    "type": "Adaptive-Performance",
    "dosha_baseline": {
      "vata": 0.45,
      "pitta": 0.35,
      "kapha": 0.20
    }
  },
  "stored": true
}
```

**Implementation:**
- Map quiz answers → dosha scores
- Compute dominant + secondary dosha
- Store in `personal_model.operating_system`
- Return computed type

**Effort:** 4-6 hours

---

#### 2. `GET /profile/operating-system/{person_id}`
**Purpose:** Retrieve stored Operating System with details

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
  "description": "You blend creativity with execution. Your mind moves fast, you pursue goals intensely, but you need variety and can burn out without recovery.",
  "strengths": [
    "Quick thinking and innovation",
    "Strong focus when engaged",
    "Adaptable to change",
    "Natural problem solver"
  ],
  "vulnerabilities": [
    "Prone to scattered energy",
    "Risk of burnout from intensity",
    "Difficulty with routine",
    "Can push past limits"
  ],
  "traits": ["Quick thinking", "Innovative", "Driven", "Variable energy"]
}
```

**Implementation:**
- Lookup `personal_model.operating_system`
- Return with static content per OS type
- 7 OS types: Adaptive, Performance, Conservation, Adaptive-Performance, Performance-Conservation, Adaptive-Conservation, Balanced

**Effort:** 2-3 hours

---

#### 3. `GET /state/current/{person_id}`
**Purpose:** Return current state vs baseline (Vikriti vs Prakruti)

**Response:**
```json
{
  "timestamp": "2026-01-22T14:30:00Z",
  "operating_mode": {
    "mode": "Activation",
    "guna_dominant": "rajas",
    "guna_scores": {"sattva": 0.3, "rajas": 0.6, "tamas": 0.1},
    "description": "Running high — energy scattered across many things"
  },
  "friction_state": {
    "state": "Chaos Friction",
    "dosha_elevated": "vata",
    "severity": "moderate",
    "description": "Your Adaptive side is amplified"
  },
  "baseline_drift": {
    "percentage": 32,
    "direction": "elevated",
    "primary_contributor": "vata",
    "description": "Sleep debt + task overload contributing"
  },
  "current_dosha": {
    "vata": 0.65,
    "pitta": 0.25,
    "kapha": 0.10
  }
}
```

**Implementation:**
- Get baseline from `personal_model.operating_system`
- Compute current from last 7 days of entries (existing `state_vector['dosha']`)
- Calculate drift = distance(current, baseline)
- Classify friction state:
  - Vata elevated > 0.3 → "Chaos Friction"
  - Pitta elevated > 0.3 → "Intensity Friction"
  - Kapha elevated > 0.3 → "Stagnation Friction"
- Get operating mode from latest guna scores

**Effort:** 6-8 hours

---

#### 4. `GET /state/friction-state/{person_id}`
**Purpose:** Simple endpoint returning just friction state

**Response:**
```json
{
  "friction_state": "Chaos Friction",
  "friction_color": "#e8c547",
  "dosha_elevated": "vata",
  "severity": "moderate",
  "since": "2026-01-20"
}
```

**Effort:** 2 hours (subset of /state/current)

---

#### 5. `GET /recommendations/now/{person_id}`
**Purpose:** Context-aware recommendations for current state

**Response:**
```json
{
  "timestamp": "2026-01-22T14:30:00Z",
  "friction_state": "Chaos Friction",
  "recommendations": [
    {
      "action": "Close 2-3 open loops before anything new",
      "why": "Reduces mental scatter immediately",
      "category": "immediate",
      "icon": "clock"
    },
    {
      "action": "5 minutes of slow, deep breathing",
      "why": "Activates your recovery system",
      "category": "immediate",
      "icon": "breath"
    },
    {
      "action": "Warm drink, no caffeine",
      "why": "Grounding without more stimulation",
      "category": "immediate",
      "icon": "drink"
    }
  ],
  "pattern_insight": {
    "pattern": "Sleep debt tends to amplify your scattered energy",
    "suggestion": "Tonight, aim for bed 30 min earlier"
  }
}
```

**Implementation (MVP - Rule-based):**
- Lookup friction state
- Return hardcoded recommendations per state:
  - Chaos Friction → grounding, closing loops, breathing
  - Intensity Friction → cooling, rest, delegation
  - Stagnation Friction → movement, stimulation, novelty
- Pattern insight from existing pattern detection

**Effort:** 4-6 hours (rule-based, no graph needed for MVP)

---

#### 6. `GET /state/weekly/{person_id}`
**Purpose:** Weekly summary for home screen

**Response:**
```json
{
  "week_start": "2026-01-20",
  "coherence_score": 64,
  "coherence_trend": "stable",
  "days": [
    {"date": "2026-01-20", "has_entry": true, "dominant_mode": "Activation"},
    {"date": "2026-01-21", "has_entry": true, "dominant_mode": "Clarity"},
    {"date": "2026-01-22", "has_entry": true, "dominant_mode": "Activation"},
    {"date": "2026-01-23", "has_entry": false, "dominant_mode": null},
    {"date": "2026-01-24", "has_entry": false, "dominant_mode": null},
    {"date": "2026-01-25", "has_entry": false, "dominant_mode": null},
    {"date": "2026-01-26", "has_entry": false, "dominant_mode": null}
  ],
  "dominant_friction": {
    "state": "Chaos Friction",
    "days_count": 3,
    "description": "3 of 3 days showing elevated Adaptive energy"
  },
  "weekly_insight": "Your Adaptive-Performance system is running hot this week. The scattered pattern usually resolves with consistent evening wind-down."
}
```

**Implementation:**
- Query entries for current week
- Compute coherence from existing `/soul/summary/{person_id}`
- Aggregate friction states across days
- Generate insight from patterns

**Effort:** 4-6 hours

---

### ⚠️ PARTIAL (Needs Enhancement)

#### 7. `POST /conversation/voice` (Enhance existing)
**Current:** `/journal/v2` or `/conversation/message`

**Enhancement needed:**
- Ensure dosha/guna computation runs on each entry
- Return computed state in response
- Store in observation.state_vector

**Response should include:**
```json
{
  "entry_id": "uuid",
  "transcript": "I've been feeling scattered...",
  "state_computed": {
    "dosha": {"vata": 0.7, "pitta": 0.2, "kapha": 0.1},
    "guna": {"sattva": 0.2, "rajas": 0.7, "tamas": 0.1},
    "mood_valence": -0.3,
    "stress_level": 0.6
  },
  "acknowledgment": "I hear you. Let me understand your state..."
}
```

**Effort:** 2-4 hours (mostly wiring existing computations)

---

#### 8. `GET /soul/summary/{person_id}` (Exists - use as-is)
**Current response includes:**
- `coherence_score` ✅
- `identity_instability_index` ✅
- `top_shadow`, `top_light` ✅

**No changes needed** - use existing endpoint for coherence

---

### ✅ EXISTS (No Changes)

| Endpoint | Used For |
|----------|----------|
| `POST /diagnose` | Backup dosha detection (if needed) |
| `GET /soul/state/{person_id}` | Shadow/light patterns |
| `GET /soul/summary/{person_id}` | Coherence score |
| `GET /rhythm/{person_id}/state` | Rhythm patterns |
| `POST /journal/v2` | Entry submission |
| `GET /memory/{person_id}/weekly` | Weekly summaries |

---

## MVP API Summary

### New Endpoints to Build: 6

| Endpoint | Priority | Effort |
|----------|----------|--------|
| `POST /onboarding/assessment` | P0 | 4-6 hrs |
| `GET /profile/operating-system/{person_id}` | P0 | 2-3 hrs |
| `GET /state/current/{person_id}` | P0 | 6-8 hrs |
| `GET /state/friction-state/{person_id}` | P1 | 2 hrs |
| `GET /recommendations/now/{person_id}` | P0 | 4-6 hrs |
| `GET /state/weekly/{person_id}` | P1 | 4-6 hrs |

### Enhancements: 1

| Endpoint | Change | Effort |
|----------|--------|--------|
| `POST /conversation/voice` | Ensure state_vector computed + returned | 2-4 hrs |

### Total Effort: ~26-37 hours (3-5 dev days)

---

## Schema Changes Needed

### `personal_model` table additions:

```sql
ALTER TABLE personal_model ADD COLUMN IF NOT EXISTS operating_system JSONB DEFAULT NULL;
-- Structure:
-- {
--   "type": "Adaptive-Performance",
--   "primary": "Adaptive",
--   "secondary": "Performance",
--   "dosha_baseline": {"vata": 0.45, "pitta": 0.35, "kapha": 0.20},
--   "computed_at": "2026-01-22T10:00:00Z"
-- }
```

**Effort:** 30 min migration

---

## Implementation Order

### Week 1: Foundation (Days 1-3)
1. Schema migration (operating_system column)
2. `POST /onboarding/assessment` - quiz → OS computation
3. `GET /profile/operating-system/{person_id}` - OS retrieval

### Week 2: State Intelligence (Days 4-6)
4. `GET /state/current/{person_id}` - mode + friction + drift
5. `GET /state/friction-state/{person_id}` - simple friction lookup
6. Enhance journal entry to ensure state_vector computed

### Week 3: Recommendations + Weekly (Days 7-9)
7. `GET /recommendations/now/{person_id}` - rule-based recs
8. `GET /state/weekly/{person_id}` - weekly summary

### Week 4: Integration + Polish (Days 10-12)
9. Wire prototype to all endpoints
10. Test full flow
11. Polish error handling, edge cases

---

## What We're NOT Building for MVP

❌ Full Knowledge Graph (nodes, edges, reasoning)
❌ Multi-hop recommendation logic
❌ Seasonal protocols
❌ Time-of-day windows
❌ Ama/Ojas tracking
❌ Advanced coherence calculation
❌ Daily rhythm protocol generator

**These are Phase 2 (post-validation) features.**

---

## Quick Reference: Prototype → API

| Prototype Element | API Endpoint |
|-------------------|--------------|
| Quiz submission | `POST /onboarding/assessment` |
| OS reveal card | `GET /profile/operating-system/{person_id}` |
| Voice recording | External (Whisper) + `POST /conversation/voice` |
| "Operating Mode" card | `GET /state/current/{person_id}` |
| "Friction State" indicator | `GET /state/current/{person_id}` |
| "Baseline Drift" | `GET /state/current/{person_id}` |
| Recommendations list | `GET /recommendations/now/{person_id}` |
| Coherence bar | `GET /soul/summary/{person_id}` (exists) |
| Week grid | `GET /state/weekly/{person_id}` |
| Weekly insight | `GET /state/weekly/{person_id}` |

---

*Document Version: 1.0*
*Created: January 2026*
