from __future__ import annotations

import datetime as dt
import hashlib
import json
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from sakhi.apps.api.core.db import q
from sakhi.apps.api.core.events import publish
from sakhi.apps.api.core.metrics import aw_events_written

router = APIRouter(prefix="/aw", tags=["awareness"])


class AwarenessEventIn(BaseModel):
    id: Optional[str] = None
    ts: Optional[dt.datetime] = None
    actor: str
    modality: str
    person_id: str
    payload: Dict[str, Any] = Field(default_factory=dict)
    payload_ref: Optional[str] = None
    context_json: Dict[str, Any]


class BatchIn(BaseModel):
    events: List[AwarenessEventIn]


def _ensure_ts(ts: Optional[dt.datetime]) -> dt.datetime:
    if ts is None:
        return dt.datetime.now(dt.timezone.utc)
    if ts.tzinfo is None:
        return ts.replace(tzinfo=dt.timezone.utc)
    return ts.astimezone(dt.timezone.utc)


def _parse_ts_param(value: Optional[str], label: str) -> Optional[dt.datetime]:
    if value is None:
        return None
    try:
        if value.endswith("Z"):
            value = value[:-1] + "+00:00"
        parsed = dt.datetime.fromisoformat(value)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid {label} value; expected ISO 8601 timestamp") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.timezone.utc)
    return parsed.astimezone(dt.timezone.utc)


@router.post("/events")
async def post_events(body: BatchIn) -> Dict[str, Any]:
    rows: List[Dict[str, str]] = []
    queue_payloads: List[Dict[str, Any]] = []
    for event in body.events:
        event_id = event.id or f"evt_{uuid.uuid4().hex}"
        ts = _ensure_ts(event.ts)
        digest = hashlib.sha256(
            json.dumps(
                {
                    "actor": event.actor,
                    "modality": event.modality,
                    "person_id": event.person_id,
                    "ts": ts.isoformat(),
                    "payload": event.payload,
                },
                sort_keys=True,
            ).encode()
        ).hexdigest()
        payload_json = json.dumps(event.payload, ensure_ascii=False)
        context_json = json.dumps(event.context_json, ensure_ascii=False)
        row = await q(
            """
            INSERT INTO aw_event (
                id, ts, actor, modality, person_id, payload_ref,
                payload, context_json, schema_version, hash
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7::jsonb, $8::jsonb, 'aw_1', $9)
            ON CONFLICT (id) DO NOTHING
            RETURNING id
            """,
            event_id,
            ts,
            event.actor,
            event.modality,
            event.person_id,
            event.payload_ref,
            payload_json,
            context_json,
            digest,
            one=True,
        )
        returned_id = row["id"] if row else event_id
        rows.append({"id": returned_id})
        queue_payloads.append(
            {
                "id": returned_id,
                "person_id": event.person_id,
                "modality": event.modality,
                "payload": event.payload,
                "payload_redacted": False,
                "actor": event.actor,
                "ts": ts.isoformat(),
            }
        )
        aw_events_written.inc()
    for payload in queue_payloads:
        await publish("aw.events", payload)
    return {"ok": True, "inserted": rows}


@router.get("/timeline")
async def timeline(
    person_id: str,
    frm: Optional[str] = None,
    to: Optional[str] = None,
    modality: Optional[str] = None,
    limit: int = 200,
) -> Dict[str, Any]:
    if limit <= 0 or limit > 1000:
        raise HTTPException(status_code=400, detail="limit must be between 1 and 1000")

    frm_ts = _parse_ts_param(frm, "from")
    to_ts = _parse_ts_param(to, "to")

    sql_parts = ["SELECT * FROM aw_event WHERE person_id=$1"]
    args: List[Any] = [person_id]
    param_index = 2

    if frm_ts is not None:
        sql_parts.append(f"AND ts >= ${param_index}")
        args.append(frm_ts)
        param_index += 1
    if to_ts is not None:
        sql_parts.append(f"AND ts <= ${param_index}")
        args.append(to_ts)
        param_index += 1
    if modality is not None:
        sql_parts.append(f"AND modality = ${param_index}")
        args.append(modality)
        param_index += 1

    sql_parts.append(f"ORDER BY ts DESC LIMIT ${param_index}")
    args.append(limit)

    events = await q(" ".join(sql_parts), *args)
    return {"events": [dict(event) for event in events]}


class RedactIn(BaseModel):
    event_ids: List[str]
    reason: Optional[str] = None


@router.post("/redact")
async def redact(body: RedactIn) -> Dict[str, Any]:
    for event_id in body.event_ids:
        await q("UPDATE aw_event SET payload_redacted = TRUE WHERE id = $1", event_id)
        await q("INSERT INTO aw_redaction (event_id, reason) VALUES ($1, $2)", event_id, body.reason or "")
    return {"ok": True, "redacted": len(body.event_ids)}
