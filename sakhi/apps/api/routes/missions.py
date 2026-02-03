"""
Mission API Routes - Endpoints for long-running task management

Provides RESTful endpoints for:
- Creating missions from goals
- Viewing mission progress
- Managing phases and weekly plans
- Tracking actions and recording data
"""

from __future__ import annotations

from datetime import date
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from sakhi.apps.api.services.missions import (
    MissionService,
    Mission,
    MissionSummary,
    MissionPhase,
    WeeklyPlan,
    ScheduledAction,
    TodayAction,
    MissionData,
    MissionCategory,
    MissionWithDetails,
)

router = APIRouter(prefix="/missions", tags=["missions"])


# ============================================================================
# Request/Response Models
# ============================================================================

class CreateMissionRequest(BaseModel):
    """Request to create a new mission from a goal"""
    goal: str = Field(min_length=3, description="Natural language goal")
    category: Optional[MissionCategory] = None
    target_weeks: int = Field(default=8, ge=1, le=52)
    context: Optional[Dict[str, Any]] = None


class CreateMissionResponse(BaseModel):
    """Response after mission creation"""
    id: UUID
    title: str
    description: Optional[str]
    category: Optional[str]
    plan_document: Optional[str]
    phases_count: int
    first_week_actions: int


class RecordDataRequest(BaseModel):
    """Request to record mission data"""
    record_type: str = Field(min_length=1, description="Type of data (expense, workout, tweet, etc.)")
    data: Dict[str, Any] = Field(description="The data payload")
    mission_id: Optional[UUID] = None
    record_date: Optional[date] = None
    source: Optional[str] = None


class RecordActionOutcomeRequest(BaseModel):
    """Request to record action outcome"""
    success: bool
    outcome: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None


class WeeklyReviewRequest(BaseModel):
    """Request to complete weekly review"""
    review_notes: str
    what_worked: List[str] = Field(default_factory=list)
    what_didnt: List[str] = Field(default_factory=list)
    adjustments: List[str] = Field(default_factory=list)


class ApprovePhaseRequest(BaseModel):
    """Request to approve a phase"""
    approved_by: str = Field(default="user")


class ExpenseSummaryResponse(BaseModel):
    """Expense summary response"""
    by_category: List[Dict[str, Any]]
    total: float


# ============================================================================
# Mission Lifecycle Endpoints
# ============================================================================

import logging

LOGGER = logging.getLogger(__name__)


@router.post("", response_model=CreateMissionResponse, status_code=status.HTTP_201_CREATED)
async def create_mission(
    person_id: str,
    body: CreateMissionRequest,
) -> CreateMissionResponse:
    """
    Create a new mission from a natural language goal.

    This endpoint:
    1. Decomposes the goal into phases and weekly plans using AI
    2. Creates the mission with a structured plan
    3. Sets up the first week's scheduled actions

    Example goals:
    - "Build my Twitter brand and get to 1000 followers"
    - "Learn Python and build 3 projects"
    - "Save $5000 for emergency fund"
    """
    try:
        person_uuid = UUID(person_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid person_id format"
        ) from exc

    try:
        mission = await MissionService.create_from_goal(
            person_id=person_uuid,
            goal=body.goal,
            category=body.category,
            target_weeks=body.target_weeks,
            context=body.context,
        )
    except Exception as e:
        LOGGER.exception("[missions] Failed to create mission: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create mission: {str(e)}"
        ) from e

    # Get phase and action counts for response
    phases = await MissionService.get_mission_details(mission.id)
    phases_count = len(phases.phases) if phases else 0
    actions_count = len(phases.upcoming_actions) if phases else 0

    return CreateMissionResponse(
        id=mission.id,
        title=mission.title,
        description=mission.description,
        category=mission.category,
        plan_document=mission.plan_document,
        phases_count=phases_count,
        first_week_actions=actions_count,
    )


@router.get("", response_model=List[MissionSummary])
async def list_missions(person_id: str) -> List[MissionSummary]:
    """
    Get all active missions for a person.

    Returns summary information including:
    - Progress percentage
    - Health status
    - Current phase
    - Next scheduled action
    """
    try:
        person_uuid = UUID(person_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid person_id format"
        ) from exc

    return await MissionService.get_active_missions(person_uuid)


@router.get("/{mission_id}", response_model=MissionWithDetails)
async def get_mission(mission_id: UUID) -> MissionWithDetails:
    """
    Get full mission details including phases and current week.
    """
    result = await MissionService.get_mission_details(mission_id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mission not found"
        )
    return result


@router.get("/{mission_id}/plan")
async def get_mission_plan(mission_id: UUID) -> Dict[str, Any]:
    """
    Get the mission's plan document (markdown format).
    """
    mission = await MissionService.get_mission(mission_id)
    if not mission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mission not found"
        )
    return {
        "mission_id": mission_id,
        "title": mission.title,
        "plan_document": mission.plan_document,
    }


# ============================================================================
# Today's Focus
# ============================================================================

@router.get("/today/actions", response_model=List[TodayAction])
async def get_todays_actions(person_id: str) -> List[TodayAction]:
    """
    Get all scheduled actions for today across all missions.

    This is the "daily focus" view showing what needs to be done today.
    """
    try:
        person_uuid = UUID(person_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid person_id format"
        ) from exc

    return await MissionService.get_todays_actions(person_uuid)


# ============================================================================
# Action Management
# ============================================================================

@router.post("/actions/{action_id}/outcome", response_model=ScheduledAction)
async def record_action_outcome(
    action_id: UUID,
    body: RecordActionOutcomeRequest,
) -> ScheduledAction:
    """
    Record the outcome of a completed action.

    Call this after an action is executed (whether successful or not).
    This updates mission metrics and triggers adaptive planning.
    """
    return await MissionService.record_action_outcome(
        action_id=action_id,
        success=body.success,
        outcome=body.outcome,
        error_message=body.error_message,
    )


# ============================================================================
# Phase Management
# ============================================================================

@router.post("/phases/{phase_id}/approve", response_model=MissionPhase)
async def approve_phase(
    phase_id: UUID,
    body: ApprovePhaseRequest,
) -> MissionPhase:
    """
    Approve a phase to begin execution.

    Phases after the first require explicit approval as a checkpoint.
    This is the human-in-the-loop for major mission milestones.
    """
    return await MissionService.approve_phase(
        phase_id=phase_id,
        approved_by=body.approved_by,
    )


# ============================================================================
# Weekly Planning
# ============================================================================

@router.post("/weekly/{weekly_plan_id}/review", response_model=WeeklyPlan)
async def complete_weekly_review(
    weekly_plan_id: UUID,
    body: WeeklyReviewRequest,
) -> WeeklyPlan:
    """
    Complete the weekly review process.

    Weekly reviews are key to adaptive planning:
    1. Reflect on what worked
    2. Identify what didn't
    3. Make adjustments for next week
    """
    return await MissionService.complete_weekly_review(
        weekly_plan_id=weekly_plan_id,
        review_notes=body.review_notes,
        what_worked=body.what_worked,
        what_didnt=body.what_didnt,
        adjustments=body.adjustments,
    )


@router.post("/{mission_id}/next-week", response_model=WeeklyPlan)
async def generate_next_week(
    mission_id: UUID,
    person_id: str,
) -> WeeklyPlan:
    """
    Generate the next week's plan based on progress.

    Uses learnings from previous weeks to adapt the upcoming plan.
    """
    try:
        person_uuid = UUID(person_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid person_id format"
        ) from exc

    result = await MissionService.generate_next_week(
        mission_id=mission_id,
        person_id=person_uuid,
    )
    if not result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not generate next week (no active phase?)"
        )
    return result


# ============================================================================
# Data Recording
# ============================================================================

@router.post("/data", response_model=MissionData, status_code=status.HTTP_201_CREATED)
async def record_data(
    person_id: str,
    body: RecordDataRequest,
) -> MissionData:
    """
    Record generic mission data.

    This is the flexible data ingestion endpoint for any mission-related data:
    - Expenses: {"category": "food", "amount": 15.50, "vendor": "..."}
    - Tweets: {"content": "...", "engagement": {...}}
    - Workouts: {"type": "run", "duration_mins": 30}
    - Lessons: {"topic": "...", "notes": "..."}

    The record_type determines how data is aggregated and reported.
    """
    try:
        person_uuid = UUID(person_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid person_id format"
        ) from exc

    return await MissionService.record_data(
        person_id=person_uuid,
        record_type=body.record_type,
        data=body.data,
        mission_id=body.mission_id,
        record_date=body.record_date,
        source=body.source,
    )


@router.get("/{mission_id}/data", response_model=List[MissionData])
async def get_mission_data(
    mission_id: UUID,
    record_type: Optional[str] = None,
    since: Optional[date] = None,
) -> List[MissionData]:
    """
    Get mission data records with optional filtering.
    """
    return await MissionService.get_mission_data(
        mission_id=mission_id,
        record_type=record_type,
        since=since,
    )


@router.get("/data/expenses", response_model=ExpenseSummaryResponse)
async def get_expense_summary(
    person_id: str,
    since: Optional[date] = None,
    mission_id: Optional[UUID] = None,
) -> ExpenseSummaryResponse:
    """
    Get aggregated expense data by category.

    Useful for budget tracking missions.
    """
    try:
        person_uuid = UUID(person_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid person_id format"
        ) from exc

    result = await MissionService.get_expense_summary(
        person_id=person_uuid,
        since=since,
        mission_id=mission_id,
    )
    return ExpenseSummaryResponse(**result)


# ============================================================================
# Checkpoints
# ============================================================================

@router.post("/{mission_id}/checkpoint")
async def create_checkpoint(
    mission_id: UUID,
    checkpoint_type: str = "manual",
    analysis: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Create a progress checkpoint.

    Checkpoints capture mission state at a point in time for:
    - Daily quick checks
    - Weekly reviews
    - Monthly assessments
    - Milestone celebrations
    """
    checkpoint = await MissionService.create_checkpoint(
        mission_id=mission_id,
        checkpoint_type=checkpoint_type,
        analysis=analysis,
    )
    return {
        "id": checkpoint.id,
        "checkpoint_type": checkpoint.checkpoint_type,
        "progress_pct": checkpoint.progress_pct,
        "health": checkpoint.health,
        "created_at": checkpoint.created_at,
    }


__all__ = ["router"]
