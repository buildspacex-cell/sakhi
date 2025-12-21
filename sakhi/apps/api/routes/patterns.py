from __future__ import annotations

from fastapi import APIRouter, HTTPException

from sakhi.apps.api.core.db import q

router = APIRouter(prefix="/v1", tags=["patterns"])


@router.get("/patterns")
async def patterns(person_id: str):
    try:
        row = await q(
            "SELECT pattern_sense FROM personal_model WHERE person_id = $1",
            person_id,
            one=True,
        )
        return {"status": "ok", "data": row.get("pattern_sense") if row else {}}
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to load pattern sense")


__all__ = ["router"]
