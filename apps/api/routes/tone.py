from __future__ import annotations

from fastapi import APIRouter, Query

router = APIRouter(prefix="/tone", tags=["Tone"])


@router.post("/refresh")
async def trigger_tone_refresh(person_id: str = Query(...)):
    # Queue/workers are not wired in this container; respond with stub.
    return {"status": "queued", "person_id": person_id}


__all__ = ["router"]
