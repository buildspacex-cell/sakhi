from __future__ import annotations

import datetime
from typing import Any, Dict, List

from sakhi.apps.worker.utils.db import db_find, db_insert
from sakhi.apps.worker.utils.llm import llm_reflect


async def synthesize_meta_reflection(person_id: str, period: str = "weekly") -> None:
    reflections: List[Dict[str, Any]] = db_find("reflections", {"user_id": person_id})
    feedback: List[Dict[str, Any]] = db_find("reflection_feedback", {"person_id": person_id})
    if not reflections:
        return

    recent_reflections = reflections[-20:]
    text_block = "\n".join(str(row.get("content") or "") for row in recent_reflections if row.get("content"))
    if not text_block:
        return

    helpful_count = sum(1 for row in feedback if row.get("helpful"))
    feedback_summary = f"{helpful_count} helpful / {len(feedback)} total" if feedback else "No feedback yet"

    summary = await llm_reflect(
        f"""
Summarize what Sakhi has learned about this person this {period}.
Include observed themes, reflection accuracy, and tone adjustments.
Reflections: {text_block}
Feedback summary: {feedback_summary}
""".strip(),
        mode="meta_reflection",
    )

    db_insert(
        "meta_reflections",
        {
            "person_id": person_id,
            "period": period,
            "summary": summary,
            "insights": {"feedback_ratio": feedback_summary},
            "captured_at": datetime.datetime.utcnow().isoformat(),
        },
    )


__all__ = ["synthesize_meta_reflection"]
