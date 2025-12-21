from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from sakhi.apps.api.core.db import q

router = APIRouter(prefix="/person", tags=["person-edit"])


class GoalUpsert(BaseModel):
    person_id: str
    title: str
    status: str = "active"
    horizon: str = "month"
    progress: float = 0.0


@router.post("/goal/upsert")
async def goal_upsert(body: GoalUpsert):
    row = await q(
        """
        insert into goals (person_id, title, horizon, status, progress)
        values ($1,$2,$3,$4,$5)
        on conflict do nothing
        returning id
        """,
        body.person_id,
        body.title,
        body.horizon,
        body.status,
        body.progress,
        one=True,
    )
    return {"ok": True, "id": row["id"] if row else None}


class PrefUpsert(BaseModel):
    person_id: str
    scope: str
    key: str
    value: dict
    confidence: float = 0.8


@router.post("/preference/upsert")
async def pref_upsert(body: PrefUpsert):
    await q(
        """
        insert into preferences (person_id, scope, key, value, confidence)
        values ($1,$2,$3,$4,$5)
        """,
        body.person_id,
        body.scope,
        body.key,
        body.value,
        body.confidence,
    )
    return {"ok": True}
