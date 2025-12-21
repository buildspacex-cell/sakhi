from __future__ import annotations

from typing import Any, Dict, List

import os

from sakhi.apps.worker.utils.db import db_fetch, db_insert
from sakhi.apps.worker.utils.llm import llm_router


def _resolve_default_user() -> str:
    default = os.getenv("DEFAULT_USER_ID") or os.getenv("DEMO_USER_ID")
    if not default:
        raise RuntimeError("Set DEFAULT_USER_ID or DEMO_USER_ID before generating clarity actions.")
    return default


async def generate_clarity_actions(person_id: str | None = None, reflection_text: str | None = None) -> None:
    """
    Uses reflection summary to extract actionable steps.
    """
    person_id = person_id or _resolve_default_user()
    text = reflection_text
    if not text:
        latest = db_fetch("reflections", {"person_id": person_id})
        text = latest.get("summary") if latest else ""
        if not text:
            return

    prompt = f"""
From this reflection text, extract any concrete actions or goals implied.
Return JSON list: [{{"action": "...", "confidence": 0.8}}].
Text: {text}
""".strip()

    try:
        suggestions: List[Dict[str, Any]] = await llm_router.json_extract(prompt)
    except Exception:
        return

    for suggestion in suggestions:
        action = suggestion.get("action")
        if not action:
            continue
        db_insert(
            "reflection_actions",
            {
                "person_id": person_id,
                "suggested_action": action,
                "confidence": float(suggestion.get("confidence", 0.7)),
                "status": "pending",
            },
        )


__all__ = ["generate_clarity_actions"]
