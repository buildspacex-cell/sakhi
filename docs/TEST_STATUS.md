# Test Status Tracking

> Last Updated: 2026-02-05
>
> Run `make test-coverage` to regenerate this report.

---

## Coverage Summary

| Category | Total | Tested | Coverage |
|----------|-------|--------|----------|
| Workers | 71 | 48 | 68% |
| Routes | 78 | 47 | 60% |
| Services | TBD | TBD | TBD |

**Target: 90% coverage before production deploy**

---

## Test Organization

```
sakhi/tests/
├── conftest.py              # Shared fixtures (DB, client, demo user)
├── fixtures/                # Test data factories
│   ├── constants.py         # Demo user IDs, sample data
│   ├── factories.py         # Data creation functions
│   └── helpers.py           # DB setup/teardown helpers
├── unit/                    # Unit tests (no DB required)
│   ├── workers/             # Worker logic tests (mocked DB)
│   └── services/            # Service logic tests (mocked DB)
├── integration/             # Integration tests (real DB)
│   ├── routes/              # API endpoint tests
│   └── workers/             # Worker + DB tests
└── e2e/                     # End-to-end flows
    └── conversation/        # Full conversation flow tests
```

---

## Workers Test Status

### Priority 1: Core Pipeline Workers (Must Have)

| Worker | Status | Test File | Notes |
|--------|--------|-----------|-------|
| `turn_updates/runner.py` | ✅ | `workers/test_full_integration.py` | Main turn pipeline |
| `observe_pipeline/runner.py` | ✅ | `workers/test_full_integration.py` | Observation pipeline |
| `episodic_consolidation_v21.py` | ✅ | `workers/test_episodic_consolidation.py` | Memory consolidation |
| `pattern_crystallization_worker.py` | ✅ | `workers/test_pattern_crystallization.py` | Pattern detection |
| `ayurvedic_pipeline.py` | ✅ | `all_workers_test.py` | Ayurvedic signals |
| `soul_refresh_worker.py` | ✅ | `v2/test_workers.py` | Soul state |
| `esr_worker.py` | ✅ | `all_workers_test.py` | Emotion-Soul-Rhythm |

### Priority 2: State Update Workers (Should Have)

| Worker | Status | Test File | Notes |
|--------|--------|-----------|-------|
| `update_conversation_state.py` | ✅ | `unit/workers/test_state_update_workers.py` | 9 tests |
| `update_emotional_context.py` | ✅ | `unit/workers/test_state_update_workers.py` | 3 tests |
| `update_prompt_profile.py` | ✅ | `unit/workers/test_state_update_workers.py` | 5 tests |
| `update_relationship_arcs.py` | ✅ | `unit/workers/test_state_update_workers.py` | 5 tests |
| `update_theme_rhythm_links.py` | ✅ | `unit/workers/test_state_update_workers.py` | 5 tests |

### Priority 3: Reflection Workers (Should Have)

| Worker | Status | Test File | Notes |
|--------|--------|-----------|-------|
| `daily_reflection.py` | ✅ | `all_workers_test.py` | |
| `reflect_morning_presence.py` | ✅ | `unit/workers/test_reflection_workers_impl.py` | 6 tests |
| `reflect_person_memory.py` | ⬜ | - | Complex deps, needs integration test |
| `reflect_value_alignment.py` | ✅ | `unit/workers/test_reflection_workers_impl.py` | 7 tests |
| `reflective_loop.py` | ✅ | `unit/workers/test_reflection_workers_impl.py` | 1 test (shim) |

### Priority 4: Memory Workers (Should Have)

| Worker | Status | Test File | Notes |
|--------|--------|-----------|-------|
| `memory_fanout.py` | ⬜ | - | Needs test |
| `memory_synthesis.py` | ⬜ | - | Needs test |
| `embedding_consolidation.py` | ✅ | `all_workers_test.py` | |

### Priority 5: Rhythm/Body Workers (Nice to Have)

| Worker | Status | Test File | Notes |
|--------|--------|-----------|-------|
| `rhythm_forecast.py` | ✅ | `all_workers_test.py` | |
| `rhythm_inference.py` | ⬜ | - | Needs test |
| `rhythm_scheduler.py` | ✅ | `all_workers_test.py` | |
| `body_refresh.py` | ⬜ | - | Needs test |
| `learn_rhythm_profile.py` | ⬜ | - | Needs test |

### Priority 6: Job Schedulers (Nice to Have)

| Worker | Status | Test File | Notes |
|--------|--------|-----------|-------|
| `jobs.py` | ✅ | `all_workers_test.py` | |
| `jobs_alignment.py` | ⬜ | - | Needs test |
| `jobs_goal_actions.py` | ⬜ | - | Needs test |
| `jobs_presence.py` | ⬜ | - | Needs test |
| `jobs_prune.py` | ⬜ | - | Needs test |
| `jobs_reflection_hooks.py` | ⬜ | - | Needs test |

---

## Routes Test Status

### Priority 1: Core API Routes (Must Have)

| Route | Status | Test File | Notes |
|-------|--------|-----------|-------|
| `turn_v2.py` | ✅ | `v2/test_turn_v2.py` | Main conversation endpoint |
| `health.py` | ✅ | `api/test_health.py` | Health checks |
| `friction_framework.py` | ✅ | `friction_framework/test_friction_framework_integration.py` | Friction state |
| `memory.py` | ✅ | `workers/test_memory_graph_wiring.py` | Memory recall |
| `memory_graph.py` | ✅ | `memory_graph/test_memory_graph_integration.py` | Graph queries |

### Priority 2: User-Facing Routes (Should Have)

| Route | Status | Test File | Notes |
|-------|--------|-----------|-------|
| `calendar.py` | ⬜ | - | Needs test |
| `chat.py` | ⬜ | - | Needs test |
| `recommendations.py` | ⬜ | - | Needs test |
| `scheduling.py` | ⬜ | - | Needs test |
| `feedback.py` | ⬜ | - | Needs test |
| `insights.py` | ⬜ | - | Needs test |

### Priority 3: Agent Routes (Should Have)

| Route | Status | Test File | Notes |
|-------|--------|-----------|-------|
| `agent.py` | ⬜ | - | Desktop agent |
| `agentic.py` | ⬜ | - | Task execution |
| `missions.py` | ⬜ | - | Long-running tasks |
| `vision.py` | ⬜ | - | Vision loop |

### Priority 4: Analytics Routes (Nice to Have)

| Route | Status | Test File | Notes |
|-------|--------|-----------|-------|
| `analytics/breath.py` | ⬜ | - | Needs test |
| `analytics/patterns.py` | ⬜ | - | Needs test |
| `analytics/summary.py` | ⬜ | - | Needs test |
| `analytics/themes.py` | ⬜ | - | Needs test |
| `analytics/timeseries.py` | ⬜ | - | Needs test |

### Priority 5: Mesh/Coordination (Future)

| Route | Status | Test File | Notes |
|-------|--------|-----------|-------|
| `mesh.py` | ⬜ | - | Inter-Sakhi |
| `knowledge_graph.py` | ⬜ | - | Graph queries |

---

## Pre-Deploy Test Checklist

Before any production deploy, run:

```bash
# 1. Run all tests
make test

# 2. Run integration tests specifically
make integration-test

# 3. Check test coverage
make test-coverage

# 4. Build verification
make build-check
```

### Minimum Requirements for Deploy:
- [ ] All unit tests pass
- [ ] All integration tests pass
- [ ] Core pipeline workers tested (Priority 1)
- [ ] Core API routes tested (Priority 1)
- [ ] No regressions in existing tests

---

## Adding New Tests

### For Workers:
```bash
# Create test scaffold
make new-worker-test name=my_worker

# Or manually create in:
sakhi/tests/unit/workers/test_my_worker.py      # Unit test (mocked DB)
sakhi/tests/integration/workers/test_my_worker.py  # Integration test (real DB)
```

### For Routes:
```bash
# Create test scaffold
make new-route-test name=my_route

# Or manually create in:
sakhi/tests/integration/routes/test_my_route.py
```

### Test Template:
```python
"""
Tests for {module_name}.

Unit tests: Mock DB, test logic only
Integration tests: Real DB, test full flow
"""

import pytest
from sakhi.tests.fixtures import DEMO_USER_ID, ensure_test_user


class TestMyWorkerUnit:
    """Unit tests - no real DB."""

    @pytest.mark.asyncio
    async def test_basic_logic(self, mock_db):
        # Test with mocked database
        pass


@pytest.mark.integration
class TestMyWorkerIntegration:
    """Integration tests - real DB required."""

    @pytest.fixture(autouse=True)
    async def setup(self):
        await ensure_test_user(DEMO_USER_ID)

    @pytest.mark.asyncio
    async def test_full_flow(self):
        # Test with real database
        pass
```

---

## Test Commands Reference

| Command | Description |
|---------|-------------|
| `make test` | Run all tests |
| `make quick-test` | Run smoke tests only |
| `make integration-test` | Run integration tests only |
| `make test-coverage` | Generate coverage report |
| `make test-workers` | Run worker tests only |
| `make test-routes` | Run route tests only |
| `pytest -k "worker"` | Run tests matching pattern |
| `pytest --lf` | Run last failed tests |
| `pytest -x` | Stop on first failure |
