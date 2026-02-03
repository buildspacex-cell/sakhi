"""
Mission Service - Business logic for long-running missions

Orchestrates between:
- Repository (database operations)
- Decomposer (LLM-based planning)
- Scheduler (action execution)

This is the main entry point for mission operations.
"""

from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Any, Dict, List, Optional
from uuid import UUID

from .repository import MissionRepository
from .decomposer import (
    decompose_mission,
    decompose_first_week,
    calculate_action_dates,
    generate_plan_document,
)
from .models import (
    Mission, MissionCreate, MissionPhase, WeeklyPlan,
    ScheduledAction, MissionCheckpoint, MissionData,
    MissionSummary, TodayAction, MissionCategory,
    MissionDecomposition, MissionWithDetails
)

LOGGER = logging.getLogger(__name__)


class MissionService:
    """
    High-level mission operations.

    Handles the full lifecycle:
    1. Create mission from goal
    2. Decompose into phases and weeks
    3. Schedule actions
    4. Track progress
    5. Adapt based on outcomes
    """

    # ========================================================================
    # MISSION LIFECYCLE
    # ========================================================================

    @staticmethod
    async def create_from_goal(
        person_id: UUID,
        goal: str,
        category: Optional[MissionCategory] = None,
        target_weeks: int = 8,
        context: Optional[Dict[str, Any]] = None,
    ) -> Mission:
        """
        Create a new mission from a natural language goal.

        This is the primary entry point for starting a mission:
        1. Decomposes the goal into phases/weeks/actions
        2. Creates the mission record
        3. Creates all phases
        4. Creates first week's plan with scheduled actions

        Args:
            person_id: User's ID
            goal: Natural language goal (e.g., "Build my Twitter brand")
            category: Optional category hint
            target_weeks: How long to plan for
            context: Additional context for personalization

        Returns:
            The created Mission with plan populated
        """
        # Step 1: Decompose the goal using LLM
        LOGGER.info("[mission] Decomposing goal: %s", goal[:50])
        decomposition = await decompose_mission(
            goal=goal,
            person_id=person_id,
            category=category,
            context=context,
            target_weeks=target_weeks,
        )

        # Step 2: Generate plan document if not provided
        if not decomposition.plan_document:
            decomposition.plan_document = await generate_plan_document(decomposition)

        # Step 3: Create mission record
        mission_data = MissionCreate(
            title=decomposition.title,
            description=decomposition.description,
            category=decomposition.category,
            target_end_date=date.today() + timedelta(weeks=decomposition.target_weeks),
            success_criteria=decomposition.success_criteria,
        )

        mission = await MissionRepository.create_mission(
            person_id=person_id,
            data=mission_data,
            plan_document=decomposition.plan_document,
        )

        LOGGER.info("[mission] Created mission %s: %s", mission.id, mission.title)

        # Step 4: Create phases
        current_date = date.today()
        for phase_plan in decomposition.phases:
            phase_end = current_date + timedelta(weeks=phase_plan.duration_weeks)

            await MissionRepository.create_phase(
                mission_id=mission.id,
                phase_number=phase_plan.phase_number,
                name=phase_plan.name,
                objective=phase_plan.objective,
                start_date=current_date,
                target_end_date=phase_end,
                expected_outcomes=phase_plan.expected_outcomes,
                requires_approval=phase_plan.phase_number > 1,  # First phase auto-approved
            )

            current_date = phase_end + timedelta(days=1)

        # Step 5: Approve and activate first phase
        phases = await MissionRepository.get_phases(mission.id)
        if phases:
            await MissionRepository.approve_phase(phases[0].id, approved_by="auto")

        # Step 6: Create first week's plan and actions
        if decomposition.phases and decomposition.phases[0].weeks:
            first_week = decomposition.phases[0].weeks[0]
            await MissionService._create_week_plan(
                mission_id=mission.id,
                phase_id=phases[0].id if phases else None,
                week_plan=first_week,
                person_id=person_id,
            )

        return mission

    @staticmethod
    async def _create_week_plan(
        mission_id: UUID,
        phase_id: Optional[UUID],
        week_plan,  # WeekPlan from decomposer
        person_id: UUID,
    ) -> WeeklyPlan:
        """Create a weekly plan with scheduled actions."""
        # Calculate week start (next Monday if not already Monday)
        today = date.today()
        days_until_monday = (7 - today.weekday()) % 7
        week_start = today + timedelta(days=days_until_monday) if days_until_monday else today

        weekly = await MissionRepository.create_weekly_plan(
            mission_id=mission_id,
            phase_id=phase_id,
            week_number=week_plan.week_number,
            week_start=week_start,
            objectives=week_plan.objectives,
            tasks={"actions": [a.model_dump() for a in week_plan.actions]},
        )

        # Create scheduled actions
        action_dates = calculate_action_dates(week_plan.actions, week_start)
        for action_data in action_dates:
            await MissionRepository.create_action(
                mission_id=mission_id,
                person_id=person_id,
                weekly_plan_id=weekly.id,
                action_type=action_data["action_type"],
                description=action_data["description"],
                scheduled_date=action_data["scheduled_date"],
                scheduled_time=action_data["scheduled_time"],
                instructions=action_data["instructions"],
            )

        LOGGER.info(
            "[mission] Created week %d plan with %d actions",
            week_plan.week_number,
            len(action_dates),
        )

        return weekly

    # ========================================================================
    # MISSION QUERIES
    # ========================================================================

    @staticmethod
    async def get_mission(mission_id: UUID) -> Optional[Mission]:
        """Get a mission by ID."""
        return await MissionRepository.get_mission(mission_id)

    @staticmethod
    async def get_active_missions(person_id: UUID) -> List[MissionSummary]:
        """Get all active missions for a user with summary info."""
        return await MissionRepository.get_active_missions(person_id)

    @staticmethod
    async def get_mission_details(mission_id: UUID) -> Optional[MissionWithDetails]:
        """Get full mission details including phases and current week."""
        mission = await MissionRepository.get_mission(mission_id)
        if not mission:
            return None

        phases = await MissionRepository.get_phases(mission_id)
        current_week = await MissionRepository.get_current_week(mission_id)

        # Get upcoming actions (next 7 days)
        # For now, just get today's actions from the repository
        today_actions = await MissionRepository.get_todays_actions(mission.person_id)
        upcoming = [a for a in today_actions if str(a.mission_id) == str(mission_id)]

        # Get recent checkpoints
        # TODO: Add repository method for this
        checkpoints: List[MissionCheckpoint] = []

        return MissionWithDetails(
            mission=mission,
            phases=phases,
            current_week=current_week,
            upcoming_actions=upcoming,
            recent_checkpoints=checkpoints,
        )

    @staticmethod
    async def get_todays_actions(person_id: UUID) -> List[TodayAction]:
        """Get all scheduled actions for today across all missions."""
        return await MissionRepository.get_todays_actions(person_id)

    # ========================================================================
    # PROGRESS TRACKING
    # ========================================================================

    @staticmethod
    async def record_action_outcome(
        action_id: UUID,
        success: bool,
        outcome: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
    ) -> ScheduledAction:
        """
        Record the outcome of a completed action.

        Called after an action executes (whether successful or not).
        Updates mission metrics and health based on outcomes.
        """
        action = await MissionRepository.complete_action(
            action_id=action_id,
            success=success,
            outcome=outcome,
            error_message=error_message,
        )

        # Update mission metrics
        if action:
            await MissionService._update_mission_metrics(action.mission_id)

        return action

    @staticmethod
    async def _update_mission_metrics(mission_id: UUID) -> None:
        """Recalculate mission progress and health based on action outcomes."""
        mission = await MissionRepository.get_mission(mission_id)
        if not mission:
            return

        # Get all actions for this mission to calculate completion rate
        # For now, simplified - just update based on completed actions
        # TODO: More sophisticated metrics calculation

        LOGGER.debug("[mission] Updated metrics for mission %s", mission_id)

    @staticmethod
    async def create_checkpoint(
        mission_id: UUID,
        checkpoint_type: str,
        analysis: Optional[str] = None,
    ) -> MissionCheckpoint:
        """
        Create a progress checkpoint.

        Checkpoints capture the state of a mission at a point in time.
        Used for:
        - Daily quick checks
        - Weekly reviews
        - Monthly assessments
        - Milestone celebrations
        """
        mission = await MissionRepository.get_mission(mission_id)
        if not mission:
            raise ValueError(f"Mission {mission_id} not found")

        metrics_snapshot = {
            "progress_pct": mission.progress_pct,
            "health": mission.health,
            "metrics": mission.metrics,
        }

        return await MissionRepository.create_checkpoint(
            mission_id=mission_id,
            checkpoint_type=checkpoint_type,
            metrics_snapshot=metrics_snapshot,
            progress_pct=mission.progress_pct,
            health=mission.health.value if hasattr(mission.health, 'value') else str(mission.health),
            analysis=analysis,
        )

    # ========================================================================
    # WEEKLY REVIEW
    # ========================================================================

    @staticmethod
    async def complete_weekly_review(
        weekly_plan_id: UUID,
        review_notes: str,
        what_worked: List[str],
        what_didnt: List[str],
        adjustments: List[str],
    ) -> WeeklyPlan:
        """
        Complete the weekly review process.

        Reviews are a key part of adaptive planning:
        1. Reflect on what worked
        2. Identify what didn't
        3. Make adjustments for next week
        4. Optionally generate next week's plan
        """
        return await MissionRepository.complete_weekly_review(
            weekly_plan_id=weekly_plan_id,
            review_notes=review_notes,
            what_worked=what_worked,
            what_didnt=what_didnt,
            adjustments=adjustments,
        )

    @staticmethod
    async def generate_next_week(
        mission_id: UUID,
        person_id: UUID,
    ) -> Optional[WeeklyPlan]:
        """
        Generate the next week's plan based on progress.

        Called after weekly review or when a week ends.
        Uses learnings from previous weeks to adapt.
        """
        mission = await MissionRepository.get_mission(mission_id)
        if not mission:
            return None

        active_phase = await MissionRepository.get_active_phase(mission_id)
        if not active_phase:
            LOGGER.warning("[mission] No active phase for mission %s", mission_id)
            return None

        # Get current week to determine next week number
        current = await MissionRepository.get_current_week(mission_id)
        next_week_num = (current.week_number + 1) if current else 1

        # Generate detailed plan for next week
        week_plan = await decompose_first_week(
            mission_title=mission.title,
            mission_description=mission.description or "",
            phase_objective=active_phase.objective or "",
            person_id=person_id,
            context={"week_number": next_week_num},
        )
        week_plan.week_number = next_week_num

        return await MissionService._create_week_plan(
            mission_id=mission_id,
            phase_id=active_phase.id,
            week_plan=week_plan,
            person_id=person_id,
        )

    # ========================================================================
    # DATA RECORDING
    # ========================================================================

    @staticmethod
    async def record_data(
        person_id: UUID,
        record_type: str,
        data: Dict[str, Any],
        mission_id: Optional[UUID] = None,
        record_date: Optional[date] = None,
        source: Optional[str] = None,
    ) -> MissionData:
        """
        Record generic mission data.

        This is the flexible data ingestion point for any mission-related data:
        - Expenses: {"category": "food", "amount": 15.50, "vendor": "..."}
        - Tweets: {"content": "...", "engagement": {...}}
        - Workouts: {"type": "run", "duration_mins": 30, "distance_km": 5}
        - Lessons: {"topic": "...", "notes": "..."}

        The record_type determines how the data is interpreted and aggregated.
        """
        return await MissionRepository.record_data(
            person_id=person_id,
            mission_id=mission_id,
            record_type=record_type,
            data=data,
            record_date=record_date,
            source=source,
        )

    @staticmethod
    async def get_mission_data(
        mission_id: UUID,
        record_type: Optional[str] = None,
        since: Optional[date] = None,
    ) -> List[MissionData]:
        """Get mission data records with optional filtering."""
        return await MissionRepository.get_mission_data(
            mission_id=mission_id,
            record_type=record_type,
            since=since,
        )

    @staticmethod
    async def get_expense_summary(
        person_id: UUID,
        since: Optional[date] = None,
        mission_id: Optional[UUID] = None,
    ) -> Dict[str, Any]:
        """Get aggregated expense data by category."""
        return await MissionRepository.aggregate_expenses(
            person_id=person_id,
            since=since,
            mission_id=mission_id,
        )

    # ========================================================================
    # PHASE MANAGEMENT
    # ========================================================================

    @staticmethod
    async def approve_phase(
        phase_id: UUID,
        approved_by: str = "user",
    ) -> MissionPhase:
        """
        Approve a phase to begin.

        Phases after the first require explicit approval as a checkpoint.
        This is the human-in-the-loop for major mission milestones.
        """
        return await MissionRepository.approve_phase(
            phase_id=phase_id,
            approved_by=approved_by,
        )


__all__ = ["MissionService"]
