from __future__ import annotations

import json
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException

from sakhi.apps.api.core.db import q

router = APIRouter(prefix="/rhythm", tags=["rhythm"])


@router.get("/{person_id}/state")
async def rhythm_state(person_id: str) -> Dict[str, Any]:
    row = await q(
        """
        SELECT rs.*, rc.chronotype, rc.score, rc.evidence
        FROM rhythm_state rs
        LEFT JOIN rhythm_chronotype rc ON rc.person_id = rs.person_id
        WHERE rs.person_id = $1
        """,
        person_id,
        one=True,
    )
    if not row:
        raise HTTPException(status_code=404, detail="Rhythm state not found")
    payload = dict(row)
    return payload


@router.get("/{person_id}/curve")
async def rhythm_curve(person_id: str) -> Dict[str, Any]:
    curves = await q(
        """
        SELECT day_scope, slots, confidence, created_at
        FROM rhythm_daily_curve
        WHERE person_id = $1
        ORDER BY day_scope DESC
        LIMIT 7
        """,
        person_id,
    )
    alignment_rows = await q(
        """
        SELECT horizon, recommendations, generated_at
        FROM rhythm_planner_alignment
        WHERE person_id = $1
        """,
        person_id,
    )
    return {
        "days": [dict(row) for row in curves],
        "alignment": {row["horizon"]: row["recommendations"] for row in alignment_rows},
    }


__all__ = ["router"]
