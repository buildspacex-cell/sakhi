from __future__ import annotations

from statistics import mean
from typing import Any, Dict, List

from sakhi.apps.worker.utils.db import db_find, db_update


async def compute_feedback_scores(person_id: str) -> None:
    """
    Aggregates reflection_feedback to update confidence per reflection kind.
    """
    rows: List[Dict[str, Any]] = db_find("reflection_feedback", {"person_id": person_id})
    if not rows:
        return

    helpful_scores = [1 if row.get("helpful") else 0 for row in rows]
    if not helpful_scores:
        return
    avg_score = mean(helpful_scores)
    db_update("personal_model", {"person_id": person_id}, {"reflection_feedback_score": avg_score})


__all__ = ["compute_feedback_scores"]
