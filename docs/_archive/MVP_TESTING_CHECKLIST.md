# Sakhi MVP Testing Checklist

> **Goal:** Verify all Phase 1-3 components work before shipping

---

## Pre-Flight: Database Migrations

### Step 1: Run Migrations in Supabase SQL Editor

```sql
-- Run 0035_planner_foundation.sql first
-- Then run 0036_pattern_occurrences.sql
```

### Step 2: Verify Tables Exist

```sql
-- Check goals table has new columns
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'goals';

-- Check new tables exist
SELECT table_name FROM information_schema.tables
WHERE table_name IN (
  'goal_history',
  'intent_extractions',
  'goal_suggestions',
  'pattern_occurrences',
  'crystallized_patterns',
  'crystallization_log'
);
```

**Expected:** All 6 tables should exist.

---

## Phase 1: Foundation Tests

### Test 1.1: Goals Table Extended
```sql
-- Verify goals has new columns
SELECT id, person_id, type, priority, due_at, meta, created_at
FROM goals LIMIT 1;
```

### Test 1.2: Pattern Occurrences Table
```sql
-- Should return empty (no data yet)
SELECT COUNT(*) FROM pattern_occurrences;
```

### Test 1.3: Scheduler Imports
```bash
cd /Users/fanantics/Documents/Sakhi
python -c "from sakhi.apps.worker.scheduler import schedule_goal_evolver_weekly, schedule_crystallization_daily; print('Scheduler imports OK')"
```

---

## Phase 2: Ayurvedic Core Tests

### Test 2.1: Prakruti Service
```bash
python -c "
from sakhi.apps.api.services.ayurveda.prakruti import compute_prakruti_from_onboarding, CONSTITUTION_NAMES
print('Constitution names:', CONSTITUTION_NAMES)
print('Prakruti service imports OK')
"
```

### Test 2.2: Vikriti Service
```bash
python -c "
from sakhi.apps.api.services.ayurveda.vikriti import compute_baseline_drift, classify_friction_state, FRICTION_STATES
print('Friction states:', list(FRICTION_STATES.keys()))
print('Vikriti service imports OK')
"
```

### Test 2.3: Friction State API
```bash
# Start the API server first, then test:
curl http://localhost:8000/v1/state/friction/YOUR_USER_ID
```

**Expected Response:**
```json
{
  "status": "ok",
  "operating_system": "Balanced",
  "drift_percentage": 0,
  "friction_state": "balanced",
  "friction_name": "Balanced Flow"
}
```

### Test 2.4: Operating System Compute
```bash
curl -X POST http://localhost:8000/v1/state/operating-system/compute \
  -H "Content-Type: application/json" \
  -d '{
    "person_id": "YOUR_USER_ID",
    "responses": {
      "body_type": "medium_muscular",
      "energy_pattern": "focused_sustained",
      "stress_response": "irritable_intense",
      "sleep_pattern": "moderate_efficient",
      "work_style": "goal_driven"
    }
  }'
```

**Expected:** Returns Prakruti with type like "Performance" or "Performance-Adaptive"

---

## Phase 3: Pattern Crystallization Tests

### Test 3.1: Crystallization Thresholds
```bash
python -c "
from sakhi.apps.api.services.crystallization.thresholds import CRYSTALLIZATION_THRESHOLDS, check_threshold

# Test threshold check
met, conf, reason = check_threshold('concern', 3, 2, 0.6, 10)
print(f'Concern threshold: met={met}, confidence={conf}, reason={reason}')

met, conf, reason = check_threshold('core_value', 2, 1, 0.5, 5)
print(f'Core value (should fail): met={met}, reason={reason}')
"
```

### Test 3.2: Crystallization Engine
```bash
python -c "
from sakhi.apps.api.services.crystallization.engine import crystallize_patterns
print('Crystallization engine imports OK')
"
```

### Test 3.3: Pattern Logging (Integration)
```bash
# This tests the episodic consolidation logging
python -c "
from sakhi.apps.worker.tasks.episodic_consolidation_v21 import log_pattern_occurrences
print('Pattern logging function exists')
"
```

### Test 3.4: Theme Upranking
```bash
python -c "
from sakhi.apps.worker.tasks.theme_inference import run_theme_inference_incremental
print('Theme upranking imports OK')
"
```

---

## Full Integration Test

### Test A: End-to-End Conversation Flow

1. **Start the API server:**
```bash
cd /Users/fanantics/Documents/Sakhi
python -m sakhi.apps.api.main
```

2. **Send a test journal entry:**
```bash
curl -X POST http://localhost:8000/v2/turn \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "YOUR_USER_ID",
    "text": "I felt really scattered today. Had trouble focusing on work. My mind kept racing with anxious thoughts about the deadline.",
    "mode": "journal"
  }'
```

3. **Check pattern occurrences were logged:**
```sql
SELECT * FROM pattern_occurrences
WHERE person_id = 'YOUR_USER_ID'
ORDER BY detected_at DESC
LIMIT 10;
```

### Test B: Manual Crystallization Run

```bash
python -m sakhi.apps.worker.tasks.pattern_crystallization_worker YOUR_USER_ID daily
```

**Expected output:**
```
Crystallization daily complete:
  Patterns checked: X
  Patterns crystallized: X
  Patterns updated: X
  Patterns decayed: X
```

### Test C: Friction State After Activity

After some journal entries:
```bash
curl http://localhost:8000/v1/state/friction/YOUR_USER_ID
```

Should show drift_percentage > 0 if journal content indicates imbalance.

---

## Worker Health Check

### Verify All Scheduler Functions

```bash
python -c "
from sakhi.apps.worker.scheduler import (
    schedule_goal_evolver_weekly,
    schedule_planner_summary_daily,
    schedule_crystallization_daily,
    schedule_crystallization_weekly,
    schedule_crystallization_monthly,
    schedule_theme_uprank_daily,
)
print('All new scheduler functions import OK')
"
```

---

## Ship Checklist

- [ ] Migrations run successfully in Supabase
- [ ] All tables created (6 new tables)
- [ ] API server starts without errors
- [ ] Friction State API responds
- [ ] Pattern occurrences log on journal entry
- [ ] Crystallization worker runs without errors
- [ ] Theme upranking imports successfully

---

## Quick Verification Commands

```bash
# 1. Test all imports at once
python -c "
from sakhi.apps.api.services.ayurveda import prakruti, vikriti
from sakhi.apps.api.services.crystallization import engine, thresholds
from sakhi.apps.worker.tasks.pattern_crystallization_worker import run_daily_crystallization
from sakhi.apps.worker.tasks.theme_inference import run_theme_inference_incremental
from sakhi.apps.api.routes.friction_state import router
print('All MVP imports successful!')
"

# 2. Check API routes registered
python -c "
from sakhi.apps.api.main import app
routes = [r.path for r in app.routes if '/state/' in r.path]
print('Friction routes:', routes)
"
```

---

## Troubleshooting

### Import Errors
- Check Python path includes project root
- Run `pip install -e .` from project root

### Database Errors
- Verify Supabase credentials in `.env`
- Check table exists with correct schema

### API Errors
- Check logs for stack traces
- Verify all dependencies installed
