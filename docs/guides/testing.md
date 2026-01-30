# Testing Guide

This document covers how to test the Sakhi system at different levels.

---

## Quick Reference

| What | Command | Location |
|------|---------|----------|
| Backend unit tests | `pytest tests/` | `sakhi/` |
| Frontend type check | `pnpm tsc --noEmit` | `apps/web/` |
| API integration | `curl` commands below | Any |
| Lab UI | `http://localhost:3000/experience/lab` | Browser |

---

## Demo User

All examples use the demo user:
```
User ID: 565bdb63-124b-4692-a039-846fddceff90
Name: Vidhya
```

---

## 1. Backend Tests

### Run All Tests
```bash
cd sakhi
pytest tests/
```

### Run Specific Test File
```bash
pytest tests/test_friction_framework.py -v
```

### Run with Coverage
```bash
pytest tests/ --cov=apps --cov-report=html
```

### Test Locations
```
sakhi/tests/
├── test_friction_framework.py   # Friction Framework tests
├── test_body_state.py           # Body state tests
├── test_turn_v2.py              # Turn API tests
└── ...
```

---

## 2. Frontend Type Checking

```bash
cd apps/web
pnpm tsc --noEmit
```

This catches TypeScript errors without building.

---

## 3. API Testing

### Test a Conversation Turn

```bash
curl -X POST "http://localhost:8000/v2/turn?user=565bdb63-124b-4692-a039-846fddceff90" \
  -H "Content-Type: application/json" \
  -d '{"text": "I have been feeling anxious lately", "source": "text"}'
```

**Response includes:**
- `reply` — Sakhi's response
- `entry_id` — Journal entry UUID
- `queued_jobs` — Workers triggered
- `context` — Context used for response

### Test Conversation History

```bash
curl "http://localhost:8000/v2/conversation/history?user=565bdb63-124b-4692-a039-846fddceff90&limit=10"
```

### Test Body State

```bash
curl "http://localhost:8000/health/body-state/565bdb63-124b-4692-a039-846fddceff90"
```

### Test Friction State

```bash
curl "http://localhost:8000/friction-framework/state/565bdb63-124b-4692-a039-846fddceff90"
```

---

## 4. Lab Endpoints

The Lab provides debug/testing endpoints for internal state inspection.

### View Memory Details
All deterministic intelligence for a user:
```bash
curl "http://localhost:8000/lab/memory-details?person_id=565bdb63-124b-4692-a039-846fddceff90"
```

**Returns:**
- Friction Framework (operating_system, life_context, decision_profile)
- State vectors (dosha, guna)
- All cache tables (daily, morning, micro, scaffolds)
- Continuity state

### Test Individual Workers
```bash
curl -X POST "http://localhost:8000/lab/run-worker" \
  -H "Content-Type: application/json" \
  -d '{
    "person_id": "565bdb63-124b-4692-a039-846fddceff90",
    "worker": "esr"
  }'
```

**Available workers:**
- `esr` — Emotion State Refresh
- `soul-refresh` — Soul state
- `rhythm-forecast` — Rhythm state
- `identity-momentum-deep` — Identity momentum
- `rhythm-soul-deep` — Rhythm-soul sync
- `episodic-consolidation-v21` — Episodic memory
- `ayurvedic-pipeline` — Full Ayurvedic pipeline

### Live Turn (Debug Mode)
```bash
curl "http://localhost:8000/lab/live-turn?person_id=565bdb63-124b-4692-a039-846fddceff90&message=How%20am%20I%20doing"
```

Returns full debug output including context used.

---

## 5. Lab UI

Access the Lab UI at: `http://localhost:3000/experience/lab`

### Panels Available:
1. **Memory Details** — View all stored intelligence
2. **Live Turn** — Test conversations with debug output
3. **Worker Execution** — Run individual workers
4. **Reflection History** — View past reflections

---

## 6. Voice Testing

### Test TTS Endpoint
```bash
curl -X POST "http://localhost:3000/api/voice/tts" \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello, how are you today?", "voice": "default"}'
```

### Voice Turn (requires audio file)
The `/api/voice/turn` endpoint expects multipart form data with an audio file.

---

## 7. Worker Queue Testing

### Check Queue Status
```bash
redis-cli -u $REDIS_URL
> LLEN turn_updates
> LLEN reflection
```

### Run Scheduler Manually
```bash
cd sakhi
python -m apps.worker.scheduler
```

### Run Workers Inline (Dev Mode)
Set `SAKHI_DISABLE_QUEUE=1` to run workers synchronously instead of queuing.

---

## 8. Database Testing

### Check Recent Entries
```sql
SELECT id, content, created_at
FROM journal_entries
WHERE user_id = '565bdb63-124b-4692-a039-846fddceff90'
ORDER BY created_at DESC
LIMIT 5;
```

### Check Personal Model
```sql
SELECT person_id,
       operating_system->'type' as os_type,
       short_term->'friction_state' as friction,
       updated_at
FROM personal_model
WHERE person_id = '565bdb63-124b-4692-a039-846fddceff90';
```

### Check Recent Turns
```sql
SELECT role, text, source, created_at
FROM conversation_turns
WHERE user_id = '565bdb63-124b-4692-a039-846fddceff90'
ORDER BY created_at DESC
LIMIT 10;
```

---

## 9. Common Issues

### Workers Not Running
1. Check Redis is running: `redis-cli ping`
2. Check queue has jobs: `redis-cli LLEN turn_updates`
3. Check worker process: `ps aux | grep worker`

### Context Not Loading
1. Check personal_model exists for user
2. Run initial onboarding if needed
3. Check deterministic_context_loader logs

### Voice Not Working
1. Check `OPENAI_API_KEY` is set
2. Check browser microphone permissions
3. Check console for errors

---

## 10. Test Data Setup

### Create Test User
```sql
INSERT INTO profiles (user_id, full_name, created_at)
VALUES ('your-uuid-here', 'Test User', NOW());

INSERT INTO personal_model (person_id, operating_system, created_at)
VALUES ('your-uuid-here', '{"type": "Adaptive"}', NOW());
```

### Reset User State
```sql
UPDATE personal_model
SET short_term = '{}', updated_at = NOW()
WHERE person_id = '565bdb63-124b-4692-a039-846fddceff90';
```

---

## Related Documents

- [System Overview](../architecture/system-overview.md) — API reference
- [Conversation Flow](../architecture/conversation-flow.md) — Turn processing details
- [Workers](../architecture/workers.md) — Complete worker inventory
