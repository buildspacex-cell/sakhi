# Sakhi Onboarding Flow

## Overview

The onboarding flow collects information to compute the user's **Operating System** (constitutional type) and personalize their Sakhi experience. It uses 19 questions across 7 screens to understand energy patterns, stress responses, life context, and decision-making style.

**Key Principle:** These answers describe current tendencies, not identity. They are soft constraints that will be refined by observed behavior over time.

---

## Flow Architecture

```
/experience (Welcome Gate)
    │
    ▼ Click "Begin"
/experience/onboarding (8 Screens)
    │
    ├── Screen 0: Framing (no questions)
    ├── Screen 1: Basics (2 questions) - Required
    ├── Screen 2: Rhythm & Energy (3 questions) - Required
    ├── Screen 3: Body Signals (3 questions) - Required
    ├── Screen 4: Life Context (3 questions) - Required
    ├── Screen 5: Food & Body (3 questions) - Optional
    ├── Screen 6: Decision Making (5 questions) - Required
    └── Screen 7: Closure (no questions)
    │
    ▼ Submit
POST /onboarding/complete → Computes Operating System
    │
    ▼
/experience/record (Voice/Text Input)
```

---

## Screen-by-Screen Breakdown

### Screen 0 — Framing (No Questions)

**Purpose:** Set expectations for the onboarding process.

**Content:**
- Title: "Welcome to Sakhi"
- Subtitle: "Before we begin, a few questions to understand you better."
- Intent: "This helps Sakhi give you relevant, personalized guidance."

---

### Screen 1 — Basics (Required)

**Intent:** Establish life stage and environmental context. Avoid giving inappropriate advice.

| Question ID | Question | Options |
|-------------|----------|---------|
| `age_range` | Your age range: | 18–24, 25–34, 35–44, 45–54, 55–64, 65+ |
| `location` | Where are you based? | Free text (City, Country) |

**Note:** These are context-only — not used for dosha computation. Location informs time zone, climate, and seasonal adjustments.

---

### Screen 2 — Rhythm & Energy (Required)

**Intent:** Understand natural clarity window, pacing tendency, and current energy state.

| Question ID | Question | Options | Dosha Signal |
|-------------|----------|---------|--------------|
| `clarity_window` | When do you usually feel most clear? | Morning, Afternoon, Evening, It varies day to day | Morning=Kapha/Pitta, Evening=Vata, Varies=High Vata |
| `pacing_under_demand` | When days get demanding, you usually: | Push harder, Slow down, Move between both | Push=Pitta, Slow=Kapha, Oscillate=Vata |
| `current_energy` | Right now, your energy feels: | Steady, In waves, Drained, Wired but tired | Steady=Kapha, Waves=Vata, Wired-tired=High Vata |

**Dosha Mapping Logic:**
```python
"clarity_window": {
    "morning": {"vata": 0.2, "pitta": 0.5, "kapha": 0.8},
    "afternoon": {"vata": 0.3, "pitta": 0.8, "kapha": 0.3},
    "evening": {"vata": 0.8, "pitta": 0.3, "kapha": 0.2},
    "varies": {"vata": 1.0, "pitta": 0.2, "kapha": 0.1},
}
```

---

### Screen 3 — Body Signals & Recovery (Required)

**Intent:** Capture concrete stress signals and recovery pathways without diagnosis.

| Question ID | Question | Options | Dosha Signal |
|-------------|----------|---------|--------------|
| `first_stress_signal` | When your days get very busy, what do you notice first? | Trouble settling or sleeping, Irritability or impatience, Low energy or heaviness, It depends | Sleep trouble=Vata, Irritability=Pitta, Low energy=Kapha |
| `body_request` | After a few demanding days, your body usually asks for: | Quiet or mental space, Physical release, Extra rest or comforting food, I'm not sure | Quiet=Vata, Physical=Pitta, Rest/food=Kapha |
| `fastest_recovery` | What helps you recover fastest? | Calm, low-stimulus time, Moving my body, Sleeping or eating well, It varies | Calm=Vata, Movement=Pitta, Sleep/food=Kapha |

**Weight:** These questions have **high weight (1.3-1.4x)** because stress responses are strong constitutional markers.

---

### Screen 4 — Life Context (Required)

**Intent:** Understand constraints, role load, and decision surface.

| Question ID | Question | Options | Purpose |
|-------------|----------|---------|---------|
| `active_roles` | Which roles feel most present right now? | Professional/builder, Caregiver, Partner/family, Personal transition | Multi-select. Context for recommendations. |
| `life_phase` | This phase of life feels like: | Building, Maintaining, Re-orienting, Recovering | Informs pace of recommendations. |
| `responsibility_load` | Your current responsibility load feels: | Mostly personal, Shared, Carrying others | Informs capacity for change. |

**Note:** These are stored in `life_context` for personalization but don't directly affect dosha computation.

---

### Screen 5 — Food & Body Preferences (Optional)

**Intent:** Enable practical, embodied recommendations (food, energy, pacing).

| Question ID | Question | Options | Dosha Signal |
|-------------|----------|---------|--------------|
| `allergies` | Any food allergies or strong intolerances? | Free text or "None" | Stored only |
| `foods_avoided` | Are there foods you usually avoid? | Free text or "None" | Stored only |
| `appetite_pattern` | Which best describes your appetite most days? | Light or variable, Strong and regular, Slow or inconsistent | Light=Vata, Strong=Pitta, Slow=Kapha |

**Weight:** Appetite pattern has **moderate weight (0.8x)** — digestive constitution indicator.

---

### Screen 6 — How You Make Tradeoffs (Required)

**Intent:** Learn how the user actually breaks ties and handles tradeoffs.

| Question ID | Question | Options | Dosha Signal |
|-------------|----------|---------|--------------|
| `decision_driver` | When choosing between two reasonable options, what usually tips the scale first? | Protecting energy/health, People/relationships, Reducing stress/uncertainty, Making progress, It depends | Progress=Pitta, Energy=Kapha, Stress=Vata |
| `risk_behavior` | Over the past few months, you've been more likely to: | Choose safer option, Take calculated risk, Balance both | Safe=Kapha, Risk=Pitta, Balance=mixed |
| `time_horizon` | Right now, most of your decisions are shaped by: | Next few weeks, Next year or two, Longer-term direction | Weeks=Vata, Year=Pitta, Long-term=Kapha |
| `energy_vs_outcome` | When outcomes matter but you're tired, you usually: | Preserve energy, Push through, Case by case | Preserve=Kapha, Push=Pitta, Case-by-case=Vata |
| `flexibility_under_load` | When plans feel heavy or constrained, you tend to: | Simplify and reduce, Reorganize and push through, Pause and reassess | Simplify=Vata/Kapha, Reorganize=Pitta, Pause=Kapha |

**Weight:** Decision questions have **lower weight (0.5-0.8x)** because these are learned behaviors that can change, not constitutional traits.

---

### Screen 7 — Closure (No Questions)

**Purpose:** Set expectations and consent posture.

**Content:**
- Title: "You're all set"
- Subtitle: "Sakhi will learn and adapt as you share more over time."
- Intent: "These answers describe current tendencies, not identity. They are soft constraints and will be updated by observed behavior."

---

## Data Storage

### Table: `personal_model`

All onboarding data is stored in three JSONB columns:

#### 1. `operating_system` Column

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
  "onboarding_responses": {
    "age_range": "35-44",
    "clarity_window": "evening",
    "pacing_under_demand": "oscillate",
    "first_stress_signal": "sleep_trouble",
    ...
  },
  "computed_at": "2026-01-22T10:00:00Z",
  "source": "full_onboarding",
  "is_soft_constraint": true,
  "override_by_observation": true
}
```

#### 2. `life_context` Column

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

#### 3. `decision_profile` Column

```json
{
  "primary_driver": "make_progress",
  "risk_tendency": "calculated_risk",
  "time_horizon": "year_two",
  "energy_tradeoff": "case_by_case",
  "flexibility_style": "reorganize"
}
```

---

## Dosha Computation Algorithm

### Step 1: Answer → Dosha Score Mapping

Each answer maps to a weighted score for each dosha:

```python
answer_weights = {
    "first_stress_signal": {
        "sleep_trouble": {"vata": 1.0, "pitta": 0.3, "kapha": 0.1},
        "irritability": {"vata": 0.2, "pitta": 1.0, "kapha": 0.1},
        "low_energy": {"vata": 0.1, "pitta": 0.2, "kapha": 1.0},
        "depends": {"vata": 0.5, "pitta": 0.5, "kapha": 0.5},
    },
    # ... 11 more questions
}
```

### Step 2: Question Weight Multipliers

Different questions have different importance for constitutional assessment:

```python
question_weights = {
    # High weight - strong constitutional signals
    "first_stress_signal": 1.4,
    "pacing_under_demand": 1.3,
    "body_request": 1.3,
    "clarity_window": 1.2,
    "fastest_recovery": 1.2,

    # Current state - not constitution
    "current_energy": 1.0,

    # Moderate weight - digestive constitution
    "appetite_pattern": 0.8,

    # Lower weight - learned behaviors
    "energy_vs_outcome": 0.8,
    "decision_driver": 0.7,
    "flexibility_under_load": 0.7,
    "risk_behavior": 0.6,
    "time_horizon": 0.5,
}
```

### Step 3: Score Aggregation

```python
for question_id, answer in responses.items():
    weights = answer_weights[question_id][answer]
    multiplier = question_weights[question_id]
    for dosha, weight in weights.items():
        scores[dosha] += weight * multiplier
```

### Step 4: Normalization

```python
total = sum(scores.values())
scores = {k: round(v / total, 2) for k, v in scores.items()}
# Result: {"vata": 0.45, "pitta": 0.35, "kapha": 0.20}
```

### Step 5: Operating System Type Determination

```python
def determine_os_type(dosha_baseline):
    vata, pitta, kapha = dosha_baseline.values()

    # Pure types (one dosha ≥ 50%)
    if vata >= 0.5: return "Adaptive"
    if pitta >= 0.5: return "Performance"
    if kapha >= 0.5: return "Conservation"

    # Dual types (two doshas both ≥ 30%)
    sorted_doshas = sorted(doshas, by=value, descending=True)
    if sorted_doshas[0] >= 0.35 and sorted_doshas[1] >= 0.30:
        return f"{first}-{second}"  # e.g., "Adaptive-Performance"

    return "Balanced"
```

---

## Operating System Types

### Pure Types (3)

| Type | Dosha | User-Facing Description |
|------|-------|------------------------|
| **Adaptive** | Vata ≥ 50% | Quick thinking, creative, variable energy. Needs grounding. |
| **Performance** | Pitta ≥ 50% | Driven, focused, intensity-oriented. Needs cooling. |
| **Conservation** | Kapha ≥ 50% | Steady, grounded, endurance-focused. Needs stimulation. |

### Dual Types (3)

| Type | Doshas | User-Facing Description |
|------|--------|------------------------|
| **Adaptive-Performance** | Vata + Pitta | Creativity meets execution. Fast mind, intense pursuit. |
| **Performance-Conservation** | Pitta + Kapha | Drive meets endurance. Determined with stamina. |
| **Adaptive-Conservation** | Vata + Kapha | Innovation meets stability. Creative but grounded. |

### Balanced (1)

| Type | Doshas | User-Facing Description |
|------|--------|------------------------|
| **Balanced** | Even distribution | Versatile and adaptable. Sensitive to environment. |

---

## API Endpoints

### Submit Onboarding

```
POST /onboarding/complete
```

**Request:**
```json
{
  "person_id": "uuid",
  "responses": {
    "age_range": "35-44",
    "location": "San Francisco, USA",
    "clarity_window": "evening",
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

### Retrieve Operating System

```
GET /profile/operating-system/{person_id}
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

---

## Frontend Implementation

### File Location

```
apps/web/app/experience/onboarding/page.tsx
```

### Key Components

- **Progress bar** at top showing completion %
- **Back/Next navigation** in footer
- **Skip button** for optional screens
- **Multi-select support** for role questions
- **Text input** for location and dietary info

### State Management

```typescript
const [currentScreen, setCurrentScreen] = useState(0);
const [answers, setAnswers] = useState<Record<string, string | string[]>>({});
```

### Submit Logic

```typescript
const handleNext = async () => {
  if (isLastScreen) {
    await fetch("/api/onboarding/complete", {
      method: "POST",
      body: JSON.stringify({
        user_id: userId,
        responses: answers,
        completed_at: new Date().toISOString(),
      }),
    });
    router.push("/experience/record");
  } else {
    setCurrentScreen(prev => prev + 1);
  }
};
```

---

## Guardrails & Philosophy

### 1. Soft Constraints

The onboarding answers are **soft constraints**, not fixed identity labels:

```json
{
  "is_soft_constraint": true,
  "override_by_observation": true
}
```

### 2. Observation Over Self-Report

Over time, Sakhi's observations of actual behavior should refine the initial assessment:

- If someone self-reports as "steady energy" but their entries show variable patterns → adjust toward Vata
- If someone says they "push through" but consistently choose rest → adjust toward Kapha

### 3. No Diagnosis

The system never diagnoses or labels users. It provides:
- Personalized insights based on patterns
- Recommendations that fit their tendencies
- Language that describes tendencies, not identity

---

## Question Summary

### By Screen

| Screen | Questions | Required | Dosha Weight |
|--------|-----------|----------|--------------|
| 0. Framing | 0 | - | - |
| 1. Basics | 2 | Yes | Context only |
| 2. Rhythm & Energy | 3 | Yes | High (1.0-1.3) |
| 3. Body Signals | 3 | Yes | Very High (1.2-1.4) |
| 4. Life Context | 3 | Yes | Context only |
| 5. Food & Body | 3 | No | Moderate (0.8) |
| 6. Decision Making | 5 | Yes | Low (0.5-0.8) |
| 7. Closure | 0 | - | - |

### Totals

- **Required questions:** 14
- **Optional questions:** 3
- **Decision intelligence questions:** 5
- **Total:** 19 questions

### Minimal Path

For a faster onboarding, users can complete only Screens 1-4 + a subset of Screen 6, skipping the optional food questions.

---

## Future Enhancements

### Phase 2 (Post-MVP)

1. **Observation-based refinement** — Update dosha baseline based on actual entries
2. **Seasonal adjustment** — Modify recommendations based on time of year
3. **Re-assessment prompts** — Periodic check-ins to update onboarding data
4. **A/B testing** — Test different question orderings and phrasings

### Phase 3 (Knowledge Graph)

1. **Multi-hop reasoning** — Connect patterns across onboarding + ongoing entries
2. **Personalized protocols** — Generate daily routines based on full profile
3. **Practitioner mode** — Allow practitioners to view/interpret user profiles

---

*Document Version: 1.0*
*Created: January 2026*
