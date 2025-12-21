from __future__ import annotations

import asyncio
from typing import List, Optional

import numpy as np
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from sakhi.apps.api.core.db import DBSession, get_db
from sakhi.apps.worker.tasks.sync_breath_to_body import sync_breath_to_body

router = APIRouter(prefix="/breath", tags=["breath"])


class BreathSessionPayload(BaseModel):
    person_id: str
    duration_sec: int = 60
    rates: List[float] = Field(default_factory=list)
    pattern: Optional[str] = "equal"
    notes: Optional[str] = None


@router.post("/session")
async def log_breath_session(
    payload: BreathSessionPayload,
    db: DBSession = Depends(get_db),
) -> dict[str, float | str]:
    if payload.duration_sec <= 0:
        raise HTTPException(status_code=400, detail="duration_sec must be positive")

    flag_row = await db.fetchrow(
        "SELECT allow_bio_data FROM profiles WHERE user_id = $1",
        payload.person_id,
    )
    if not flag_row or not flag_row.get("allow_bio_data"):
        await db.close()
        raise HTTPException(status_code=403, detail="Bio-data disabled for this profile.")

    avg_rate = float(np.mean(payload.rates)) if payload.rates else None
    calm_score = 0.0
    if avg_rate is not None:
        calm_score = round(max(0.0, 1 - abs(avg_rate - 6.0) / 6.0), 2)

    await db.execute(
        """
        INSERT INTO breath_sessions(
            person_id,
            duration_sec,
            avg_breath_rate,
            pattern,
            calm_score,
            notes
        )
        VALUES ($1, $2, $3, $4, $5, $6)
        """,
        payload.person_id,
        payload.duration_sec,
        avg_rate,
        payload.pattern or "equal",
        calm_score,
        payload.notes,
    )
    await db.close()

    asyncio.create_task(sync_breath_to_body(payload.person_id))
    return {"status": "ok", "calm_score": calm_score}


__all__ = ["router"]
