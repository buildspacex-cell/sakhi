"""Unit tests for recurring agentic scheduling logic."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from sakhi.apps.api.services.agentic.planner import TaskStatus
from sakhi.apps.api.services.agentic.recurring import (
    RecurringRunLog,
    RecurringRunStatus,
    RecurringSchedule,
    RecurringScheduleStatus,
    _compute_next_monthly_run,
    _run_status_from_plan,
    execute_due_recurring_schedules,
)


class TestRecurringRunTimeMath:
    def test_compute_next_monthly_run_moves_forward_when_slot_has_passed(self):
        # Reference is after Jan 1st at 9:00 UTC, so next run should be Feb 1st 9:00 UTC.
        reference = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
        result = _compute_next_monthly_run(
            reference,
            run_timezone="UTC",
            day_of_month=1,
            run_hour=9,
            run_minute=0,
        )
        assert result == datetime(2026, 2, 1, 9, 0, tzinfo=timezone.utc)

    def test_compute_next_monthly_run_clamps_invalid_day_for_short_month(self):
        # February 2026 has 28 days, so day=31 should clamp to Feb 28.
        reference = datetime(2026, 1, 30, 12, 0, tzinfo=timezone.utc)
        result = _compute_next_monthly_run(
            reference,
            run_timezone="UTC",
            day_of_month=31,
            run_hour=9,
            run_minute=0,
        )
        assert result == datetime(2026, 1, 31, 9, 0, tzinfo=timezone.utc)

        reference_after = datetime(2026, 1, 31, 12, 0, tzinfo=timezone.utc)
        result_after = _compute_next_monthly_run(
            reference_after,
            run_timezone="UTC",
            day_of_month=31,
            run_hour=9,
            run_minute=0,
        )
        assert result_after == datetime(2026, 2, 28, 9, 0, tzinfo=timezone.utc)

    def test_run_status_mapping_from_task_plan_status(self):
        assert _run_status_from_plan(TaskStatus.COMPLETED) == RecurringRunStatus.COMPLETED
        assert _run_status_from_plan(TaskStatus.CANCELLED) == RecurringRunStatus.CANCELLED
        assert _run_status_from_plan(TaskStatus.FAILED) == RecurringRunStatus.FAILED
        assert _run_status_from_plan("paused") == RecurringRunStatus.FAILED


@pytest.mark.asyncio
async def test_execute_due_recurring_schedules_processes_claimed_schedule(monkeypatch):
    schedule_id = "f3ac3227-9e78-4940-95f6-35e7ceef17ad"
    claimed_row = {
        "id": schedule_id,
        "person_id": "person-1",
        "task_description": "Monthly subscription audit",
        "goal_hint": None,
        "cadence": "monthly",
        "cadence_interval": 1,
        "run_timezone": "UTC",
        "day_of_month": 1,
        "run_hour": 9,
        "run_minute": 0,
        "status": "active",
        "is_running": True,
        "next_run_at": datetime(2026, 2, 1, 9, 0, tzinfo=timezone.utc),
        "last_run_at": None,
        "last_run_status": None,
        "consecutive_failures": 0,
        "created_plan_id": None,
        "latest_plan_id": None,
        "metadata": {},
        "created_at": datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc),
        "updated_at": datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc),
    }
    schedule = RecurringSchedule(
        id=schedule_id,
        person_id="person-1",
        task_description="Monthly subscription audit",
        cadence="monthly",
        cadence_interval=1,
        run_timezone="UTC",
        day_of_month=1,
        run_hour=9,
        run_minute=0,
        status=RecurringScheduleStatus.ACTIVE,
        is_running=False,
        next_run_at=datetime(2026, 3, 1, 9, 0, tzinfo=timezone.utc),
    )
    run_log = RecurringRunLog(
        id="d38b6ea4-05ad-4ecf-b99a-a2b1832ecf7a",
        schedule_id=schedule_id,
        person_id="person-1",
        status=RecurringRunStatus.COMPLETED,
        started_at=datetime(2026, 2, 1, 9, 0, tzinfo=timezone.utc),
    )

    dbfetch_mock = AsyncMock(side_effect=[[{"id": schedule_id}], claimed_row])
    execute_claimed_mock = AsyncMock(return_value=(schedule, None, run_log))
    ensure_mock = AsyncMock()

    monkeypatch.setattr("sakhi.apps.api.services.agentic.recurring.dbfetch", dbfetch_mock)
    monkeypatch.setattr(
        "sakhi.apps.api.services.agentic.recurring._execute_claimed_schedule",
        execute_claimed_mock,
    )
    monkeypatch.setattr(
        "sakhi.apps.api.services.agentic.recurring._ensure_recurring_tables",
        ensure_mock,
    )

    result = await execute_due_recurring_schedules(limit=5)

    assert result["processed"] == 1
    assert result["runs"][0]["schedule_id"] == schedule_id
    assert result["runs"][0]["status"] == "completed"
    assert execute_claimed_mock.await_count == 1
