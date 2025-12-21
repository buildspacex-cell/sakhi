from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter
from pydantic import BaseModel, Field

from sakhi.apps.api.services.memory.recall import unified_recall

router = APIRouter(prefix="/recall", tags=["recall"])


class RecallIn(BaseModel):
    person_id: str
    query: str = Field(min_length=1)
    days: int = Field(default=90, ge=1, le=365)
    limit: int = Field(default=8, ge=1, le=100)


@router.post("/search")
async def search(body: RecallIn) -> Dict[str, Any]:
    results = await unified_recall(body.person_id, body.query, limit=body.limit)
    return {"results": results}
