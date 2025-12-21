from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter

from sakhi.apps.api.core.db import q

router = APIRouter(prefix="/soul", tags=["soul"])


@router.get("/alignment")
async def alignment(person_id: str) -> Dict[str, Any]:
    goals = await q(
        "SELECT COUNT(*) AS c FROM goals WHERE person_id=$1 AND status='active'",
        person_id,
        one=True,
    )
    work = await q(
        """
        SELECT COUNT(*) AS c
        FROM episodes
        WHERE person_id=$1
          AND ts > NOW() - INTERVAL '7 days'
          AND 'work'=ANY(tags)
        """,
        person_id,
        one=True,
    )
    health = await q(
        """
        SELECT COUNT(*) AS c
        FROM episodes
        WHERE person_id=$1
          AND ts > NOW() - INTERVAL '7 days'
          AND 'health'=ANY(tags)
        """,
        person_id,
        one=True,
    )
    work_count = float(work.get("c", 0) or 0)
    health_count = float(health.get("c", 0) or 0)
    score = (health_count + 1.0) / (work_count + 1.0)
    return {"alignment_score": max(0.0, min(1.0, score))}
