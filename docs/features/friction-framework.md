# Friction Framework API Implementation

## Overview

The Friction Framework API provides endpoints to support the MVP user experience for Sakhi's Ayurveda-based self-awareness system. This document details the implementation of 6 new endpoints that translate Ayurvedic concepts into accessible, user-friendly terminology.

**Implementation Date:** January 2026
**Location:** `sakhi/apps/api/routes/friction_framework.py`

---

## Terminology Translation

The Friction Framework uses modern, accessible terms instead of traditional Ayurvedic terminology:

| Ayurvedic Concept | User-Facing Term | Description |
|-------------------|------------------|-------------|
| Dosha (Vata/Pitta/Kapha) | Operating System | Your constitutional type |
| Prakruti | Baseline/Default | Your natural state |
| Vikriti | Current State | Where you are now |
| Guna (Sattva/Rajas/Tamas) | Operating Mode | How you're running |
| Dosha Imbalance | Friction State | What's creating resistance |

### Operating System Types (7 total)

| Type | Primary | Secondary | Description |
|------|---------|-----------|-------------|
| Adaptive | Vata | - | Quick thinking, creative, variable energy |
| Performance | Pitta | - | Driven, focused, intensity-oriented |
| Conservation | Kapha | - | Steady, grounded, endurance-focused |
| Adaptive-Performance | Vata | Pitta | Creativity meets execution |
| Performance-Conservation | Pitta | Kapha | Drive meets endurance |
| Adaptive-Conservation | Vata | Kapha | Innovation meets stability |
| Balanced | - | - | Even distribution |

### Operating Modes (3 states)

| Mode | Guna | Description |
|------|------|-------------|
| Clarity | Sattva | Clear, balanced, harmonious |
| Activation | Rajas | High energy, dynamic, driven |
| Recovery | Tamas | Low energy, inward, rest-oriented |

### Friction States (3 types)

| Friction State | Elevated Dosha | Symptoms |
|----------------|----------------|----------|
| Chaos Friction | Vata | Scattered energy, anxiety, overcommitment |
| Intensity Friction | Pitta | Burnout, irritability, pushing limits |
| Stagnation Friction | Kapha | Lethargy, resistance to change, heaviness |

---

## Database Schema

### Migration: `0028_friction_framework.sql`

```sql
-- Add operating_system JSONB column to personal_model
ALTER TABLE personal_model
ADD COLUMN IF NOT EXISTS operating_system JSONB DEFAULT NULL;

-- Structure:
-- {
--   "type": "Adaptive-Performance",
--   "primary": "Adaptive",
--   "secondary": "Performance",
--   "dosha_baseline": {"vata": 0.45, "pitta": 0.35, "kapha": 0.20},
--   "assessment_responses": [...],
--   "computed_at": "2026-01-22T10:00:00Z"
-- }

-- Index for querying by OS type
CREATE INDEX IF NOT EXISTS idx_personal_model_operating_system_type
ON personal_model ((operating_system->>'type'));
```

---

## API Endpoints

### 1. POST /onboarding/complete (Full Onboarding - 19 Questions)

**Purpose:** Complete the full onboarding questionnaire and compute Operating System

This is the primary onboarding endpoint that processes all 19 questions across 7 screens.

**Request:**
```json
{
  "person_id": "uuid",
  "responses": {
    "age_range": "35-44",
    "location": "San Francisco, USA",
    "clarity_window": "morning",
    "pacing_under_demand": "oscillate",
    "current_energy": "waves",
    "first_stress_signal": "sleep_trouble",
    "body_request": "quiet_space",
    "fastest_recovery": "calm_time",
    "active_roles": ["professional", "partner_family"],
    "life_phase": "building",
    "responsibility_load": "shared",
    "allergies": "None",
    "foods_avoided": "None",
    "appetite_pattern": "light_variable",
    "decision_driver": "make_progress",
    "risk_behavior": "calculated_risk",
    "time_horizon": "year_two",
    "energy_vs_outcome": "case_by_case",
    "flexibility_under_load": "reorganize"
  },
  "completed_at": "2026-01-22T10:00:00Z"
}
```

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
  "life_context": {
    "age_range": "35-44",
    "location": "San Francisco, USA",
    "active_roles": ["professional", "partner_family"],
    "life_phase": "building",
    "responsibility_load": "shared"
  },
  "decision_profile": {
    "primary_driver": "make_progress",
    "risk_tendency": "calculated_risk",
    "time_horizon": "year_two",
    "energy_tradeoff": "case_by_case",
    "flexibility_style": "reorganize"
  },
  "stored": true
}
```

**Question Categories & Dosha Mapping:**

| Screen | Questions | Primary Signal |
|--------|-----------|----------------|
| Basics | age_range, location | Context only |
| Rhythm & Energy | clarity_window, pacing, current_energy | Constitutional energy patterns |
| Body Signals | first_stress_signal, body_request, fastest_recovery | Strong constitutional markers |
| Life Context | active_roles, life_phase, responsibility_load | Context for recommendations |
| Food & Body | allergies, foods_avoided, appetite_pattern | Digestive constitution |
| Decision Making | 5 questions | Behavioral tendencies |

**Internal Guardrail:**
> These answers describe current tendencies, not identity. They are soft constraints and must be overridden by observed behavior over time.

---

### 1b. POST /onboarding/assessment (Simple - 5 Questions)

**Purpose:** Quick assessment for returning users or simple onboarding

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
  "operating_system": "Adaptive-Performance",
  "primary": "Adaptive",
  "secondary": "Performance",
  "dosha_baseline": {
    "vata": 0.45,
    "pitta": 0.35,
    "kapha": 0.20
  },
  "stored": true
}
```

---

### 2. GET /profile/operating-system/{person_id}

**Purpose:** Retrieve stored Operating System with full details

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
  "description": "You blend creativity with execution...",
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

**Implementation:** Static content lookup by OS type from `OS_TYPE_DEFINITIONS` dictionary.

---

### 3. GET /state/current/{person_id}

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

**Implementation Logic:**

1. **Get Baseline:** Query `personal_model.operating_system`

2. **Compute Current State:** Average `state_vector['dosha']` from last 7 days of observations

3. **Calculate Drift:**
   ```python
   drift = sum(abs(current[d] - baseline[d]) for d in doshas) / 2
   drift_percentage = int(drift * 100)
   ```

4. **Classify Friction State:**
   - If any dosha elevated > 0.25 from baseline → friction state
   - Vata elevated → Chaos Friction
   - Pitta elevated → Intensity Friction
   - Kapha elevated → Stagnation Friction

5. **Determine Operating Mode:**
   - Highest guna score determines mode
   - Sattva → Clarity, Rajas → Activation, Tamas → Recovery

---

### 4. GET /state/friction-state/{person_id}

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

**Implementation:** Subset of `/state/current` logic.

---

### 5. GET /recommendations/now/{person_id}

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

**Implementation (LLM-Powered with Rule Fallback):**

The recommendations endpoint uses a two-tier approach:

**1. Primary: LLM-Generated Recommendations**
- Builds rich context from user's state (OS type, friction, mode, drift %)
- Includes recent patterns from their entries (shadows/lights)
- Uses structured JSON output for consistent parsing
- Generates personalized, dynamic recommendations

**2. Fallback: Rule-Based Recommendations**
- Used when LLM is unavailable or fails
- Static recommendations per friction state:
  - Chaos Friction → grounding, closing loops, breathing
  - Intensity Friction → cooling, rest, delegation
  - Stagnation Friction → movement, stimulation, novelty

**LLM Prompt Structure:**
```
System: Sakhi wellness companion with Ayurvedic context
User Context:
- Operating System: {os_type} (primary: {os_primary})
- Current Mode: {operating_mode}
- Friction State: {friction_state or "balanced"}
- Baseline Drift: {drift}%
- Recent patterns: {patterns from entries}
```

**Why LLM-Powered:**
- **Dynamic:** Recommendations adapt to user's specific context
- **Personalized:** Considers OS type + current state combination
- **Pattern-aware:** Incorporates recent behavioral patterns
- **Natural language:** Feels like talking to a wise friend, not a rule engine

---

### 6. GET /state/weekly/{person_id}

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
  "weekly_insight": "Your Adaptive-Performance system is running hot this week..."
}
```

**Implementation Logic:**

1. Query observations for current week (Monday-Sunday)
2. Compute coherence from existing `/soul/summary` data
3. Aggregate friction states across days
4. Generate insight based on patterns

---

## Code Architecture

### File Structure

```
sakhi/apps/api/routes/friction_framework.py
├── Imports & Router Setup
├── Pydantic Models
│   ├── QuizResponse
│   ├── AssessmentRequest
│   ├── OperatingSystemResult
│   ├── CurrentStateResponse
│   ├── FrictionStateResponse
│   ├── Recommendation
│   ├── RecommendationsResponse
│   └── WeeklyStateResponse
├── Static Data
│   ├── ANSWER_DOSHA_SCORES (quiz answer mappings)
│   ├── OS_TYPE_DEFINITIONS (7 OS types with content)
│   └── FRICTION_STATE_CONFIG (3 friction states with recs)
├── Helper Functions
│   ├── _compute_dosha_from_responses()
│   ├── _determine_os_type()
│   ├── _classify_friction_state()
│   ├── _determine_operating_mode()
│   └── _calculate_baseline_drift()
└── Endpoints (6 routes)
```

### Key Dependencies

- **FastAPI** for routing
- **Pydantic** for request/response validation
- **asyncpg** via `get_async_pool()` for database access
- Existing `observation` table for state_vector data
- Existing `personal_model` table for storing operating_system

---

## Testing the Endpoints

### 1. Submit Assessment
```bash
curl -X POST http://localhost:8000/onboarding/assessment \
  -H "Content-Type: application/json" \
  -d '{
    "person_id": "your-uuid-here",
    "responses": [
      {"question_id": "q1_challenge", "answer": "jump_in_quickly"},
      {"question_id": "q2_energy", "answer": "variable_bursts"},
      {"question_id": "q3_stress", "answer": "scattered_anxious"},
      {"question_id": "q4_environment", "answer": "dynamic_varied"},
      {"question_id": "q5_sleep", "answer": "light_irregular"}
    ]
  }'
```

### 2. Get Operating System Profile
```bash
curl http://localhost:8000/profile/operating-system/your-uuid-here
```

### 3. Get Current State
```bash
curl http://localhost:8000/state/current/your-uuid-here
```

### 4. Get Friction State Only
```bash
curl http://localhost:8000/state/friction-state/your-uuid-here
```

### 5. Get Recommendations
```bash
curl http://localhost:8000/recommendations/now/your-uuid-here
```

### 6. Get Weekly Summary
```bash
curl http://localhost:8000/state/weekly/your-uuid-here
```

---

## Future Enhancements (Post-MVP)

These features are NOT in the current implementation:

1. **Knowledge Graph Integration** - Multi-hop reasoning for recommendations
2. **Seasonal Protocols** - Time-of-year adjustments
3. **Time-of-Day Windows** - Circadian rhythm integration
4. **Ama/Ojas Tracking** - Toxin and vitality metrics
5. **LLM-Generated Recommendations** - Dynamic, personalized suggestions
6. **Historical Trend Analysis** - Long-term pattern detection

---

## Maintenance Notes

### Adding New Quiz Questions

1. Add question_id to the quiz flow
2. Add answer mappings to `ANSWER_DOSHA_SCORES` in `friction_framework.py`
3. Each answer should map to a dosha distribution: `{"vata": x, "pitta": y, "kapha": z}` where x+y+z = 1.0

### Modifying Operating System Descriptions

Update the `OS_TYPE_DEFINITIONS` dictionary with:
- `description`: 1-2 sentence summary
- `strengths`: List of 4 positives
- `vulnerabilities`: List of 4 challenges
- `traits`: List of 4 keywords

### Adjusting Friction Thresholds

The `_classify_friction_state()` function uses 0.25 as the drift threshold. Adjust this value to make friction detection more or less sensitive.

---

*Document Version: 1.0*
*Created: January 2026*
