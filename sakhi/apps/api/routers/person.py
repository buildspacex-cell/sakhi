from __future__ import annotations

import json
from typing import Any, List

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from sakhi.apps.api.core.db import dbfetchrow, q
from sakhi.apps.api.services.memory.context_select import fetch_relevant_long_term


router = APIRouter(prefix="/person", tags=["person"])


class PersonSummaryIn(BaseModel):
    person_id: str


@router.post("/summary")
async def get_person_summary(body: PersonSummaryIn):
    row = await q(
        "SELECT * FROM person_summary_v WHERE person_id=$1",
        body.person_id,
        one=True,
    )
    if not row:
        return {
            "person_id": body.person_id,
            "goals": [],
            "values_prefs": [],
            "themes": [],
            "avg_mood_7d": None,
            "aspect_snapshot": [],
        }
    return dict(row)


class PersonalModelOut(BaseModel):
    person_id: str
    short_term: dict
    relevant_long_term: List[dict]
    overall_long_term: dict
    summary_text: str | None = None
    last_seen: str | None = None
    updated_at: str | None = None


def _ensure_dict(value: Any) -> dict:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            return {}
    return {}


@router.get("/model", response_model=PersonalModelOut)
async def get_personal_model(
    person_id: str = Query(...), latest_text: str | None = Query(None)
):
    row = await dbfetchrow(
        """
        SELECT person_id,
               COALESCE(short_term, '{}'::jsonb) AS short_term,
               COALESCE(long_term,  '{}'::jsonb) AS long_term,
               summary_text,
               last_seen,
               updated_at
        FROM personal_model
        WHERE person_id = $1
        """,
        person_id,
    )

    if not row:
        raise HTTPException(status_code=404, detail="personal_model not found")

    short_term = _ensure_dict(row.get("short_term"))
    overall_long_term = _ensure_dict(row.get("long_term"))

    relevant_long_term: List[dict] = []
    if latest_text:
        relevant_long_term = await fetch_relevant_long_term(person_id, latest_text)

    updated = row.get("updated_at")
    updated_str = _to_iso(updated)

    last_seen_value = row.get("last_seen")
    if last_seen_value is None:
        last_seen_value = short_term.get("updated_at") or overall_long_term.get("last_updated")
    last_seen_str = _to_iso(last_seen_value)

    return {
        "person_id": str(row["person_id"]),
        "short_term": short_term,
        "relevant_long_term": relevant_long_term,
        "overall_long_term": overall_long_term,
        "summary_text": row.get("summary_text"),
        "last_seen": last_seen_str,
        "updated_at": updated_str,
    }


def _to_iso(value: Any) -> str | None:
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if isinstance(value, str):
        return value
    return str(value)
