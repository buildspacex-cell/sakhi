"""
A.4.1 Intervention Plan Tracking
--------------------------------
Track long-term interventions with recurring schedules.

When Sakhi recommends something like "walk 20 min every alternate day
for 2 weeks", this system:
1. Creates an intervention plan with schedule
2. Tracks daily check-ins (did they do it?)
3. Sends nudges on scheduled days
4. Correlates adherence to symptom outcomes

Flow:
    Recommendation → User opts in → Plan created → Daily tracking → Outcome correlation
"""

from __future__ import annotations

import logging
from datetime import datetime, date, timedelta
from typing import Any, Dict, List, Optional
from enum import Enum
import json

from pydantic import BaseModel, Field

from sakhi.apps.api.core.db import q as dbfetch, exec as dbexec

LOGGER = logging.getLogger(__name__)


# =============================================================================
# Models
# =============================================================================

class ScheduleType(str, Enum):
    """How often the intervention should be done."""
    DAILY = "daily"
    ALTERNATE_DAYS = "alternate_days"
    WEEKLY = "weekly"  # e.g., every Monday, Wednesday, Friday
    SPECIFIC_DAYS = "specific_days"  # custom day pattern
    AS_NEEDED = "as_needed"  # track whenever they do it


class InterventionType(str, Enum):
    """Category of intervention."""
    ACTIVITY = "activity"  # walk, yoga, exercise
    FOOD = "food"  # dietary changes
    MINDFULNESS = "mindfulness"  # meditation, breathing
    SLEEP = "sleep"  # sleep hygiene
    SOCIAL = "social"  # connection activities
    AVOIDANCE = "avoidance"  # things to avoid
    CUSTOM = "custom"


class PlanStatus(str, Enum):
    """Status of an intervention plan."""
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


class CheckInStatus(str, Enum):
    """Status of a daily check-in."""
    PENDING = "pending"  # Scheduled, not yet checked
    DONE = "done"  # Completed
    SKIPPED = "skipped"  # User explicitly skipped
    MISSED = "missed"  # Day passed without check-in
    PARTIAL = "partial"  # Partially done


class InterventionPlan(BaseModel):
    """A tracked intervention plan."""
    id: str
    person_id: str
    intervention_type: InterventionType
    intervention_name: str
    description: Optional[str] = None

    # Schedule
    schedule_type: ScheduleType
    schedule_days: Optional[List[int]] = None  # 0=Mon, 6=Sun for SPECIFIC_DAYS
    target_per_day: int = 1  # How many times per scheduled day

    # Duration
    start_date: date
    end_date: Optional[date] = None
    duration_days: Optional[int] = None

    # Target
    target_symptom: Optional[str] = None
    target_dosha: Optional[str] = None
    baseline_severity: Optional[float] = None

    # Tracking
    status: PlanStatus = PlanStatus.ACTIVE
    total_scheduled: int = 0
    total_completed: int = 0
    current_streak: int = 0
    longest_streak: int = 0

    # Source
    recommendation_id: Optional[str] = None
    conversation_id: Optional[str] = None

    created_at: datetime = Field(default_factory=datetime.utcnow)


class DailyCheckIn(BaseModel):
    """A check-in for a specific day."""
    id: str
    plan_id: str
    scheduled_date: date
    status: CheckInStatus = CheckInStatus.PENDING
    completed_count: int = 0
    notes: Optional[str] = None
    mood_before: Optional[float] = None  # 0-1 scale
    mood_after: Optional[float] = None
    checked_in_at: Optional[datetime] = None
    nudge_sent: bool = False
    nudge_sent_at: Optional[datetime] = None


class CreatePlanRequest(BaseModel):
    """Request to create an intervention plan from a recommendation."""
    person_id: str
    intervention_type: str = "activity"
    intervention_name: str
    description: Optional[str] = None

    schedule_type: str = "daily"
    schedule_days: Optional[List[int]] = None
    target_per_day: int = 1

    duration_days: int = 14  # Default 2 weeks

    target_symptom: Optional[str] = None
    target_dosha: Optional[str] = None
    baseline_severity: Optional[float] = None

    recommendation_id: Optional[str] = None
    conversation_id: Optional[str] = None


class PlanProgress(BaseModel):
    """Progress summary for a plan."""
    plan_id: str
    plan_name: str
    status: str

    days_elapsed: int
    days_remaining: int

    adherence_rate: float  # 0-1
    total_scheduled: int
    total_completed: int
    total_missed: int

    current_streak: int
    longest_streak: int

    symptom_improvement: Optional[float] = None  # Percentage change

    next_scheduled: Optional[date] = None
    needs_checkin_today: bool = False


# =============================================================================
# Plan Creation
# =============================================================================

async def create_intervention_plan(request: CreatePlanRequest) -> InterventionPlan:
    """
    Create an intervention plan from a recommendation.

    Called when user opts in to track a recommended routine.
    """
    try:
        intervention_type = InterventionType(request.intervention_type)
    except ValueError:
        intervention_type = InterventionType.CUSTOM

    try:
        schedule_type = ScheduleType(request.schedule_type)
    except ValueError:
        schedule_type = ScheduleType.DAILY

    start_date = date.today()
    end_date = start_date + timedelta(days=request.duration_days)

    # Calculate total scheduled days
    total_scheduled = _calculate_scheduled_days(
        start_date, end_date, schedule_type, request.schedule_days
    )

    row = await dbfetch(
        """
        INSERT INTO intervention_plans (
            person_id, intervention_type, intervention_name, description,
            schedule_type, schedule_days, target_per_day,
            start_date, end_date, duration_days,
            target_symptom, target_dosha, baseline_severity,
            status, total_scheduled,
            recommendation_id, conversation_id
        ) VALUES (
            $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17
        )
        RETURNING *
        """,
        request.person_id,
        intervention_type.value,
        request.intervention_name,
        request.description,
        schedule_type.value,
        request.schedule_days,
        request.target_per_day,
        start_date,
        end_date,
        request.duration_days,
        request.target_symptom,
        request.target_dosha,
        request.baseline_severity,
        PlanStatus.ACTIVE.value,
        total_scheduled,
        request.recommendation_id,
        request.conversation_id,
        one=True,
    )

    plan_id = str(row["id"])

    # Generate check-in slots for the plan
    await _generate_checkin_slots(
        plan_id, start_date, end_date, schedule_type, request.schedule_days
    )

    LOGGER.info(
        "[intervention] Created plan %s: %s for %d days (%d scheduled)",
        plan_id[:8], request.intervention_name,
        request.duration_days, total_scheduled
    )

    return _row_to_plan(row)


def _calculate_scheduled_days(
    start: date,
    end: date,
    schedule_type: ScheduleType,
    schedule_days: Optional[List[int]],
) -> int:
    """Calculate how many days are scheduled in the date range."""
    count = 0
    current = start
    day_index = 0

    while current <= end:
        if _is_scheduled_day(current, day_index, schedule_type, schedule_days):
            count += 1
        current += timedelta(days=1)
        day_index += 1

    return count


def _is_scheduled_day(
    d: date,
    day_index: int,
    schedule_type: ScheduleType,
    schedule_days: Optional[List[int]],
) -> bool:
    """Check if a date is a scheduled intervention day."""
    if schedule_type == ScheduleType.DAILY:
        return True
    elif schedule_type == ScheduleType.ALTERNATE_DAYS:
        return day_index % 2 == 0
    elif schedule_type == ScheduleType.WEEKLY:
        # Default to Mon/Wed/Fri if not specified
        days = schedule_days or [0, 2, 4]
        return d.weekday() in days
    elif schedule_type == ScheduleType.SPECIFIC_DAYS:
        return d.weekday() in (schedule_days or [])
    elif schedule_type == ScheduleType.AS_NEEDED:
        return False  # No scheduled days, track whenever
    return False


async def _generate_checkin_slots(
    plan_id: str,
    start_date: date,
    end_date: date,
    schedule_type: ScheduleType,
    schedule_days: Optional[List[int]],
) -> None:
    """Pre-generate check-in slots for scheduled days."""
    current = start_date
    day_index = 0

    values = []
    while current <= end_date:
        if _is_scheduled_day(current, day_index, schedule_type, schedule_days):
            values.append((plan_id, current))
        current += timedelta(days=1)
        day_index += 1

    if values:
        # Batch insert
        for plan_id, scheduled_date in values:
            await dbexec(
                """
                INSERT INTO intervention_checkins (plan_id, scheduled_date, status)
                VALUES ($1, $2, 'pending')
                ON CONFLICT (plan_id, scheduled_date) DO NOTHING
                """,
                plan_id,
                scheduled_date,
            )


def _row_to_plan(row: Dict[str, Any]) -> InterventionPlan:
    """Convert database row to InterventionPlan."""
    return InterventionPlan(
        id=str(row["id"]),
        person_id=row["person_id"],
        intervention_type=InterventionType(row["intervention_type"]),
        intervention_name=row["intervention_name"],
        description=row.get("description"),
        schedule_type=ScheduleType(row["schedule_type"]),
        schedule_days=row.get("schedule_days"),
        target_per_day=row.get("target_per_day", 1),
        start_date=row["start_date"],
        end_date=row.get("end_date"),
        duration_days=row.get("duration_days"),
        target_symptom=row.get("target_symptom"),
        target_dosha=row.get("target_dosha"),
        baseline_severity=row.get("baseline_severity"),
        status=PlanStatus(row.get("status", "active")),
        total_scheduled=row.get("total_scheduled", 0),
        total_completed=row.get("total_completed", 0),
        current_streak=row.get("current_streak", 0),
        longest_streak=row.get("longest_streak", 0),
        recommendation_id=row.get("recommendation_id"),
        conversation_id=row.get("conversation_id"),
        created_at=row.get("created_at", datetime.utcnow()),
    )


# =============================================================================
# Check-ins
# =============================================================================

async def record_checkin(
    plan_id: str,
    completed: bool = True,
    completed_count: int = 1,
    notes: Optional[str] = None,
    mood_before: Optional[float] = None,
    mood_after: Optional[float] = None,
    checkin_date: Optional[date] = None,
) -> Optional[DailyCheckIn]:
    """
    Record a check-in for today (or specified date).

    Called when user reports they did (or didn't do) the intervention.
    """
    target_date = checkin_date or date.today()

    status = CheckInStatus.DONE if completed else CheckInStatus.SKIPPED
    if completed and completed_count < 1:
        status = CheckInStatus.PARTIAL

    # Update or insert check-in
    row = await dbfetch(
        """
        INSERT INTO intervention_checkins (
            plan_id, scheduled_date, status, completed_count,
            notes, mood_before, mood_after, checked_in_at
        ) VALUES ($1, $2, $3, $4, $5, $6, $7, NOW())
        ON CONFLICT (plan_id, scheduled_date) DO UPDATE
        SET status = $3,
            completed_count = $4,
            notes = COALESCE($5, intervention_checkins.notes),
            mood_before = COALESCE($6, intervention_checkins.mood_before),
            mood_after = COALESCE($7, intervention_checkins.mood_after),
            checked_in_at = NOW()
        RETURNING *
        """,
        plan_id,
        target_date,
        status.value,
        completed_count,
        notes,
        mood_before,
        mood_after,
        one=True,
    )

    if row:
        # Update plan stats
        await _update_plan_stats(plan_id)

        LOGGER.info(
            "[intervention] Check-in for %s on %s: %s",
            plan_id[:8], target_date, status.value
        )

        return DailyCheckIn(
            id=str(row["id"]),
            plan_id=plan_id,
            scheduled_date=row["scheduled_date"],
            status=CheckInStatus(row["status"]),
            completed_count=row.get("completed_count", 0),
            notes=row.get("notes"),
            mood_before=row.get("mood_before"),
            mood_after=row.get("mood_after"),
            checked_in_at=row.get("checked_in_at"),
            nudge_sent=row.get("nudge_sent", False),
            nudge_sent_at=row.get("nudge_sent_at"),
        )

    return None


async def _update_plan_stats(plan_id: str) -> None:
    """Update plan statistics after a check-in."""
    # Get all check-ins for this plan
    rows = await dbfetch(
        """
        SELECT scheduled_date, status FROM intervention_checkins
        WHERE plan_id = $1
        ORDER BY scheduled_date
        """,
        plan_id,
    )

    total_completed = 0
    current_streak = 0
    longest_streak = 0
    temp_streak = 0

    for row in rows or []:
        if row["status"] in ["done", "partial"]:
            total_completed += 1
            temp_streak += 1
            longest_streak = max(longest_streak, temp_streak)
        else:
            temp_streak = 0

    # Current streak is from the end
    for row in reversed(rows or []):
        if row["status"] in ["done", "partial"]:
            current_streak += 1
        else:
            break

    await dbexec(
        """
        UPDATE intervention_plans
        SET total_completed = $2,
            current_streak = $3,
            longest_streak = $4
        WHERE id = $1
        """,
        plan_id,
        total_completed,
        current_streak,
        longest_streak,
    )


async def get_today_checkins(person_id: str) -> List[Dict[str, Any]]:
    """
    Get all interventions that need check-in today.

    Used to show "Did you do X today?" prompts.
    """
    today = date.today()

    rows = await dbfetch(
        """
        SELECT p.id as plan_id, p.intervention_name, p.intervention_type,
               p.target_per_day, p.target_symptom,
               c.id as checkin_id, c.status, c.completed_count
        FROM intervention_plans p
        JOIN intervention_checkins c ON c.plan_id = p.id
        WHERE p.person_id = $1
          AND p.status = 'active'
          AND c.scheduled_date = $2
        """,
        person_id,
        today,
    )

    return [
        {
            "plan_id": str(row["plan_id"]),
            "checkin_id": str(row["checkin_id"]) if row.get("checkin_id") else None,
            "intervention_name": row["intervention_name"],
            "intervention_type": row["intervention_type"],
            "target_per_day": row.get("target_per_day", 1),
            "target_symptom": row.get("target_symptom"),
            "status": row.get("status", "pending"),
            "completed_count": row.get("completed_count", 0),
            "needs_checkin": row.get("status") == "pending",
        }
        for row in (rows or [])
    ]


# =============================================================================
# Progress & Stats
# =============================================================================

async def get_plan_progress(plan_id: str) -> Optional[PlanProgress]:
    """Get detailed progress for a plan."""
    plan_row = await dbfetch(
        "SELECT * FROM intervention_plans WHERE id = $1",
        plan_id,
        one=True,
    )

    if not plan_row:
        return None

    today = date.today()
    start = plan_row["start_date"]
    end = plan_row.get("end_date") or (start + timedelta(days=plan_row.get("duration_days", 14)))

    days_elapsed = (today - start).days
    days_remaining = max(0, (end - today).days)

    # Get check-in stats
    stats = await dbfetch(
        """
        SELECT
            COUNT(*) FILTER (WHERE status IN ('done', 'partial')) as completed,
            COUNT(*) FILTER (WHERE status = 'missed') as missed,
            COUNT(*) as total
        FROM intervention_checkins
        WHERE plan_id = $1 AND scheduled_date <= $2
        """,
        plan_id,
        today,
        one=True,
    )

    total_so_far = stats["total"] if stats else 0
    completed = stats["completed"] if stats else 0
    missed = stats["missed"] if stats else 0

    adherence = completed / total_so_far if total_so_far > 0 else 0.0

    # Get next scheduled day
    next_row = await dbfetch(
        """
        SELECT scheduled_date FROM intervention_checkins
        WHERE plan_id = $1 AND scheduled_date > $2 AND status = 'pending'
        ORDER BY scheduled_date LIMIT 1
        """,
        plan_id,
        today,
        one=True,
    )

    # Check if today needs check-in
    today_row = await dbfetch(
        """
        SELECT status FROM intervention_checkins
        WHERE plan_id = $1 AND scheduled_date = $2
        """,
        plan_id,
        today,
        one=True,
    )

    # Calculate symptom improvement if we have baseline
    symptom_improvement = None
    if plan_row.get("baseline_severity") and plan_row.get("target_symptom"):
        symptom_improvement = await _calculate_symptom_improvement(
            plan_row["person_id"],
            plan_row["target_symptom"],
            plan_row["baseline_severity"],
            start,
        )

    return PlanProgress(
        plan_id=plan_id,
        plan_name=plan_row["intervention_name"],
        status=plan_row.get("status", "active"),
        days_elapsed=days_elapsed,
        days_remaining=days_remaining,
        adherence_rate=round(adherence, 2),
        total_scheduled=plan_row.get("total_scheduled", 0),
        total_completed=completed,
        total_missed=missed,
        current_streak=plan_row.get("current_streak", 0),
        longest_streak=plan_row.get("longest_streak", 0),
        symptom_improvement=symptom_improvement,
        next_scheduled=next_row["scheduled_date"] if next_row else None,
        needs_checkin_today=today_row["status"] == "pending" if today_row else False,
    )


async def _calculate_symptom_improvement(
    person_id: str,
    symptom: str,
    baseline: float,
    since: date,
) -> Optional[float]:
    """Calculate symptom improvement since baseline."""
    # Get recent symptom logs
    row = await dbfetch(
        """
        SELECT AVG(severity) as avg_severity
        FROM symptom_log
        WHERE person_id = $1
          AND symptom_type ILIKE $2
          AND occurred_at > $3
        """,
        person_id,
        f"%{symptom}%",
        since,
        one=True,
    )

    if not row or row["avg_severity"] is None:
        return None

    current = float(row["avg_severity"])
    if baseline == 0:
        return None

    # Negative = improvement (lower severity)
    improvement = ((baseline - current) / baseline) * 100
    return round(improvement, 1)


async def get_active_plans(person_id: str) -> List[InterventionPlan]:
    """Get all active intervention plans for a user."""
    rows = await dbfetch(
        """
        SELECT * FROM intervention_plans
        WHERE person_id = $1 AND status = 'active'
        ORDER BY start_date DESC
        """,
        person_id,
    )

    return [_row_to_plan(row) for row in (rows or [])]


async def get_plan(plan_id: str) -> Optional[InterventionPlan]:
    """Get a specific plan by ID."""
    row = await dbfetch(
        "SELECT * FROM intervention_plans WHERE id = $1",
        plan_id,
        one=True,
    )
    return _row_to_plan(row) if row else None


# =============================================================================
# Plan Lifecycle
# =============================================================================

async def pause_plan(plan_id: str) -> bool:
    """Pause an active plan."""
    await dbexec(
        "UPDATE intervention_plans SET status = 'paused' WHERE id = $1",
        plan_id,
    )
    return True


async def resume_plan(plan_id: str) -> bool:
    """Resume a paused plan."""
    await dbexec(
        "UPDATE intervention_plans SET status = 'active' WHERE id = $1",
        plan_id,
    )
    return True


async def complete_plan(plan_id: str) -> bool:
    """Mark a plan as completed."""
    await dbexec(
        "UPDATE intervention_plans SET status = 'completed' WHERE id = $1",
        plan_id,
    )
    return True


async def abandon_plan(plan_id: str, reason: Optional[str] = None) -> bool:
    """Abandon a plan (user decided to stop)."""
    await dbexec(
        """
        UPDATE intervention_plans
        SET status = 'abandoned', notes = COALESCE($2, notes)
        WHERE id = $1
        """,
        plan_id,
        reason,
    )
    return True


# =============================================================================
# Missed Day Processing
# =============================================================================

async def mark_missed_checkins() -> int:
    """
    Mark pending check-ins from past days as missed.

    Should be run daily as a background job.
    """
    yesterday = date.today() - timedelta(days=1)

    result = await dbfetch(
        """
        UPDATE intervention_checkins
        SET status = 'missed'
        WHERE status = 'pending' AND scheduled_date < $1
        RETURNING plan_id
        """,
        yesterday,
    )

    # Update stats for affected plans
    plan_ids = set(row["plan_id"] for row in (result or []))
    for plan_id in plan_ids:
        await _update_plan_stats(str(plan_id))

    count = len(result) if result else 0
    if count > 0:
        LOGGER.info("[intervention] Marked %d check-ins as missed", count)

    return count


# =============================================================================
# Outcome Correlation
# =============================================================================

async def correlate_plan_outcomes(plan_id: str) -> Dict[str, Any]:
    """
    Analyze correlation between adherence and symptom outcomes.

    Called when plan completes or periodically during plan.
    """
    plan = await get_plan(plan_id)
    if not plan:
        return {"error": "Plan not found"}

    progress = await get_plan_progress(plan_id)
    if not progress:
        return {"error": "Could not get progress"}

    result = {
        "plan_id": plan_id,
        "intervention_name": plan.intervention_name,
        "adherence_rate": progress.adherence_rate,
        "total_completed": progress.total_completed,
        "total_scheduled": progress.total_scheduled,
        "symptom_improvement": progress.symptom_improvement,
        "effectiveness_score": None,
        "recommendation": None,
    }

    # Calculate effectiveness score
    # High adherence + symptom improvement = effective
    if progress.symptom_improvement is not None:
        adherence_factor = progress.adherence_rate
        improvement_factor = max(0, progress.symptom_improvement) / 100

        # Weighted score: adherence matters, but improvement matters more
        effectiveness = (adherence_factor * 0.3) + (improvement_factor * 0.7)
        result["effectiveness_score"] = round(effectiveness, 2)

        # Generate recommendation
        if effectiveness > 0.6:
            result["recommendation"] = "continue"
            result["message"] = f"{plan.intervention_name} is working well for you. Consider making it a regular habit."
        elif effectiveness > 0.3:
            result["recommendation"] = "adjust"
            result["message"] = f"{plan.intervention_name} shows some benefit. Try increasing frequency or duration."
        else:
            if progress.adherence_rate < 0.5:
                result["recommendation"] = "simplify"
                result["message"] = f"Adherence was low. Consider a simpler version of {plan.intervention_name}."
            else:
                result["recommendation"] = "try_different"
                result["message"] = f"{plan.intervention_name} may not be the best fit. Let's try something else."

    # Store outcome in intervention_outcomes for learning
    if result["effectiveness_score"] is not None:
        from sakhi.apps.api.services.learning.outcomes import log_intervention_outcome

        await log_intervention_outcome(
            person_id=plan.person_id,
            intervention_type=plan.intervention_type.value,
            intervention_name=plan.intervention_name,
            was_effective=result["effectiveness_score"] > 0.5,
            effectiveness_score=result["effectiveness_score"],
            symptom_addressed=plan.target_symptom,
            related_dosha=plan.target_dosha,
            notes=f"Adherence: {progress.adherence_rate:.0%}, Improvement: {progress.symptom_improvement or 0:.1f}%",
        )

    return result


__all__ = [
    "ScheduleType",
    "InterventionType",
    "PlanStatus",
    "CheckInStatus",
    "InterventionPlan",
    "DailyCheckIn",
    "CreatePlanRequest",
    "PlanProgress",
    "create_intervention_plan",
    "record_checkin",
    "get_today_checkins",
    "get_plan_progress",
    "get_active_plans",
    "get_plan",
    "pause_plan",
    "resume_plan",
    "complete_plan",
    "abandon_plan",
    "mark_missed_checkins",
    "correlate_plan_outcomes",
]
