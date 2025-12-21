from __future__ import annotations

import datetime as dt
from typing import List, Dict, Any

from fastapi import APIRouter, HTTPException

from sakhi.apps.api.core.db import q
from sakhi.apps.api.schemas.soul_lens import SoulState, SoulTimelinePoint, SoulSummary

router = APIRouter(prefix="/soul", tags=["soul"])


def _flatten_top(items: List[Any], limit: int = 5) -> List[str]:
    flat: List[str] = []
    for item in items:
        if isinstance(item, list):
            flat.extend([str(x) for x in item])
        elif isinstance(item, str):
            flat.append(item)
    seen = []
    for it in flat:
        if it not in seen:
            seen.append(it)
    return seen[:limit]


@router.get("/state/{person_id}", response_model=SoulState)
async def get_soul_state(person_id: str):
    row = await q(
        """
        SELECT soul_state, soul_shadow, soul_light, soul_conflicts, soul_friction
        FROM personal_model
        WHERE person_id = $1
        """,
        person_id,
        one=True,
    )
    if not row:
        raise HTTPException(status_code=404, detail="Person not found")
    soul_state = row.get("soul_state") or {}
    return SoulState(
        core_values=soul_state.get("core_values") or [],
        longing=soul_state.get("longing") or [],
        aversions=soul_state.get("aversions") or [],
        identity_themes=soul_state.get("identity_themes") or [],
        commitments=soul_state.get("commitments") or [],
        shadow=row.get("soul_shadow") or soul_state.get("shadow_patterns") or [],
        light=row.get("soul_light") or soul_state.get("light_patterns") or [],
        conflicts=row.get("soul_conflicts") or [],
        friction=row.get("soul_friction") or [],
        confidence=soul_state.get("confidence"),
        updated_at=soul_state.get("updated_at"),
    )


@router.get("/timeline/{person_id}", response_model=List[SoulTimelinePoint])
async def get_soul_timeline(person_id: str, limit: int = 100):
    rows = await q(
        """
        SELECT soul_shadow, soul_light, soul_conflict, soul_friction, updated_at
        FROM memory_episodic
        WHERE person_id = $1
        ORDER BY updated_at DESC
        LIMIT $2
        """,
        person_id,
        limit,
    )
    timeline: List[SoulTimelinePoint] = []
    for row in rows:
        timeline.append(
            SoulTimelinePoint(
                ts=row.get("updated_at").isoformat() if isinstance(row.get("updated_at"), dt.datetime) else row.get("updated_at"),
                shadow=row.get("soul_shadow") or [],
                light=row.get("soul_light") or [],
                conflict=row.get("soul_conflict") or [],
                friction=row.get("soul_friction") or [],
            )
        )
    return timeline


@router.get("/summary/{person_id}", response_model=SoulSummary)
async def get_soul_summary(person_id: str):
    rows = await q(
        """
        SELECT soul_shadow, soul_light, soul_conflict, soul_friction
        FROM memory_episodic
        WHERE person_id = $1
        ORDER BY updated_at DESC
        LIMIT 200
        """,
        person_id,
    )
    shadows: List[Any] = []
    lights: List[Any] = []
    frictions: List[Any] = []
    for row in rows:
        shadows.extend(row.get("soul_shadow") or [])
        lights.extend(row.get("soul_light") or [])
        frictions.extend(row.get("soul_friction") or [])

    top_shadow = _flatten_top(shadows, limit=5)
    top_light = _flatten_top(lights, limit=5)
    dominant_friction = _flatten_top(frictions, limit=1)[0] if frictions else None

    identity_instability_index = float(len(top_shadow)) / max(1, len(top_light) + len(top_shadow))
    coherence_score = 1.0 - identity_instability_index

    return SoulSummary(
        top_shadow=top_shadow,
        top_light=top_light,
        dominant_friction=dominant_friction,
        identity_instability_index=round(identity_instability_index, 2),
        coherence_score=round(coherence_score, 2),
    )
