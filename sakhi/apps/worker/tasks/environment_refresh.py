from __future__ import annotations

from typing import Any, Dict, Optional

from sakhi.apps.api.services.environment.engine import upsert_environment_context


async def refresh_environment(
    person_id: str,
    *,
    weather: Optional[Dict[str, Any]] = None,
    calendar_blocks: Optional[list[Dict[str, Any]]] = None,
    day_cycle: Optional[str] = None,
    weekend_flag: Optional[bool] = None,
    holiday_flag: Optional[bool] = None,
    travel_flag: Optional[bool] = None,
    environment_tags: Optional[list[str]] = None,
) -> bool:
    """Lightweight refresh hook for scheduled or manual jobs."""
    return await upsert_environment_context(
        person_id,
        weather=weather,
        calendar_blocks=calendar_blocks,
        day_cycle=day_cycle,
        weekend_flag=weekend_flag,
        holiday_flag=holiday_flag,
        travel_flag=travel_flag,
        environment_tags=environment_tags,
    )


__all__ = ["refresh_environment"]
