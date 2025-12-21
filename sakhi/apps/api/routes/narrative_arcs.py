from __future__ import annotations

from fastapi import APIRouter, HTTPException

from sakhi.apps.api.core.db import q

router = APIRouter(prefix="/v1/narrative", tags=["narrative"])


@router.get("/arcs")
async def narrative_arcs(person_id: str):
    try:
        row = await q(
            "SELECT narrative_arcs FROM personal_model WHERE person_id = $1",
            person_id,
            one=True,
        )
        return {"status": "ok", "data": row.get("narrative_arcs") if row else []}
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to load narrative arcs")


__all__ = ["router"]
