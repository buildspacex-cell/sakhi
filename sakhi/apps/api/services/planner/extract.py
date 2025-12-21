from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List

from sakhi.apps.api.core.llm import call_llm

LOGGER = logging.getLogger(__name__)
_JSON_BLOCK_RE = re.compile(r"```json\s*(.*?)```", re.DOTALL | re.IGNORECASE)
VALID_TIME_KINDS = {
    "today",
    "tomorrow",
    "this_week",
    "this_month",
    "this_quarter",
    "unspecified",
}
VALID_RECURRENCE_KINDS = {"none", "daily", "weekly", "monthly", "quarterly"}
VALID_ENERGY = {"low", "medium", "high"}


async def extract_intents(person_id: str, text: str) -> List[Dict[str, Any]]:
    """
    Use LLM to interpret text → intents.
    """

    prompt = f"""
You are Sakhi's intent extractor. Extract actionable user intents only.
Always respond in pure JSON inside one ```json block.

User said: "{text}"

Your output MUST be exactly in this format:

```json
{{
  "intents": [
    {{
      "type": "task" | "plan" | "reminder" | "goal" | "query",
      "title": "<short title>",
      "details": "<full user request paraphrased>",
      "time_window": {{
        "kind": "today" | "tomorrow" | "this_week" | "this_month" | "this_quarter" | "unspecified",
        "confidence": 0.0
      }},
      "priority": 1-5,
      "recurrence": {{"kind": "none"|"daily"|"weekly"|"monthly"|"quarterly", "interval_days": 0}},
      "energy_hint": "low"|"medium"|"high"|null,
      "difficulty_hint": "very_easy"|"easy"|"medium"|"hard"|"very_hard"|null
    }}
  ]
}}
```

Rules:
1. If no actionable intent is present, return:
   ```json
   {{"intents": []}}
   ```
2. NEVER return plain text.
3. NEVER respond without a ```json block.
4. If uncertain, still return an empty intents array inside JSON.
"""

    response = await call_llm(
        messages=[{"role": "user", "content": prompt}],
        model="gpt-4o-mini",
        person_id=person_id,
    )

    payload = response if isinstance(response, str) else json.dumps(response)
    intents = _parse_intents(payload)
    if intents is None:
        preview = payload.strip()
        if len(preview) > 200:
            preview = preview[:200] + "…"
        LOGGER.warning("[Planner] Intent extraction failed; returning empty list. payload=%s", preview)
        return []
    return intents


__all__ = ["extract_intents"]


def _parse_intents(payload: str) -> List[Dict[str, Any]] | None:
    snippet = _extract_json_snippet(payload)
    if not snippet:
        return None

    try:
        parsed = json.loads(snippet)
    except json.JSONDecodeError:
        return None

    intents = parsed.get("intents")
    if not isinstance(intents, list):
        return None

    normalized: List[Dict[str, Any]] = []
    for intent in intents:
        if not isinstance(intent, dict):
            continue
        normalized.append(
            {
                "type": str(intent.get("type") or "query"),
                "title": str(intent.get("title") or "").strip(),
                "details": str(intent.get("details") or "").strip(),
                "time_window": _normalize_time_window(intent.get("time_window")),
                "priority": _normalize_priority(intent.get("priority")),
                "recurrence": _normalize_recurrence(intent.get("recurrence")),
                "energy_hint": _normalize_energy(intent.get("energy_hint")),
                "difficulty_hint": _normalize_difficulty(intent.get("difficulty_hint")),
            }
        )
    return normalized


def _extract_json_snippet(payload: str) -> str | None:
    text = payload.strip()
    if not text:
        return None

    block_match = _JSON_BLOCK_RE.search(text)
    if block_match:
        snippet = block_match.group(1).strip()
        if snippet:
            return snippet

    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return text[start : end + 1].strip()
    return None


def _normalize_time_window(candidate: Any) -> Dict[str, Any]:
    default = {"kind": "unspecified", "confidence": 0.0}
    if not isinstance(candidate, dict):
        return default

    kind = str(candidate.get("kind") or "").strip().lower()
    if kind not in VALID_TIME_KINDS:
        kind = "unspecified"

    confidence_raw = candidate.get("confidence", 0.0)
    try:
        confidence = float(confidence_raw)
    except (TypeError, ValueError):
        confidence = 0.0
    confidence = max(0.0, min(1.0, confidence))
    return {"kind": kind, "confidence": confidence}


def _normalize_priority(value: Any) -> int:
    try:
        num = int(value)
    except (TypeError, ValueError):
        num = 1
    return max(1, min(5, num))


def _normalize_recurrence(candidate: Any) -> Dict[str, Any] | None:
    if candidate is None:
        return None
    if isinstance(candidate, str):
        kind = candidate.strip().lower()
        if kind not in VALID_RECURRENCE_KINDS:
            kind = "none"
        return {"kind": kind, "interval_days": 0 if kind == "none" else 1}
    if isinstance(candidate, dict):
        kind = str(candidate.get("kind") or "none").strip().lower()
        if kind not in VALID_RECURRENCE_KINDS:
            kind = "none"
        try:
            interval = int(candidate.get("interval_days") or 0)
        except (TypeError, ValueError):
            interval = 0
        return {"kind": kind, "interval_days": max(0, interval)}
    return None


def _normalize_energy(candidate: Any) -> str | None:
    if not candidate:
        return None
    key = str(candidate).strip().lower()
    return key if key in VALID_ENERGY else None


def _normalize_difficulty(candidate: Any) -> str | None:
    if not candidate:
        return None
    key = str(candidate).strip().lower()
    replacements = {"very easy": "very_easy", "very hard": "very_hard"}
    key = replacements.get(key, key)
    allowed = {"very_easy", "easy", "medium", "hard", "very_hard"}
    return key if key in allowed else None
