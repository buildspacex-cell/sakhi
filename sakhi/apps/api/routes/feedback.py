from __future__ import annotations

from fastapi import APIRouter, Query

from sakhi.apps.api.core.db import q as db_fetch

router = APIRouter(prefix="/feedback", tags=["Feedback"])


@router.get("/summary")
async def feedback_summary(person_id: str = Query(...)):
    rows = await db_fetch(
        """
        SELECT feedback_type, COUNT(*) AS count, AVG(relevance_score) AS avg_score
        FROM reflection_feedback
        WHERE person_id = $1
        GROUP BY feedback_type
        """,
        person_id,
    )
    return {"summary": rows}


__all__ = ["router"]
