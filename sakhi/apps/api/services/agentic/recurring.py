"""
Recurring Task Scheduler Service
--------------------------------
Durable recurring task schedules and run logs for Stage 2 automation.
"""

from __future__ import annotations

import asyncio
import calendar
import json
import logging
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo
import uuid

from pydantic import BaseModel, Field

from sakhi.apps.api.core.db import q as dbfetch, exec as dbexec
from sakhi.apps.api.core.event_logger import log_event
from sakhi.apps.api.services.agentic.planner import (
    TaskPlan,
    TaskStatus,
    approve_task_plan,
    cancel_task_plan,
    create_task_plan,
    get_task_plan,
)

LOGGER = logging.getLogger(__name__)

_RECURRING_TABLES_READY = False
_RECURRING_TABLES_LOCK = asyncio.Lock()


class RecurringScheduleStatus(str, Enum):
    PENDING_APPROVAL = "pending_approval"
    ACTIVE = "active"
    PAUSED = "paused"
    CANCELLED = "cancelled"


class RecurringRunStatus(str, Enum):
    STARTED = "started"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class RecurringSchedule(BaseModel):
    id: str
    person_id: str
    task_description: str
    goal_hint: Optional[str] = None
    cadence: str = "monthly"
    cadence_interval: int = 1
    run_timezone: str = "UTC"
    day_of_month: int = 1
    run_hour: int = 9
    run_minute: int = 0
    status: RecurringScheduleStatus = RecurringScheduleStatus.PENDING_APPROVAL
    is_running: bool = False
    next_run_at: Optional[datetime] = None
    last_run_at: Optional[datetime] = None
    last_run_status: Optional[str] = None
    consecutive_failures: int = 0
    created_plan_id: Optional[str] = None
    latest_plan_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class RecurringRunLog(BaseModel):
    id: str
    schedule_id: str
    person_id: str
    plan_id: Optional[str] = None
    trigger_source: str = "scheduler"
    status: RecurringRunStatus = RecurringRunStatus.STARTED
    started_at: datetime
    completed_at: Optional[datetime] = None
    summary: Optional[str] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


async def _ensure_recurring_tables() -> None:
    """
    Ensure recurring schedule tables exist.

    Matches migration 0009 for local/staging resilience.
    """
    global _RECURRING_TABLES_READY
    if _RECURRING_TABLES_READY:
        return

    async with _RECURRING_TABLES_LOCK:
        if _RECURRING_TABLES_READY:
            return

        await dbexec(
            """
            CREATE TABLE IF NOT EXISTS agent_task_schedules (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                person_id TEXT NOT NULL,
                task_description TEXT NOT NULL,
                goal_hint TEXT,
                cadence TEXT NOT NULL DEFAULT 'monthly',
                cadence_interval INTEGER NOT NULL DEFAULT 1,
                run_timezone TEXT NOT NULL DEFAULT 'UTC',
                day_of_month INTEGER NOT NULL DEFAULT 1,
                run_hour INTEGER NOT NULL DEFAULT 9,
                run_minute INTEGER NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'pending_approval',
                is_running BOOLEAN NOT NULL DEFAULT FALSE,
                next_run_at TIMESTAMPTZ,
                last_run_at TIMESTAMPTZ,
                last_run_status TEXT,
                consecutive_failures INTEGER NOT NULL DEFAULT 0,
                created_plan_id TEXT,
                latest_plan_id TEXT,
                metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )
        await dbexec(
            """
            CREATE TABLE IF NOT EXISTS agent_task_schedule_runs (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                schedule_id UUID NOT NULL REFERENCES agent_task_schedules(id) ON DELETE CASCADE,
                person_id TEXT NOT NULL,
                plan_id TEXT,
                trigger_source TEXT NOT NULL DEFAULT 'scheduler',
                status TEXT NOT NULL DEFAULT 'started',
                started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                completed_at TIMESTAMPTZ,
                summary TEXT,
                error TEXT,
                metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )
        await dbexec(
            """
            CREATE INDEX IF NOT EXISTS idx_agent_task_schedules_person_status
            ON agent_task_schedules(person_id, status)
            """
        )
        await dbexec(
            """
            CREATE INDEX IF NOT EXISTS idx_agent_task_schedules_due
            ON agent_task_schedules(status, is_running, next_run_at)
            """
        )
        await dbexec(
            """
            CREATE INDEX IF NOT EXISTS idx_agent_task_schedule_runs_schedule_created
            ON agent_task_schedule_runs(schedule_id, created_at DESC)
            """
        )
        _RECURRING_TABLES_READY = True


def _normalize_timezone(tz_name: str) -> str:
    candidate = (tz_name or "UTC").strip() or "UTC"
    try:
        ZoneInfo(candidate)
        return candidate
    except Exception:
        return "UTC"


def _clamp(value: int, minimum: int, maximum: int) -> int:
    return max(minimum, min(maximum, int(value)))


def _compute_next_monthly_run(
    reference_utc: datetime,
    run_timezone: str,
    day_of_month: int,
    run_hour: int,
    run_minute: int,
) -> datetime:
    if reference_utc.tzinfo is None:
        reference_utc = reference_utc.replace(tzinfo=timezone.utc)
    tz = ZoneInfo(_normalize_timezone(run_timezone))
    local_ref = reference_utc.astimezone(tz)

    year = local_ref.year
    month = local_ref.month

    current_month_days = calendar.monthrange(year, month)[1]
    day = min(_clamp(day_of_month, 1, 31), current_month_days)
    candidate_local = datetime(
        year,
        month,
        day,
        _clamp(run_hour, 0, 23),
        _clamp(run_minute, 0, 59),
        tzinfo=tz,
    )

    if candidate_local <= local_ref:
        if month == 12:
            year += 1
            month = 1
        else:
            month += 1
        next_month_days = calendar.monthrange(year, month)[1]
        day = min(_clamp(day_of_month, 1, 31), next_month_days)
        candidate_local = datetime(
            year,
            month,
            day,
            _clamp(run_hour, 0, 23),
            _clamp(run_minute, 0, 59),
            tzinfo=tz,
        )

    return candidate_local.astimezone(timezone.utc)


def _run_status_from_plan(plan_status: str | TaskStatus) -> RecurringRunStatus:
    status = plan_status.value if isinstance(plan_status, TaskStatus) else str(plan_status)
    if status == TaskStatus.COMPLETED.value:
        return RecurringRunStatus.COMPLETED
    if status == TaskStatus.CANCELLED.value:
        return RecurringRunStatus.CANCELLED
    return RecurringRunStatus.FAILED


def _first_failed_step_error(plan: TaskPlan) -> Optional[str]:
    for step in plan.steps:
        if step.status.value == "failed":
            return step.error or "Step failed"
    return None


def _row_to_schedule(row: Dict[str, Any]) -> RecurringSchedule:
    return RecurringSchedule(
        id=str(row["id"]),
        person_id=row["person_id"],
        task_description=row["task_description"],
        goal_hint=row.get("goal_hint"),
        cadence=row.get("cadence") or "monthly",
        cadence_interval=row.get("cadence_interval") or 1,
        run_timezone=row.get("run_timezone") or "UTC",
        day_of_month=row.get("day_of_month") or 1,
        run_hour=row.get("run_hour") or 9,
        run_minute=row.get("run_minute") or 0,
        status=RecurringScheduleStatus(row.get("status") or "pending_approval"),
        is_running=bool(row.get("is_running")),
        next_run_at=row.get("next_run_at"),
        last_run_at=row.get("last_run_at"),
        last_run_status=row.get("last_run_status"),
        consecutive_failures=row.get("consecutive_failures") or 0,
        created_plan_id=row.get("created_plan_id"),
        latest_plan_id=row.get("latest_plan_id"),
        metadata=row.get("metadata") or {},
        created_at=row.get("created_at"),
        updated_at=row.get("updated_at"),
    )


def _row_to_run_log(row: Dict[str, Any]) -> RecurringRunLog:
    return RecurringRunLog(
        id=str(row["id"]),
        schedule_id=str(row["schedule_id"]),
        person_id=row["person_id"],
        plan_id=row.get("plan_id"),
        trigger_source=row.get("trigger_source") or "scheduler",
        status=RecurringRunStatus(row.get("status") or "started"),
        started_at=row["started_at"],
        completed_at=row.get("completed_at"),
        summary=row.get("summary"),
        error=row.get("error"),
        metadata=row.get("metadata") or {},
        created_at=row.get("created_at"),
        updated_at=row.get("updated_at"),
    )


async def _log_recurring_event(person_id: str, event: str, payload: Dict[str, Any]) -> None:
    try:
        await log_event(
            person_id=person_id,
            layer="stage2_outer_action",
            event=event,
            payload=payload,
        )
    except Exception as exc:
        LOGGER.debug("[recurring] Event log failed for %s: %s", event, exc)


async def create_recurring_schedule(
    *,
    person_id: str,
    task_description: str,
    goal_hint: Optional[str] = None,
    cadence: str = "monthly",
    cadence_interval: int = 1,
    run_timezone: str = "UTC",
    day_of_month: int = 1,
    run_hour: int = 9,
    run_minute: int = 0,
    metadata: Optional[Dict[str, Any]] = None,
) -> Tuple[RecurringSchedule, TaskPlan]:
    """Create recurring schedule + initial pending-approval plan."""
    await _ensure_recurring_tables()

    normalized_cadence = (cadence or "monthly").strip().lower()
    if normalized_cadence != "monthly":
        raise ValueError("Only monthly cadence is supported right now")

    plan = await create_task_plan(
        person_id=person_id,
        task_description=task_description,
        session_id=None,
        auto_approve=False,
    )

    safe_timezone = _normalize_timezone(run_timezone)
    safe_day = _clamp(day_of_month, 1, 31)
    safe_hour = _clamp(run_hour, 0, 23)
    safe_minute = _clamp(run_minute, 0, 59)
    safe_interval = max(int(cadence_interval), 1)
    next_run_at = _compute_next_monthly_run(
        datetime.now(timezone.utc),
        safe_timezone,
        safe_day,
        safe_hour,
        safe_minute,
    )

    row = await dbfetch(
        """
        INSERT INTO agent_task_schedules (
            person_id,
            task_description,
            goal_hint,
            cadence,
            cadence_interval,
            run_timezone,
            day_of_month,
            run_hour,
            run_minute,
            status,
            next_run_at,
            created_plan_id,
            latest_plan_id,
            metadata
        )
        VALUES (
            $1, $2, $3, $4, $5, $6, $7, $8, $9,
            'pending_approval', $10, $11, $12, $13::jsonb
        )
        RETURNING *
        """,
        person_id,
        task_description,
        goal_hint,
        normalized_cadence,
        safe_interval,
        safe_timezone,
        safe_day,
        safe_hour,
        safe_minute,
        next_run_at,
        plan.id,
        plan.id,
        json.dumps(metadata or {}),
        one=True,
    )
    schedule = _row_to_schedule(row)

    await _log_recurring_event(
        person_id,
        "recurring_schedule_created",
        {
            "schedule_id": schedule.id,
            "plan_id": plan.id,
            "cadence": schedule.cadence,
        },
    )
    return schedule, plan


async def get_recurring_schedule(
    schedule_id: str,
    person_id: Optional[str] = None,
) -> Optional[RecurringSchedule]:
    await _ensure_recurring_tables()
    if person_id:
        row = await dbfetch(
            "SELECT * FROM agent_task_schedules WHERE id = $1::uuid AND person_id = $2",
            schedule_id,
            person_id,
            one=True,
        )
    else:
        row = await dbfetch(
            "SELECT * FROM agent_task_schedules WHERE id = $1::uuid",
            schedule_id,
            one=True,
        )
    if not row:
        return None
    return _row_to_schedule(row)


async def list_recurring_schedules(
    person_id: str,
    *,
    include_inactive: bool = False,
    limit: int = 20,
) -> List[RecurringSchedule]:
    await _ensure_recurring_tables()
    if include_inactive:
        rows = await dbfetch(
            """
            SELECT * FROM agent_task_schedules
            WHERE person_id = $1
            ORDER BY created_at DESC
            LIMIT $2
            """,
            person_id,
            limit,
        )
    else:
        rows = await dbfetch(
            """
            SELECT * FROM agent_task_schedules
            WHERE person_id = $1
              AND status != 'cancelled'
            ORDER BY created_at DESC
            LIMIT $2
            """,
            person_id,
            limit,
        )

    return [_row_to_schedule(row) for row in (rows or [])]


async def get_recurring_schedule_runs(
    schedule_id: str,
    *,
    limit: int = 20,
) -> List[RecurringRunLog]:
    await _ensure_recurring_tables()
    rows = await dbfetch(
        """
        SELECT *
        FROM agent_task_schedule_runs
        WHERE schedule_id = $1::uuid
        ORDER BY created_at DESC
        LIMIT $2
        """,
        schedule_id,
        limit,
    )
    return [_row_to_run_log(row) for row in (rows or [])]


async def _create_run_log(
    *,
    schedule: RecurringSchedule,
    plan_id: Optional[str],
    trigger_source: str,
) -> RecurringRunLog:
    row = await dbfetch(
        """
        INSERT INTO agent_task_schedule_runs (
            schedule_id,
            person_id,
            plan_id,
            trigger_source,
            status,
            started_at,
            metadata
        )
        VALUES ($1::uuid, $2, $3, $4, 'started', NOW(), '{}'::jsonb)
        RETURNING *
        """,
        schedule.id,
        schedule.person_id,
        plan_id,
        trigger_source,
        one=True,
    )
    return _row_to_run_log(row)


async def _finalize_run_log(
    run_log_id: str,
    *,
    status: RecurringRunStatus,
    summary: Optional[str] = None,
    error: Optional[str] = None,
    plan_id: Optional[str] = None,
) -> RecurringRunLog:
    row = await dbfetch(
        """
        UPDATE agent_task_schedule_runs
        SET status = $2,
            summary = $3,
            error = $4,
            plan_id = COALESCE($5, plan_id),
            completed_at = NOW(),
            updated_at = NOW()
        WHERE id = $1::uuid
        RETURNING *
        """,
        run_log_id,
        status.value,
        summary,
        error,
        plan_id,
        one=True,
    )
    return _row_to_run_log(row)


async def _mark_schedule_after_run(
    schedule: RecurringSchedule,
    *,
    latest_plan_id: Optional[str],
    run_status: RecurringRunStatus,
    next_run_at: datetime,
) -> RecurringSchedule:
    failure_count = schedule.consecutive_failures
    if run_status == RecurringRunStatus.COMPLETED:
        failure_count = 0
    elif run_status == RecurringRunStatus.FAILED:
        failure_count += 1

    row = await dbfetch(
        """
        UPDATE agent_task_schedules
        SET status = CASE
                WHEN status = 'pending_approval' THEN 'active'
                ELSE status
            END,
            is_running = FALSE,
            last_run_at = NOW(),
            last_run_status = $2,
            consecutive_failures = $3,
            latest_plan_id = COALESCE($4, latest_plan_id),
            next_run_at = $5,
            updated_at = NOW()
        WHERE id = $1::uuid
        RETURNING *
        """,
        schedule.id,
        run_status.value,
        failure_count,
        latest_plan_id,
        next_run_at,
        one=True,
    )
    return _row_to_schedule(row)


async def approve_recurring_schedule(
    schedule_id: str,
    person_id: str,
) -> Tuple[RecurringSchedule, TaskPlan, RecurringRunLog]:
    """Approve recurring setup and execute first run using its initial plan."""
    await _ensure_recurring_tables()
    schedule = await get_recurring_schedule(schedule_id, person_id=person_id)
    if not schedule:
        raise ValueError("Recurring schedule not found")
    if schedule.status == RecurringScheduleStatus.CANCELLED:
        raise ValueError("Recurring schedule is cancelled")
    if not schedule.created_plan_id:
        raise ValueError("Recurring schedule missing initial plan")

    run_log = await _create_run_log(
        schedule=schedule,
        plan_id=schedule.created_plan_id,
        trigger_source="initial_approval",
    )

    approved_plan = await approve_task_plan(schedule.created_plan_id, person_id)
    if approved_plan is None:
        existing_plan = await get_task_plan(schedule.created_plan_id)
        if not existing_plan:
            raise ValueError("Initial recurring plan not found")
        approved_plan = existing_plan

    run_status = _run_status_from_plan(approved_plan.status)
    run_error = _first_failed_step_error(approved_plan) if run_status == RecurringRunStatus.FAILED else None
    run_summary = approved_plan.final_output if run_status == RecurringRunStatus.COMPLETED else None

    finalized_run = await _finalize_run_log(
        run_log.id,
        status=run_status,
        summary=run_summary,
        error=run_error,
        plan_id=approved_plan.id,
    )

    next_run_at = schedule.next_run_at or _compute_next_monthly_run(
        datetime.now(timezone.utc),
        schedule.run_timezone,
        schedule.day_of_month,
        schedule.run_hour,
        schedule.run_minute,
    )
    if run_status == RecurringRunStatus.FAILED:
        # Retry sooner on failed first run.
        next_run_at = datetime.now(timezone.utc) + timedelta(hours=6)

    updated_schedule = await _mark_schedule_after_run(
        schedule,
        latest_plan_id=approved_plan.id,
        run_status=run_status,
        next_run_at=next_run_at,
    )

    await _log_recurring_event(
        person_id,
        "recurring_schedule_approved",
        {
            "schedule_id": updated_schedule.id,
            "plan_id": approved_plan.id,
            "run_status": run_status.value,
        },
    )

    return updated_schedule, approved_plan, finalized_run


async def cancel_recurring_schedule(
    schedule_id: str,
    person_id: str,
) -> bool:
    await _ensure_recurring_tables()
    schedule = await get_recurring_schedule(schedule_id, person_id=person_id)
    if not schedule:
        return False

    if schedule.status == RecurringScheduleStatus.PENDING_APPROVAL and schedule.created_plan_id:
        await cancel_task_plan(schedule.created_plan_id, person_id)

    await dbexec(
        """
        UPDATE agent_task_schedules
        SET status = 'cancelled',
            is_running = FALSE,
            updated_at = NOW()
        WHERE id = $1::uuid AND person_id = $2
        """,
        schedule_id,
        person_id,
    )
    await _log_recurring_event(
        person_id,
        "recurring_schedule_cancelled",
        {"schedule_id": schedule_id},
    )
    return True


async def _execute_claimed_schedule(
    schedule: RecurringSchedule,
    *,
    trigger_source: str,
) -> Tuple[RecurringSchedule, Optional[TaskPlan], RecurringRunLog]:
    run_log = await _create_run_log(schedule=schedule, plan_id=None, trigger_source=trigger_source)

    try:
        plan = await create_task_plan(
            person_id=schedule.person_id,
            task_description=schedule.task_description,
            session_id=f"recurring:{schedule.id}:{uuid.uuid4()}",
            auto_approve=True,
        )
        run_status = _run_status_from_plan(plan.status)
        run_error = _first_failed_step_error(plan) if run_status == RecurringRunStatus.FAILED else None
        run_summary = plan.final_output if run_status == RecurringRunStatus.COMPLETED else None

        if run_status == RecurringRunStatus.FAILED:
            next_run = datetime.now(timezone.utc) + timedelta(hours=6)
        else:
            next_run = _compute_next_monthly_run(
                datetime.now(timezone.utc),
                schedule.run_timezone,
                schedule.day_of_month,
                schedule.run_hour,
                schedule.run_minute,
            )

        finalized_run = await _finalize_run_log(
            run_log.id,
            status=run_status,
            summary=run_summary,
            error=run_error,
            plan_id=plan.id,
        )
        updated_schedule = await _mark_schedule_after_run(
            schedule,
            latest_plan_id=plan.id,
            run_status=run_status,
            next_run_at=next_run,
        )

        await _log_recurring_event(
            schedule.person_id,
            "recurring_schedule_run_completed",
            {
                "schedule_id": schedule.id,
                "plan_id": plan.id,
                "run_status": run_status.value,
                "trigger_source": trigger_source,
            },
        )
        return updated_schedule, plan, finalized_run
    except Exception as exc:
        LOGGER.error("[recurring] run failed for schedule %s: %s", schedule.id, exc)
        finalized_run = await _finalize_run_log(
            run_log.id,
            status=RecurringRunStatus.FAILED,
            summary=None,
            error=str(exc),
            plan_id=None,
        )
        retry_run = datetime.now(timezone.utc) + timedelta(hours=6)
        updated_schedule = await _mark_schedule_after_run(
            schedule,
            latest_plan_id=schedule.latest_plan_id,
            run_status=RecurringRunStatus.FAILED,
            next_run_at=retry_run,
        )
        return updated_schedule, None, finalized_run


async def run_recurring_schedule_now(
    schedule_id: str,
    person_id: str,
) -> Tuple[RecurringSchedule, Optional[TaskPlan], RecurringRunLog]:
    """Manually execute an active recurring schedule now."""
    await _ensure_recurring_tables()
    claimed = await dbfetch(
        """
        UPDATE agent_task_schedules
        SET is_running = TRUE,
            updated_at = NOW()
        WHERE id = $1::uuid
          AND person_id = $2
          AND status = 'active'
          AND is_running = FALSE
        RETURNING *
        """,
        schedule_id,
        person_id,
        one=True,
    )
    if not claimed:
        schedule = await get_recurring_schedule(schedule_id, person_id=person_id)
        if not schedule:
            raise ValueError("Recurring schedule not found")
        if schedule.status != RecurringScheduleStatus.ACTIVE:
            raise ValueError("Recurring schedule is not active")
        raise ValueError("Recurring schedule is already running")

    schedule = _row_to_schedule(claimed)
    return await _execute_claimed_schedule(schedule, trigger_source="manual")


async def execute_due_recurring_schedules(limit: int = 10) -> Dict[str, Any]:
    """Claim and execute due recurring schedules."""
    await _ensure_recurring_tables()

    rows = await dbfetch(
        """
        SELECT id
        FROM agent_task_schedules
        WHERE status = 'active'
          AND is_running = FALSE
          AND next_run_at IS NOT NULL
          AND next_run_at <= NOW()
        ORDER BY next_run_at ASC
        LIMIT $1
        """,
        max(1, int(limit)),
    )

    run_results: List[Dict[str, Any]] = []
    for row in rows or []:
        schedule_id = str(row["id"])
        claimed = await dbfetch(
            """
            UPDATE agent_task_schedules
            SET is_running = TRUE,
                updated_at = NOW()
            WHERE id = $1::uuid
              AND status = 'active'
              AND is_running = FALSE
              AND next_run_at <= NOW()
            RETURNING *
            """,
            schedule_id,
            one=True,
        )
        if not claimed:
            continue

        schedule = _row_to_schedule(claimed)
        updated_schedule, plan, run_log = await _execute_claimed_schedule(
            schedule,
            trigger_source="scheduler",
        )
        run_results.append(
            {
                "schedule_id": updated_schedule.id,
                "plan_id": plan.id if plan else None,
                "run_id": run_log.id,
                "status": run_log.status.value,
            }
        )

    return {
        "processed": len(run_results),
        "runs": run_results,
    }


__all__ = [
    "RecurringScheduleStatus",
    "RecurringRunStatus",
    "RecurringSchedule",
    "RecurringRunLog",
    "create_recurring_schedule",
    "get_recurring_schedule",
    "list_recurring_schedules",
    "get_recurring_schedule_runs",
    "approve_recurring_schedule",
    "cancel_recurring_schedule",
    "run_recurring_schedule_now",
    "execute_due_recurring_schedules",
]
