from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, List

from sakhi.apps.api.core.llm import call_llm
from sakhi.apps.worker.utils.db import db_find, db_insert


async def run_meta_audit(person_id: str) -> None:
    recent_reflections: List[Dict[str, Any]] = db_find("reflections", {"user_id": person_id})[:5]
    if not recent_reflections:
        return

    prompt = f"""
You are Sakhi’s Meta-Reviewer.
Evaluate the following recent reflections for:
- emotional bias (over-positivity, negativity)
- repetition or narrow theme focus
- missing perspectives (e.g., body vs mind imbalance)
Suggest a correction note for future reasoning style.

Data:
{recent_reflections}

Output JSON:
{{
  "bias_detected": ["emotion_focus","theme_repetition"],
  "correction_note": "Balance pragmatic and emotional insight in next reflection.",
  "confidence": 0.82
}}
""".strip()

    response = await call_llm(
        messages=[{"role": "user", "content": prompt}],
        person_id=person_id,
    )
    payload = response.get("message") if isinstance(response, dict) else response
    try:
        data = json.loads(payload or "{}")
    except json.JSONDecodeError:
        data = {}

    db_insert(
        "meta_audit",
        {
            "person_id": person_id,
            "review_scope": "reflection",
            "bias_detected": data.get("bias_detected", []),
            "correction_note": data.get("correction_note", ""),
            "confidence": data.get("confidence", 0.7),
            "created_at": datetime.now(timezone.utc).isoformat(),
        },
    )


__all__ = ["run_meta_audit"]
