from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, List

from sakhi.apps.api.core.llm import call_llm
from sakhi.apps.worker.utils.db import db_find, db_insert, db_update


async def run_reflective_loop(person_id: str) -> None:
    reflections = db_find("reflections", {"user_id": person_id})[:5]
    turns = db_find("conversation_turns", {"user_id": person_id})[:20]

    for reflection in reflections:
        created_at = _coerce_datetime(reflection.get("created_at"))
        related_turns = [
            turn.get("text")
            for turn in turns
            if turn.get("role") == "user" and _coerce_datetime(turn.get("created_at")) > created_at
        ]
        if not related_turns:
            continue

        prompt = f"""
You are Sakhi’s self-observer.
Evaluate how the user responded to your reflection.

REFLECTION: "{reflection.get('content')}"
USER RESPONSES:
{json.dumps(related_turns[:5], indent=2)}

Classify as:
  - feedback_type: positive / neutral / negative
  - relevance_score: 0–1 (how aligned the reflection was)
Output JSON.
""".strip()

        response = await call_llm(messages=[{"role": "user", "content": prompt}])
        payload = response.get("message") if isinstance(response, dict) else response
        try:
            feedback = json.loads(payload or "{}")
        except json.JSONDecodeError:
            feedback = {}

        db_insert(
            "reflection_feedback",
            {
                "person_id": person_id,
                "reflection_id": reflection.get("id"),
                "feedback_type": feedback.get("feedback_type", "neutral"),
                "relevance_score": feedback.get("relevance_score", 0.5),
            },
        )

    rows = db_find("reflection_feedback", {"person_id": person_id})
    if rows:
        avg_score = sum(float(row.get("relevance_score", 0.5)) for row in rows) / len(rows)
        for edge in db_find("memory_edges", {"person_id": person_id}):
            current = float(edge.get("relevance", 0.5))
            updated = (current * 0.8) + (avg_score * 0.2)
            db_update(
                "memory_edges",
                {"person_id": person_id, "from_node": edge.get("from_node"), "to_node": edge.get("to_node")},
                {"relevance": updated},
            )


def _coerce_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value))
    except Exception:
        return datetime.now(timezone.utc)


__all__ = ["run_reflective_loop"]
