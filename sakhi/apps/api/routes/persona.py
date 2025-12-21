from __future__ import annotations

from fastapi import APIRouter, Query

from sakhi.apps.api.core.db import q as db_fetchrow

router = APIRouter(prefix="/persona", tags=["Persona"])


@router.get("/current")
async def get_persona(person_id: str = Query(...)):
    row = await db_fetchrow("SELECT * FROM persona_traits WHERE person_id = $1", person_id)
    return {"persona": row or {}}


__all__ = ["router"]
