from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, status

from sakhi.apps.api.services.reflection.daily_generator import generate_daily_reflection

router = APIRouter(prefix="/reflection", tags=["reflection"])


@router.post("/daily")
async def trigger_daily_reflection(person_id: str = Query(...)):
    result = await generate_daily_reflection(person_id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to generate daily reflection.",
        )
    return {"status": "ok", "data": result}


__all__ = ["router"]
