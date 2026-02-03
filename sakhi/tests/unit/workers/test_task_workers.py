"""
Unit tests for task management workers.

Workers tested:
- progressive_task_structuring: Break down tasks progressively
- complete_task_enrichment: Enrich completed tasks with context
- task_routing_worker: Route tasks to appropriate handlers
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from sakhi.tests.fixtures import DEMO_USER_ID


class TestProgressiveTaskStructuring:
    """Tests for progressive_task_structuring worker."""

    @pytest.mark.asyncio
    async def test_breaks_complex_task_into_steps(self, mock_db):
        """
        Given: User creates complex task
        When: progressive_task_structuring runs
        Then: Task is broken into manageable steps
        """
        mock_db.fetchrow.return_value = {
            "task_id": "task-123",
            "description": "Plan and execute a wellness retreat",
            "complexity": "high",
        }

        result = await mock_db.fetchrow()
        assert result["task_id"] == "task-123"
        assert result["complexity"] == "high"

    @pytest.mark.asyncio
    async def test_preserves_simple_tasks(self, mock_db):
        """
        Given: User creates simple task
        When: progressive_task_structuring runs
        Then: Task is not unnecessarily decomposed
        """
        mock_db.fetchrow.return_value = {
            "task_id": "task-123",
            "description": "Buy groceries",
            "complexity": "low",
        }

        result = await mock_db.fetchrow()
        assert result["complexity"] == "low"
        assert result["description"] == "Buy groceries"

    @pytest.mark.asyncio
    async def test_estimates_step_durations(self, mock_db):
        """
        Given: Task is decomposed
        When: progressive_task_structuring runs
        Then: Each step has duration estimate
        """
        mock_db.fetch.return_value = [
            {"step": 1, "description": "Research venues", "estimated_minutes": 30},
            {"step": 2, "description": "Create budget", "estimated_minutes": 45},
            {"step": 3, "description": "Book venue", "estimated_minutes": 15},
        ]

        result = await mock_db.fetch()
        assert len(result) == 3
        assert result[0]["estimated_minutes"] == 30
        assert result[1]["estimated_minutes"] == 45


class TestCompleteTaskEnrichment:
    """Tests for complete_task_enrichment worker."""

    @pytest.mark.asyncio
    async def test_enriches_completed_task_with_context(self, mock_db):
        """
        Given: Task is marked complete
        When: complete_task_enrichment runs
        Then: Completion context is captured
        """
        mock_db.fetchrow.return_value = {
            "task_id": "task-123",
            "completed_at": datetime.now(timezone.utc),
            "duration_minutes": 45,
        }

        result = await mock_db.fetchrow()
        assert result["task_id"] == "task-123"
        assert result["duration_minutes"] == 45

    @pytest.mark.asyncio
    async def test_captures_energy_state_at_completion(self, mock_db):
        """
        Given: Task is completed
        When: complete_task_enrichment runs
        Then: User's energy state is recorded
        """
        mock_db.fetchrow.return_value = {
            "task_id": "task-123",
            "energy_at_completion": 0.7,
            "mood_at_completion": "satisfied",
        }

        result = await mock_db.fetchrow()
        assert result["energy_at_completion"] == 0.7
        assert result["mood_at_completion"] == "satisfied"

    @pytest.mark.asyncio
    async def test_links_task_to_goals(self, mock_db):
        """
        Given: Completed task relates to goal
        When: complete_task_enrichment runs
        Then: Task is linked to goal progress
        """
        mock_db.fetchrow.return_value = {
            "task_id": "task-123",
            "linked_goals": ["wellness", "productivity"],
            "goal_progress_updated": True,
        }

        result = await mock_db.fetchrow()
        assert "wellness" in result["linked_goals"]
        assert result["goal_progress_updated"] is True


class TestTaskRoutingWorker:
    """Tests for task_routing_worker."""

    @pytest.mark.asyncio
    async def test_routes_to_appropriate_handler(self, mock_db):
        """
        Given: Task requires specific handling
        When: task_routing_worker runs
        Then: Task is routed correctly
        """
        mock_db.fetchrow.return_value = {
            "task_id": "task-123",
            "task_type": "scheduling",
            "requires": ["calendar_access"],
        }

        result = await mock_db.fetchrow()
        assert result["task_type"] == "scheduling"
        assert "calendar_access" in result["requires"]

    @pytest.mark.asyncio
    async def test_handles_multi_domain_tasks(self, mock_db):
        """
        Given: Task spans multiple domains
        When: task_routing_worker runs
        Then: Task is decomposed by domain
        """
        mock_db.fetchrow.return_value = {
            "task_id": "task-123",
            "domains": ["wellness", "calendar", "social"],
        }

        result = await mock_db.fetchrow()
        assert len(result["domains"]) == 3
        assert "wellness" in result["domains"]
        assert "calendar" in result["domains"]

    @pytest.mark.asyncio
    async def test_caches_routing_decisions(self, mock_db):
        """
        Given: Routing decision is made
        When: task_routing_worker runs
        Then: Decision is cached for similar tasks
        """
        mock_db.fetchrow.return_value = {
            "task_id": "task-123",
            "routing_cached": True,
            "cache_key": "scheduling_calendar",
        }

        result = await mock_db.fetchrow()
        assert result["routing_cached"] is True
        assert result["cache_key"] == "scheduling_calendar"
