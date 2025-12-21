from __future__ import annotations

from fastapi import APIRouter, HTTPException

from sakhi.apps.api.core.db import q

router = APIRouter(prefix="/v1", tags=["forecast"])


@router.get("/forecast")
async def forecast(person_id: str):
    try:
        pm_row = await q(
            "SELECT forecast_state FROM personal_model WHERE person_id = $1",
            person_id,
            one=True,
        )
        if pm_row and pm_row.get("forecast_state") is not None:
            return {"status": "ok", "data": pm_row.get("forecast_state")}
        cache_row = await q(
            "SELECT forecast_state FROM forecast_cache WHERE person_id = $1",
            person_id,
            one=True,
        )
        return {"status": "ok", "data": cache_row.get("forecast_state") if cache_row else {}}
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to load forecast state")


__all__ = ["router"]
