"""
Stub functions for archived workers.

These workers were archived in the v2 refactor but some debug routes still reference them.
Instead of breaking the routes, we provide no-op stubs that return "archived" status.
"""

from typing import Any, Dict, Optional


async def run_weekly_planner_pressure(person_id: str) -> Dict[str, Any]:
    """Stub for archived weekly_planner_pressure_worker."""
    return {"status": "archived", "note": "Worker archived in v2 refactor"}


async def run_turn_personal_model_update(person_id: str) -> Dict[str, Any]:
    """Stub for archived turn_personal_model_update."""
    return {"status": "archived", "note": "Worker archived in v2 refactor"}


async def generate_weekly_reflection(
    person_id: str,
    longitudinal_state: Optional[Dict] = None,
    system_prompt_override: Optional[str] = None,
    user_prompt_override: Optional[str] = None,
    include_debug: bool = False,
    target_week_start: Optional[Any] = None,
) -> Dict[str, Any]:
    """Stub for archived weekly_reflection."""
    return {
        "status": "archived",
        "note": "Worker archived in v2 refactor",
        "reflection": "Weekly reflection feature is being updated.",
    }


async def _fetch_weekly_signals(
    person_id: str,
    target_week_start: Optional[Any] = None,
) -> list:
    """Stub for archived _fetch_weekly_signals."""
    return []
