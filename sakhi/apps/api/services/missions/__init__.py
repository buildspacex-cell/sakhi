"""
Mission Service - Long-Running Task Management

Handles missions that span weeks or months:
- Twitter brand building
- Learning new skills
- Fitness goals
- Expense tracking

Architecture: See docs/LONG_RUNNING_TASKS.md
"""

from .models import (
    Mission,
    MissionPhase,
    WeeklyPlan,
    ScheduledAction,
    MissionCheckpoint,
    MissionData,
    MissionCreate,
    MissionDecomposition,
    MissionSummary,
    TodayAction,
    MissionWithDetails,
    MissionCategory,
)
from .repository import MissionRepository
from .service import MissionService
from .decomposer import (
    decompose_mission,
    decompose_first_week,
    suggest_next_actions,
    calculate_action_dates,
)

__all__ = [
    # Models
    "Mission",
    "MissionPhase",
    "WeeklyPlan",
    "ScheduledAction",
    "MissionCheckpoint",
    "MissionData",
    "MissionCreate",
    "MissionDecomposition",
    "MissionSummary",
    "TodayAction",
    "MissionWithDetails",
    "MissionCategory",
    # Service
    "MissionService",
    "MissionRepository",
    # Decomposer functions
    "decompose_mission",
    "decompose_first_week",
    "suggest_next_actions",
    "calculate_action_dates",
]
