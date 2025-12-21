from __future__ import annotations

from fastapi import APIRouter, HTTPException

from sakhi.apps.api.core.db import q

router = APIRouter(prefix="/v1", tags=["inner-dialogue"])


@router.get("/inner_dialogue")
async def inner_dialogue(person_id: str):
    """
    Read-only access to the latest inner dialogue frame for a person.
    Returns the cached dialogue from personal_model, falling back to the cache table if present.
    """
    try:
        pm_row = await q(
            "SELECT inner_dialogue_state FROM personal_model WHERE person_id = $1",
            person_id,
            one=True,
        )
        if pm_row and pm_row.get("inner_dialogue_state") is not None:
            return {"status": "ok", "dialogue": pm_row.get("inner_dialogue_state")}

        cache_row = await q(
            "SELECT dialogue FROM inner_dialogue_cache WHERE person_id = $1",
            person_id,
            one=True,
        )
        return {"status": "ok", "dialogue": cache_row.get("dialogue") if cache_row else {}}
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to load inner dialogue")


__all__ = ["router"]
