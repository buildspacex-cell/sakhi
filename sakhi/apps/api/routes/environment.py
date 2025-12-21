from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from sakhi.apps.api.services.environment.engine import (
    get_environment_context,
    upsert_environment_context,
)

router = APIRouter(prefix="/environment", tags=["environment"])


class EnvironmentUpdateIn(BaseModel):
    person_id: str
    weather: Optional[Dict[str, Any]] = Field(default=None, description="lightweight weather payload e.g. {temp_c, condition}")
    calendar_blocks: Optional[List[Dict[str, Any]]] = Field(default=None, description="summarised calendar blocks for the day")
    day_cycle: Optional[str] = Field(default=None, description="morning|afternoon|evening|night")
    weekend_flag: Optional[bool] = None
    holiday_flag: Optional[bool] = None
    travel_flag: Optional[bool] = None
    environment_tags: Optional[List[str]] = None


@router.post("/update")
async def environment_update(body: EnvironmentUpdateIn) -> Dict[str, Any]:
    ok = await upsert_environment_context(
        body.person_id,
        weather=body.weather,
        calendar_blocks=body.calendar_blocks,
        day_cycle=body.day_cycle,
        weekend_flag=body.weekend_flag,
        holiday_flag=body.holiday_flag,
        travel_flag=body.travel_flag,
        environment_tags=body.environment_tags,
    )
    if not ok:
        raise HTTPException(status_code=500, detail="Failed to update environment context")
    ctx = await get_environment_context(body.person_id)
    return {"status": "ok", "data": ctx}


@router.get("/get")
async def environment_get(person_id: str = Query(..., description="person id")) -> Dict[str, Any]:
    ctx = await get_environment_context(person_id)
    return {"status": "ok", "data": ctx or {}}


__all__ = ["router"]
