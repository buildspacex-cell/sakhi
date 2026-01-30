# Body State Design — Ayurvedic Physical Intelligence

> **Principle:** The body speaks before the mind knows. Track physical signals through an Ayurvedic lens to understand the whole person.

---

## Overview

The `body_state` captures the physical/somatic dimension of a person's being, grounded in Ayurvedic and Yogic principles. This completes the vision layer:

```
Soul (purpose) → Breath (rhythm) → Body (physical) → Emotion (feelings)
```

---

## Ayurvedic Body Framework

### The Five Elements (Pancha Mahabhutas)

Every physical signal maps to elemental qualities:

| Element | Qualities | Body Signals |
|---------|-----------|--------------|
| **Akasha** (Space) | Expansive, light, subtle | Joint flexibility, openness, breath capacity |
| **Vayu** (Air) | Mobile, dry, cold, light | Movement, circulation, nervous system |
| **Agni** (Fire) | Hot, sharp, light, spreading | Digestion, metabolism, body temperature |
| **Jala** (Water) | Cool, fluid, soft, smooth | Hydration, lubrication, fluids |
| **Prithvi** (Earth) | Heavy, stable, dense, slow | Weight, bones, muscle mass, grounding |

### Dosha Mapping in Body

Physical imbalances manifest as dosha disturbances:

| Dosha | Balanced Body | Imbalanced Body |
|-------|---------------|-----------------|
| **Vata** | Light, energetic, flexible | Dry skin, cold hands, restless, constipated |
| **Pitta** | Warm, strong digestion, clear skin | Hot, inflamed, acidic, skin eruptions |
| **Kapha** | Strong, stable, good endurance | Heavy, sluggish, congested, water retention |

---

## Body State Schema

```python
body_state = {
    # === CORE VITALS (from health apps) ===
    "vitals": {
        "heart_rate_resting": 62,          # bpm
        "heart_rate_variability": 45,       # ms (higher = more adaptive)
        "blood_oxygen": 98,                 # SpO2 %
        "respiratory_rate": 14,             # breaths/min
        "body_temperature": 36.6,           # celsius
    },

    # === SLEEP (critical for body restoration) ===
    "sleep": {
        "duration_hours": 7.2,
        "quality_score": 0.75,              # 0-1
        "deep_sleep_percent": 18,           # % of total
        "rem_percent": 22,
        "interruptions": 2,
        "sleep_debt_hours": 3.5,            # accumulated deficit
        "consistency_score": 0.6,           # regularity of schedule
    },

    # === ENERGY & ACTIVITY ===
    "energy": {
        "level": 0.65,                      # 0-1 current energy
        "trend": "declining",               # rising, stable, declining
        "peak_hours": [9, 10, 11, 16, 17],  # when energy is highest
        "low_hours": [14, 15, 22, 23],      # when energy dips
    },
    "activity": {
        "steps_today": 6500,
        "active_minutes": 45,
        "standing_hours": 8,
        "exercise_minutes": 30,
        "exercise_type": "yoga",            # last exercise type
        "sedentary_hours": 6,
    },

    # === AYURVEDIC BODY ASSESSMENT ===
    "dosha_body": {
        "vata_signs": {
            "score": 0.4,                   # 0-1 (0=balanced, 1=aggravated)
            "signals": ["cold_hands", "dry_skin", "restless_legs"],
        },
        "pitta_signs": {
            "score": 0.2,
            "signals": [],
        },
        "kapha_signs": {
            "score": 0.3,
            "signals": ["morning_sluggishness"],
        },
        "dominant_imbalance": "vata",       # which dosha is most disturbed
    },

    # === AGNI (Digestive Fire) ===
    "agni": {
        "strength": "variable",             # strong, moderate, variable, weak
        "last_meal_hours_ago": 4,
        "hunger_level": 0.6,                # 0-1
        "digestion_quality": "good",        # good, sluggish, hyperactive, irregular
        "bloating": false,
        "elimination_regular": true,
    },

    # === OJAS (Vital Essence) ===
    "ojas": {
        "level": 0.7,                       # 0-1 (immunity, vitality, glow)
        "indicators": {
            "skin_glow": true,
            "eye_clarity": true,
            "voice_strength": true,
            "endurance": "moderate",
        },
    },

    # === BODY TENSION MAP (Yogic) ===
    "tension_map": {
        "neck_shoulders": 0.6,              # 0-1 tension level
        "upper_back": 0.4,
        "lower_back": 0.3,
        "hips": 0.5,
        "jaw": 0.2,
        "primary_holding": "neck_shoulders", # where tension accumulates
    },

    # === PRANA (Breath/Life Force) ===
    "prana": {
        "breath_quality": "shallow",        # deep, moderate, shallow, irregular
        "breath_location": "chest",         # belly, chest, clavicular
        "nostril_dominance": "right",       # left (ida/cooling), right (pingala/heating), balanced
        "capacity_score": 0.6,              # 0-1 overall prana
    },

    # === HYDRATION & NUTRITION ===
    "hydration": {
        "level": 0.7,                       # 0-1
        "water_intake_ml": 1800,
        "caffeine_intake_mg": 200,
        "alcohol_units": 0,
    },
    "nutrition": {
        "meals_today": 2,
        "last_meal_quality": "balanced",    # heavy, light, balanced, processed
        "cravings": ["sweet", "warm"],      # current cravings (reveal imbalances)
    },

    # === CIRCADIAN & SEASONAL ===
    "circadian": {
        "phase": "afternoon_slump",         # morning_rise, peak, afternoon_slump, evening_wind, night
        "aligned_with_sun": true,           # waking/sleeping with natural light
        "jet_lag_hours": 0,
    },
    "seasonal": {
        "current_ritu": "shishira",         # Ayurvedic season
        "seasonal_adjustment": "warming",    # what body needs this season
    },

    # === COMPUTED SUMMARY ===
    "summary": {
        "overall_score": 0.68,              # 0-1 overall body wellness
        "primary_need": "grounding",        # what body needs most
        "top_recommendations": [
            "warm_oil_massage",
            "earlier_bedtime",
            "reduce_screen_time"
        ],
        "ayurvedic_assessment": "Vata slightly elevated, needs grounding and warmth",
    },

    # === METADATA ===
    "updated_at": "2024-01-28T10:30:00Z",
    "data_sources": ["apple_health", "self_report", "inference"],
    "confidence": 0.75,                     # how complete/reliable the data
}
```

---

## Apple Health Integration

### Available Data Points (HealthKit)

| Category | Metrics | Ayurvedic Mapping |
|----------|---------|-------------------|
| **Activity** | Steps, active energy, exercise time, standing hours | Vata (movement), Kapha (sedentary) |
| **Heart** | Resting HR, HRV, walking HR | Pitta (inflammation), Vata (variability) |
| **Sleep** | Duration, stages, consistency | Ojas (restoration), Vata (irregularity) |
| **Respiratory** | Respiratory rate, SpO2 | Prana, Kapha (congestion) |
| **Nutrition** | Water intake, caffeine, alcohol | Agni, hydration |
| **Mindfulness** | Mindful minutes | Sattva/clarity |
| **Body** | Weight, BMI, body fat % | Kapha (excess), Vata (underweight) |
| **Vitals** | Blood pressure, temperature | Pitta (heat), Vata (cold) |

### HealthKit Permissions Required

```swift
let healthKitTypes: Set<HKSampleType> = [
    // Activity
    HKQuantityType.quantityType(forIdentifier: .stepCount)!,
    HKQuantityType.quantityType(forIdentifier: .activeEnergyBurned)!,
    HKQuantityType.quantityType(forIdentifier: .appleExerciseTime)!,
    HKQuantityType.quantityType(forIdentifier: .appleStandTime)!,

    // Heart
    HKQuantityType.quantityType(forIdentifier: .heartRate)!,
    HKQuantityType.quantityType(forIdentifier: .heartRateVariabilitySDNN)!,
    HKQuantityType.quantityType(forIdentifier: .restingHeartRate)!,

    // Sleep
    HKCategoryType.categoryType(forIdentifier: .sleepAnalysis)!,

    // Respiratory
    HKQuantityType.quantityType(forIdentifier: .respiratoryRate)!,
    HKQuantityType.quantityType(forIdentifier: .oxygenSaturation)!,

    // Nutrition
    HKQuantityType.quantityType(forIdentifier: .dietaryWater)!,
    HKQuantityType.quantityType(forIdentifier: .dietaryCaffeine)!,

    // Mindfulness
    HKCategoryType.categoryType(forIdentifier: .mindfulSession)!,

    // Body
    HKQuantityType.quantityType(forIdentifier: .bodyMass)!,
    HKQuantityType.quantityType(forIdentifier: .bodyTemperature)!,
]
```

---

## Android Health Connect Integration

### Available Data Points

| Category | Metrics | Ayurvedic Mapping |
|----------|---------|-------------------|
| **Activity** | Steps, distance, calories, exercise sessions | Vata/Kapha balance |
| **Sleep** | Sleep sessions, stages | Ojas restoration |
| **Heart** | Heart rate, HRV, resting HR | Dosha balance |
| **Respiratory** | Respiratory rate, SpO2 | Prana |
| **Nutrition** | Hydration, nutrition records | Agni |
| **Body** | Weight, body fat, BMI | Kapha/Vata |

### Health Connect Permissions

```kotlin
val healthPermissions = setOf(
    HealthPermission.getReadPermission(StepsRecord::class),
    HealthPermission.getReadPermission(HeartRateRecord::class),
    HealthPermission.getReadPermission(SleepSessionRecord::class),
    HealthPermission.getReadPermission(RespiratoryRateRecord::class),
    HealthPermission.getReadPermission(OxygenSaturationRecord::class),
    HealthPermission.getReadPermission(HydrationRecord::class),
    HealthPermission.getReadPermission(WeightRecord::class),
    HealthPermission.getReadPermission(ExerciseSessionRecord::class),
)
```

---

## Data Flow

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

---

## Ayurvedic Inference Rules

### Vata Imbalance Detection

```python
vata_signals = {
    # From health data
    "low_hrv": hrv < 30,  # Low adaptability
    "irregular_sleep": sleep_consistency < 0.5,
    "high_variability": hr_std > 15,  # Heart rate jumps around
    "low_body_temp": temp < 36.2,
    "underweight": bmi < 18.5,

    # From self-report
    "cold_extremities": user_reported,
    "dry_skin": user_reported,
    "constipation": user_reported,
    "anxiety": emotion_state.anxiety > 0.6,
    "restless_sleep": deep_sleep_percent < 15,
}
```

### Pitta Imbalance Detection

```python
pitta_signals = {
    # From health data
    "elevated_hr": resting_hr > 80,
    "high_body_temp": temp > 37.2,
    "short_sleep": duration < 6,
    "intense_exercise": exercise_intensity == "high",

    # From self-report
    "acid_reflux": user_reported,
    "skin_inflammation": user_reported,
    "irritability": emotion_state.irritability > 0.6,
    "overheating": user_reported,
}
```

### Kapha Imbalance Detection

```python
kapha_signals = {
    # From health data
    "low_activity": steps < 3000,
    "excess_sleep": duration > 9,
    "low_hr": resting_hr < 55,
    "weight_gain": weight_trend == "increasing",
    "sedentary": sedentary_hours > 10,

    # From self-report
    "morning_sluggishness": user_reported,
    "congestion": user_reported,
    "water_retention": user_reported,
    "lethargy": energy.level < 0.3,
}
```

---

## Translation to Friendly Language

| Internal State | User Sees |
|----------------|-----------|
| vata_elevated: 0.6 | "Your body's been running on overdrive" |
| pitta_elevated: 0.7 | "You're running hot — body's working hard" |
| kapha_elevated: 0.5 | "Body feels heavy, wants to slow down" |
| low_ojas | "You're running on empty" |
| weak_agni | "Digestion's sluggish today" |
| high_tension_shoulders | "Carrying a lot in your shoulders" |
| shallow_breathing | "Breath's up in your chest" |
| sleep_debt: 5 | "Sleep's been short — body's asking for rest" |

---

## Database Schema

```sql
-- Add body_state to personal_model
ALTER TABLE personal_model
ADD COLUMN IF NOT EXISTS body_state JSONB DEFAULT '{}'::jsonb;

-- Health data sync table (raw data from apps)
CREATE TABLE IF NOT EXISTS health_data_sync (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id UUID NOT NULL REFERENCES persons(id),
    source TEXT NOT NULL,  -- 'apple_health', 'android_health', 'self_report'
    data_type TEXT NOT NULL,  -- 'sleep', 'activity', 'heart', etc.
    data JSONB NOT NULL,
    recorded_at TIMESTAMPTZ NOT NULL,
    synced_at TIMESTAMPTZ DEFAULT NOW(),
    processed BOOLEAN DEFAULT FALSE
);

CREATE INDEX idx_health_sync_person ON health_data_sync(person_id);
CREATE INDEX idx_health_sync_unprocessed ON health_data_sync(person_id, processed) WHERE NOT processed;
```

---

## Implementation Priority

1. **Phase 1: Schema & Basic Worker**
   - Add body_state column to personal_model
   - Create health_data_sync table
   - Create body_refresh worker with basic inference

2. **Phase 2: Self-Report Integration**
   - Add body check-in UI in app
   - Capture tension, digestion, energy manually
   - Feed into body_state

3. **Phase 3: Apple Health Integration**
   - React Native HealthKit module
   - Background sync to API
   - Full Ayurvedic mapping

4. **Phase 4: Android Health Connect**
   - Health Connect integration
   - Parity with Apple Health

---

## Summary

The body_state completes the physical dimension:

```
personal_model = {
    "operating_system": {...},      # Core personality (Prakruti)
    "emotion_state": {...},         # Feelings right now
    "soul_state": {...},            # Purpose & meaning
    "rhythm_state": {...},          # Energy patterns
    "body_state": {...},            # Physical/somatic ← NEW
    "longitudinal_state": {...},    # Long-term patterns
    "identity_momentum_state": {...} # Growth trajectory
}
```

The body speaks. Sakhi listens.
