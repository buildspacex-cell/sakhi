from __future__ import annotations

import json
import uuid
from typing import Any, Dict

from fastapi import APIRouter
from pydantic import BaseModel

from sakhi.apps.api.core.db import q

router = APIRouter(prefix="/intel", tags=["intelligence"])


class ReflectIn(BaseModel):
    person_id: str
    insight_id: str
    feedback: str
    note: str | None = None


@router.post("/reflect")
async def reflect(body: ReflectIn) -> Dict[str, Any]:
    event_id = f"evt_{uuid.uuid4().hex}"
    payload_json = json.dumps(
        {"insight_id": body.insight_id, "feedback": body.feedback, "note": body.note or ""},
        ensure_ascii=False,
    )
    context_json = json.dumps(
        {"device": "web", "tz": "Asia/Kolkata", "privacy_flags": ["pii_masked"]},
        ensure_ascii=False,
    )
    await q(
        """
        INSERT INTO aw_event(
            id, actor, modality, person_id, payload, context_json, schema_version, hash
        )
        VALUES ($1, 'user', 'thought', $2, $3::jsonb, $4::jsonb, 'aw_1', $5)
        """,
        event_id,
        body.person_id,
        payload_json,
        context_json,
        f"feedback:{body.insight_id}",
    )

    if body.feedback == "up":
        await q(
            "UPDATE insight SET confidence = LEAST(1.0, confidence + 0.05) WHERE id = $1",
            body.insight_id,
        )
    elif body.feedback == "down":
        await q(
            "UPDATE insight SET confidence = GREATEST(0.0, confidence - 0.05) WHERE id = $1",
            body.insight_id,
        )

    await q(
        "INSERT INTO aw_edge(src_id, dst_id, kind) VALUES ($1, $2, 'reflects') ON CONFLICT DO NOTHING",
        body.insight_id,
        event_id,
    )
    return {"ok": True}
