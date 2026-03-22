# Test Status Tracking

> Last Updated: 2026-03-18
>
> Run `make test-coverage` to regenerate this report.

---

## Coverage Summary

| Category | Total | Tested | Coverage |
|----------|-------|--------|----------|
| Workers | 86 task files | 48 | ~56% |
| Routes | 81 | 48 | ~59% |
| Kala (governance) | 49 source files | 552 tests | 100% |
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

## Recent Additions (2026-03-11)

| Area | Status | Test Files | Notes |
|------|--------|------------|-------|
| Support console privacy + route/session guards | ✅ | `unit/routes/test_support_console.py` | Validates support code normalization, metadata sanitization caps, active/expired status logic, create-flow diagnostics opt-out behavior, session timeline event-type guardrails + redaction, session reuse/event ingest behavior, operator inactive-code denial, and public bundle payload shape (metadata-only contract) |
| Turn v2 continuity product signal | ✅ | `unit/routes/test_turn_v2_continuity_signal.py` | Verifies non-debug `/v2/turn` continuity payload includes `deep_reflect` readiness plus optional cross-topic passthrough fields (`candidate_topics`, `cross_context`, `whole_story`, `life_dimensions`), and that chat Deep Reflect uses effective same-thread depth rather than only strict primary moments |
| Continuity service | ✅ | `unit/services/test_continuity_service.py`, `unit/services/test_continuity_chat.py`, `unit/services/test_continuity_reflection.py` | Policy gating, arc payload shaping, continuity pack generation (including compact history stats/phase path/anchors, qualitative arc summary with mirror-only mode, and cross-topic readiness signals), deep reflection job lifecycle, deterministic+LLM response persistence, `whole_story/cross_context` mode normalization with `topic_keys`, related-arc evidence dedupe, optional linked-thread whole-story prompting, priority-conflict emotion guardrails, topic-drift filtering, surface-policy carry-through, and prompt composition checks |
| Cross-topic continuity cache service | ✅ | `unit/services/test_continuity_cross_topic.py` | Verifies cached correlation normalization preserves related-topic depth for whole-story gating, confirms dominant mirror-safe primaries can unlock linked synthesis, validates unique-moment total counting across shared evidence, checks semantic vector fallback behavior, confirms profile-driven cache TTL handling, and covers delete-triggered cache invalidation behavior |
| Monitoring / on-call sink | ✅ | `unit/services/test_monitoring.py` | Webhook alert payload shaping, dedupe window behavior, disabled no-op behavior, sync exception-report bridge, burst-threshold alerts (auth failures, crash loops, export/delete spikes), and normalized break-glass alert events |
| Observability redaction | ✅ | `unit/services/test_observability_redaction.py`, `unit/services/test_monitoring.py` | Redacts sensitive free-text keys in telemetry/monitoring payloads and strips inline secret/token data from formatted log/alert strings |
| Env contract checker | ✅ | `unit/services/test_check_env.py` | Profile-based env contract validation (`local`, `prod_api`, `prod_web`, `ci`), alias handling, queue-mode Redis gating, and monitoring sink requirement checks |
| Journal crypto foundation | ✅ | `unit/services/test_journal_crypto.py`, `unit/services/test_check_env.py` | Per-user encryption roundtrip/key isolation, encrypted-only default payload policy, fail-closed master key contract (`SAKHI_JOURNAL_MASTER_KEY`, 32+ chars), and strict-mode decrypt failure coverage |
| Auth-bound person routing | ✅ | `unit/services/test_person_resolver.py`, `unit/services/test_continuity_reflection.py` | Production person binding enforces authenticated ownership on person-scoped routes and deep-reflection status/result fetches are now person-scoped (id + person_id) |
| Deterministic context loader | ✅ | `unit/services/test_deterministic_context_loader.py` | Confirms turn-time rhythm planner alignment is deferred by default and only loaded when explicitly enabled via feature flag |
| Pipeline hardening | ✅ | `unit/services/test_pipeline_hardening.py` | Continuity fallback resilience, recommendation filtering hygiene, and weekly rhythm rollup safeguards (disabled-by-policy, missing-table skip, missing-events fallback) |
| Simulation continuity compiler | ✅ | `unit/services/test_simulation_continuity.py`, `unit/services/test_simulation_continuity_benchmark.py`, `unit/services/test_thread_resolver.py` | Topic classification benchmark, deterministic compile output, bounded related-anchor projection for shared moments across threads, thread-aware follow-up attachment for ambiguous entries, contextual multi-thread attachment for close runner-ups, effective depth accounting (`primary` + `attached` vs `related`), unresolved-entry auditability, and arc construction safeguards |
| Journal identity resolution | ✅ | `unit/services/test_person_utils.py` | Verifies journal writes can resolve consistent `person_id` + `user_id` owner columns from person/profile mappings and direct profile ids |
| Kala arc primitives | ✅ | `kala/tests/test_arc.py` | Deterministic IDs, segmentation, features, structure-only summary |
| Web continuity mirror | ✅ | `apps/web/app/lab/simulation/__tests__/continuityMirror.spec.ts`, `apps/web/app/lab/simulation/__tests__/continuityArcDetail.spec.ts` | Mirror copy/recap behavior and explainability anchors |

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
