from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from sakhi.apps.api.core.db import q
from sakhi.apps.api.core.metrics import derivatives_written

router = APIRouter(prefix="/hands", tags=["hands"])


class ScheduleIn(BaseModel):
    person_id: str
    insight_id: str
    label: str = Field(min_length=1)
    minutes: int = Field(default=45, ge=5, le=8 * 60)
    start_ts: str | None = None


def _parse_start_ts(value: str | None) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="start_ts must be ISO-8601") from exc
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


@router.post("/schedule")
async def schedule(body: ScheduleIn) -> Dict[str, Any]:
    start = _parse_start_ts(body.start_ts)
    due = start + timedelta(minutes=body.minutes)
    payload_json = json.dumps({"insight_id": body.insight_id, "minutes": body.minutes}, ensure_ascii=False)
    origin_id = f"hands:{body.insight_id}:{int(start.timestamp())}"
    row = await q(
        """
        INSERT INTO planned_items (
            person_id,
            scope,
            label,
            payload,
            due_ts,
            status,
            priority,
            energy,
            horizon,
            origin_id,
            meta
        )
        VALUES ($1, 'health', $2, $3::jsonb, $4, 'scheduled', 2, 'medium', 'today', $5, $3::jsonb)
        RETURNING id
        """,
        body.person_id,
        body.label,
        payload_json,
        due,
        origin_id,
        one=True,
    )
    derivatives_written.inc()
    return {"ok": True, "planned_item_id": row["id"]}
