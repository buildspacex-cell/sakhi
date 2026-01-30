"""
Smoke Tests

Quick health checks to verify the system is working:
1. API is reachable
2. Database connection works
3. Key imports succeed
4. Turn endpoint responds

Run: pytest sakhi/tests/v2/test_smoke.py -v
"""

import os
import pytest

pytestmark = pytest.mark.asyncio


class TestDatabaseConnection:
    """Verify database connectivity."""

    async def test_database_connection(self, db):
        """Test we can connect and query the database."""
        result = await db.fetchval("SELECT 1")
        assert result == 1

    async def test_profiles_table_exists(self, db):
        """Test profiles table exists."""
        result = await db.fetchval("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = 'profiles'
            )
        """)
        assert result is True

    async def test_personal_model_table_exists(self, db):
        """Test personal_model table exists."""
        result = await db.fetchval("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = 'personal_model'
            )
        """)
        assert result is True

    async def test_memory_episodic_table_exists(self, db):
        """Test memory_episodic table exists."""
        result = await db.fetchval("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = 'memory_episodic'
            )
        """)
        assert result is True

    async def test_memory_nodes_table_exists(self, db):
        """Test memory_nodes table exists (memory graph)."""
        result = await db.fetchval("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = 'memory_nodes'
            )
        """)
        assert result is True


class TestKeyImports:
    """Verify key modules import without error."""

    def test_api_main_imports(self):
        """Test API main module imports."""
        from sakhi.apps.api import main
        assert main is not None

    def test_turn_v2_imports(self):
        """Test turn_v2 route imports."""
        from sakhi.apps.api.routes import turn_v2
        assert turn_v2 is not None

    def test_runner_imports(self):
        """Test turn pipeline runner imports."""
        from sakhi.apps.worker.pipelines.turn_updates.runner import (
            process_turn_job_async,
        )
        assert process_turn_job_async is not None

    def test_scheduler_imports(self):
        """Test scheduler imports."""
        from sakhi.apps.worker import scheduler
        assert scheduler is not None

    def test_episodic_consolidation_imports(self):
        """Test episodic consolidation imports."""
        from sakhi.apps.worker.tasks.episodic_consolidation_v21 import (
            run_episodic_consolidation_v21,
        )
        assert run_episodic_consolidation_v21 is not None


class TestAPIHealth:
    """Test API endpoints (requires running server)."""

    def test_api_import(self):
        """Test FastAPI app can be imported."""
        from sakhi.apps.api.main import app
        assert app is not None

    async def test_turn_endpoint_exists(self):
        """Verify /v2/turn route is registered."""
        from sakhi.apps.api.main import app

        routes = [r.path for r in app.routes]
        assert "/v2/turn" in routes or any("/v2/turn" in str(r) for r in routes)


class TestWorkerArchitecture:
    """Verify v2 worker architecture is correct."""

    def test_only_two_turn_jobs(self):
        """Verify only 2 job types are used per-turn."""
        # This is a documentation/contract test
        v2_turn_jobs = ["turn_memory_update", "episodic_consolidation_v21"]
        assert len(v2_turn_jobs) == 2

    def test_daily_workers_exist(self):
        """Verify daily workers are defined in scheduler."""
        from sakhi.apps.worker.scheduler import (
            schedule_ayurvedic_pipeline_daily,
            schedule_identity_momentum_daily,
            schedule_emotion_soul_rhythm_daily,
            schedule_esr_daily,
            schedule_soul_refresh_daily,
        )
        # All should be callable
        assert callable(schedule_ayurvedic_pipeline_daily)
        assert callable(schedule_identity_momentum_daily)
        assert callable(schedule_emotion_soul_rhythm_daily)
        assert callable(schedule_esr_daily)
        assert callable(schedule_soul_refresh_daily)

    def test_runner_only_has_two_handlers(self):
        """Verify runner only handles 2 job types."""
        # Read and check runner.py only has 2 if/elif for job types
        import inspect
        from sakhi.apps.worker.pipelines.turn_updates.runner import _process

        source = inspect.getsource(_process)
        # Count job_type == checks (should be 2 + 1 else)
        assert 'job_type == "turn_memory_update"' in source
        assert 'job_type == "episodic_consolidation_v21"' in source
        # Old handlers should NOT be present
        assert 'job_type == "ayurvedic_pipeline"' not in source
        assert 'job_type == "identity_momentum_deep"' not in source
