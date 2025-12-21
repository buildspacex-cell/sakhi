from __future__ import annotations

from fastapi import APIRouter, HTTPException

from sakhi.apps.api.core.db import q

router = APIRouter(prefix="/v1", tags=["identity"])


@router.get("/identity/conflict")
async def inner_conflict(person_id: str):
    try:
        pm_row = await q(
            "SELECT conflict_state FROM personal_model WHERE person_id = $1",
            person_id,
            one=True,
        )
        if pm_row and pm_row.get("conflict_state") is not None:
            return {"status": "ok", "data": pm_row.get("conflict_state")}
        cache_row = await q(
            "SELECT conflict_state FROM inner_conflict_cache WHERE person_id = $1",
            person_id,
            one=True,
        )
        return {"status": "ok", "data": cache_row.get("conflict_state") if cache_row else {}}
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to load conflict state")


__all__ = ["router"]
