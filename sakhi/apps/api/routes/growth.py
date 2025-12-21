from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from sakhi.apps.api.services.growth.loop import record_daily_check_in, summarize_growth

router = APIRouter(prefix="/growth", tags=["growth"])


class CheckInPayload(BaseModel):
    energy: float | None = Field(None, ge=0.0, le=1.0)
    mood: str | None = None
    reflection: str | None = None
    plan_adjustment: dict[str, object] | None = None


@router.get("/{person_id}/summary")
async def growth_summary(person_id: str):
    return await summarize_growth(person_id)


@router.post("/{person_id}/checkin")
async def growth_checkin(person_id: str, payload: CheckInPayload):
    result = await record_daily_check_in(
        person_id,
        energy=payload.energy,
        mood=payload.mood,
        reflection=payload.reflection,
        plan_adjustment=payload.plan_adjustment,
    )
    if not result:
        raise HTTPException(status_code=500, detail="Unable to record check-in")
    return result


__all__ = ["router"]
