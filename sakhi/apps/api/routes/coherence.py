from __future__ import annotations

from fastapi import APIRouter, HTTPException

from sakhi.apps.api.core.db import q

router = APIRouter(prefix="/v1/coherence", tags=["coherence"])


@router.get("/report")
async def coherence_report(person_id: str):
    try:
        row = await q(
            "SELECT coherence_state FROM personal_model WHERE person_id = $1",
            person_id,
            one=True,
        )
        if row and row.get("coherence_state") is not None:
            return {"status": "ok", "data": row.get("coherence_state")}
        cache_row = await q(
            "SELECT coherence_state FROM coherence_cache WHERE person_id = $1",
            person_id,
            one=True,
        )
        return {"status": "ok", "data": cache_row.get("coherence_state") if cache_row else {}}
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to load coherence report")


__all__ = ["router"]
