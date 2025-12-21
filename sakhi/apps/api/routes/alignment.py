from __future__ import annotations

from fastapi import APIRouter, HTTPException

from sakhi.apps.api.core.db import q

router = APIRouter(prefix="/v1/alignment", tags=["alignment"])


@router.get("/today")
async def alignment_today(person_id: str):
    try:
        row = await q(
            """
            SELECT alignment_map, updated_at
            FROM daily_alignment_cache
            WHERE person_id = $1
            """,
            person_id,
            one=True,
        )
        return {"status": "ok", "data": row or {}}
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to load alignment")


__all__ = ["router"]
