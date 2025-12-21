from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

from sakhi.apps.api.core.llm import call_llm
from sakhi.apps.worker.utils.db import db_find, db_insert


async def run_presence_reflector(person_id: str) -> None:
    reflections: List[Dict[str, Any]] = db_find("reflections", {"user_id": person_id})
    if not reflections:
        return

    now = datetime.now(timezone.utc)
    pending = [
        ref
        for ref in reflections
        if (now - _coerce_datetime(ref.get("created_at"))).days >= 5
    ][:10]

    if not pending:
        return

    tone_rows = db_find("emotional_tones", {"person_id": person_id})
    tone_map = {row.get("reflection_id"): row for row in tone_rows}
    payload = [
        {
            "theme": ref.get("theme"),
            "content": ref.get("content"),
            "tone": tone_map.get(ref.get("id"), {}),
        }
        for ref in pending
    ]
    prompt = f"""
You are Sakhi’s Presence Layer.
Review past reflections and tones to create emotionally aligned follow-ups.

REFLECTIONS:
{json.dumps(payload, indent=2)}

Write 1–2 messages that:
- Match the emotional tone of each reflection
- Are gentle if the mood was low, or upbeat if progress was made
- Keep continuity and warmth
Output JSON:
[{{"theme": "...", "message": "...", "confidence": 0.8}}]
""".strip()

    response = await call_llm(messages=[{"role": "user", "content": prompt}])
    raw_content = response.get("message") if isinstance(response, dict) else response
    try:
        suggestions = json.loads(raw_content or "[]")
    except json.JSONDecodeError:
        return

    for suggestion in suggestions:
        scheduled_for = now + timedelta(days=1)
        db_insert(
            "presence_prompts",
            {
                "person_id": person_id,
                "theme": suggestion.get("theme"),
                "message": suggestion.get("message"),
                "scheduled_for": scheduled_for.isoformat(),
                "confidence": suggestion.get("confidence", 0.6),
            },
        )


def _coerce_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value))
    except Exception:
        return datetime.now(timezone.utc) - timedelta(days=5)


__all__ = ["run_presence_reflector"]
