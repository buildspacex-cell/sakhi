"""
Mission Models - Pydantic schemas for long-running tasks
"""

from datetime import date, time, datetime
from typing import Optional, List, Any
from uuid import UUID
from pydantic import BaseModel, Field, field_validator
from enum import Enum
import json


# ============================================================================
# Enums
# ============================================================================

class MissionStatus(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


class MissionHealth(str, Enum):
    ON_TRACK = "on_track"
    AT_RISK = "at_risk"
    BEHIND = "behind"
    AHEAD = "ahead"


class PhaseStatus(str, Enum):
    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"
    SKIPPED = "skipped"


class ActionStatus(str, Enum):
    SCHEDULED = "scheduled"
    TRIGGERED = "triggered"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class TriggerType(str, Enum):
    SCHEDULED = "scheduled"
    RECURRING = "recurring"
    CONDITION = "condition"
    EVENT = "event"
    MANUAL = "manual"


class MissionCategory(str, Enum):
    CAREER = "career"
    HEALTH = "health"
    LEARNING = "learning"
    CREATIVE = "creative"
    RELATIONSHIPS = "relationships"
    FINANCE = "finance"


# ============================================================================
# Core Models
# ============================================================================

class MissionCreate(BaseModel):
    """Request to create a new mission"""
    title: str
    description: Optional[str] = None
    category: Optional[MissionCategory] = None
    target_end_date: Optional[date] = None
    success_criteria: Optional[dict] = None


def _parse_json_field(v: Any) -> Optional[Any]:
    """Parse a JSON field that might be a string or already parsed."""
    if v is None:
        return None
    if isinstance(v, (dict, list)):
        return v
    if isinstance(v, str):
        try:
            return json.loads(v)
        except json.JSONDecodeError:
            return None
    return None


class Mission(BaseModel):
    """A long-running mission (weeks to months)"""
    id: UUID
    person_id: UUID
    title: str
    description: Optional[str] = None
    category: Optional[str] = None
    success_criteria: Optional[dict] = None
    plan_document: Optional[str] = None
    target_end_date: Optional[date] = None
    actual_end_date: Optional[date] = None
    status: MissionStatus = MissionStatus.ACTIVE
    health: MissionHealth = MissionHealth.ON_TRACK
    strategy_notes: Optional[str] = None
    lessons_learned: Optional[dict] = None
    progress_pct: int = 0
    metrics: Optional[dict] = None
    conversation_id: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime

    @field_validator("success_criteria", "lessons_learned", "metrics", mode="before")
    @classmethod
    def parse_json_fields(cls, v: Any) -> Optional[dict]:
        return _parse_json_field(v)

    class Config:
        from_attributes = True


class MissionPhase(BaseModel):
    """A multi-week chunk within a mission"""
    id: UUID
    mission_id: UUID
    phase_number: int
    name: str
    objective: Optional[str] = None
    start_date: date
    target_end_date: date
    actual_end_date: Optional[date] = None
    status: PhaseStatus = PhaseStatus.PENDING
    expected_outcomes: Optional[Any] = None  # JSONB can be list or dict
    actual_outcomes: Optional[Any] = None    # JSONB can be list or dict
    requires_approval: bool = True
    approved_at: Optional[datetime] = None
    approved_by: Optional[str] = None
    adjustments_made: Optional[List[str]] = None
    created_at: datetime
    updated_at: datetime

    @field_validator("expected_outcomes", "actual_outcomes", mode="before")
    @classmethod
    def parse_json_fields(cls, v: Any) -> Optional[Any]:
        return _parse_json_field(v)

    class Config:
        from_attributes = True


class WeeklyPlan(BaseModel):
    """Concrete plan for a 7-day period"""
    id: UUID
    mission_id: UUID
    phase_id: Optional[UUID] = None
    week_number: int
    week_start: date
    week_end: date
    objectives: Optional[List[str]] = None
    tasks: Optional[dict] = None
    status: str = "planned"
    review_completed: bool = False
    review_notes: Optional[str] = None
    what_worked: Optional[List[str]] = None
    what_didnt: Optional[List[str]] = None
    adjustments_for_next: Optional[List[str]] = None
    created_at: datetime
    updated_at: datetime

    @field_validator("tasks", mode="before")
    @classmethod
    def parse_json_fields(cls, v: Any) -> Optional[dict]:
        return _parse_json_field(v)

    class Config:
        from_attributes = True


class ScheduledAction(BaseModel):
    """Individual task to execute"""
    id: UUID
    mission_id: UUID
    weekly_plan_id: Optional[UUID] = None
    person_id: UUID
    action_type: str
    description: str
    instructions: Optional[dict] = None
    scheduled_date: date
    scheduled_time: Optional[time] = None
    deadline: Optional[datetime] = None
    trigger_type: TriggerType = TriggerType.SCHEDULED
    cron_expression: Optional[str] = None
    trigger_condition: Optional[str] = None
    status: ActionStatus = ActionStatus.SCHEDULED
    agent_session_id: Optional[UUID] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    outcome: Optional[dict] = None
    success: Optional[bool] = None
    error_message: Optional[str] = None
    effectiveness_score: Optional[float] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    @field_validator("instructions", "outcome", mode="before")
    @classmethod
    def parse_json_fields(cls, v: Any) -> Optional[dict]:
        return _parse_json_field(v)

    class Config:
        from_attributes = True


class MissionCheckpoint(BaseModel):
    """Progress snapshot"""
    id: UUID
    mission_id: UUID
    checkpoint_date: date
    checkpoint_type: str  # daily, weekly, monthly, milestone
    metrics_snapshot: Optional[dict] = None
    progress_pct: Optional[int] = None
    health: Optional[str] = None
    analysis: Optional[str] = None
    recommendations: Optional[List[str]] = None
    risks: Optional[List[str]] = None
    adjustments_approved: Optional[dict] = None
    user_feedback: Optional[str] = None
    created_at: datetime

    @field_validator("metrics_snapshot", "adjustments_approved", mode="before")
    @classmethod
    def parse_json_fields(cls, v: Any) -> Optional[dict]:
        return _parse_json_field(v)

    class Config:
        from_attributes = True


class MissionData(BaseModel):
    """Generic data record for any mission type"""
    id: UUID
    mission_id: Optional[UUID] = None
    person_id: UUID
    record_type: str  # 'expense', 'tweet', 'workout', 'lesson', etc.
    data: dict  # Schema-free JSONB
    record_date: Optional[date] = None
    source: Optional[str] = None  # 'email', 'manual', 'api', 'vision_loop'
    created_at: datetime

    @field_validator("data", mode="before")
    @classmethod
    def parse_json_fields(cls, v: Any) -> dict:
        result = _parse_json_field(v)
        return result if result is not None else {}

    class Config:
        from_attributes = True


# ============================================================================
# Decomposition Models (for LLM output)
# ============================================================================

class ActionPlan(BaseModel):
    """Single action within a week"""
    action_type: str
    description: str
    scheduled_day: str  # monday, tuesday, etc.
    scheduled_time: Optional[str] = None  # "09:00"
    instructions: Optional[dict] = None


class WeekPlan(BaseModel):
    """Week plan generated by decomposer"""
    week_number: int
    objectives: List[str]
    actions: List[ActionPlan]


class PhasePlan(BaseModel):
    """Phase plan generated by decomposer"""
    phase_number: int
    name: str
    objective: str
    duration_weeks: int
    expected_outcomes: List[str]
    weeks: List[WeekPlan]


class MissionDecomposition(BaseModel):
    """Full decomposition of a mission into phases, weeks, and actions"""
    title: str
    description: str
    category: MissionCategory
    success_criteria: dict
    target_weeks: int
    phases: List[PhasePlan]
    plan_document: str  # Markdown version


# ============================================================================
# API Response Models
# ============================================================================

class MissionSummary(BaseModel):
    """Condensed mission for list views"""
    id: UUID
    title: str
    category: Optional[str] = None
    progress_pct: int
    health: str
    current_phase: Optional[str] = None
    next_action: Optional[str] = None
    next_action_date: Optional[date] = None


class TodayAction(BaseModel):
    """Action for today's focus view"""
    action_id: UUID
    mission_id: UUID
    mission_title: str
    action_type: str
    description: str
    scheduled_time: Optional[time] = None
    status: str


class MissionWithDetails(BaseModel):
    """Full mission with phases and current week"""
    mission: Mission
    phases: List[MissionPhase]
    current_week: Optional[WeekPlan] = None
    upcoming_actions: List[ScheduledAction]
    recent_checkpoints: List[MissionCheckpoint]
