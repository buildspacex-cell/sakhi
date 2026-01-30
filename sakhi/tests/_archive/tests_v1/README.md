# Archived Tests (v1)

**Archived:** 2026-01-28
**Reason:** Replaced with streamlined v2 test suite

## Archived Files

| File | Original Location | Why Archived |
|------|-------------------|--------------|
| `test_turn_enqueues_only.py` | `tests/` | Replaced by `v2/test_turn_v2.py` |
| `test_turn_harmony_mock_queue.py` | `tests/` | Old harmony flow, superseded |
| `test_turn_personal_model_update.py` | `tests/` | Old worker test, superseded |
| `test_turn_pipeline.py` | `sakhi/tests/workers/` | Replaced by `v2/test_workers.py` |

## New Test Location

All tests are now in: `sakhi/tests/v2/`

```
sakhi/tests/v2/
├── __init__.py
├── conftest.py           # Shared fixtures
├── test_smoke.py         # Quick health checks
├── test_turn_v2.py       # Turn endpoint tests
├── test_workers.py       # Worker tests
└── test_context_loader.py # Context loading tests
```

## Running Tests

```bash
# All v2 tests
pytest sakhi/tests/v2/ -v

# Smoke tests only (quick)
pytest sakhi/tests/v2/test_smoke.py -v

# With database
DATABASE_URL=... pytest sakhi/tests/v2/ -v
```
