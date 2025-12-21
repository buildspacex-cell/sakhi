from __future__ import annotations

from typing import Any, Dict, List

from sakhi.apps.api.core.llm import call_llm
INTENT_SYSTEM_PROMPT = """
You are Sakhi’s intent extractor.

Your job:
- Read the user text
- Identify any actionable intent (task, plan, reminder, goal, habit)
- Always return a JSON object:
{
  "intents": [
      {
         "kind": "...",
         "description": "...",
         "confidence": 0.0
      }
  ]
}

If nothing actionable is present:
{
  "intents": []
}

Be strict, concise, and NEVER output anything outside JSON.
"""


async def extract_intents_for_entry(
    *,
    entry_id: str | None,
    text: str,
    topics: List[str] | None = None,
    emotion: Dict[str, Any] | None = None,
) -> List[Dict[str, Any]]:
    """
    LLM-backed intent extraction tuned for the orchestrator.
    """

    topics = topics or []
    mood = (emotion or {}).get("label")

    result = await call_llm(
        messages=[
            {"role": "system", "content": INTENT_SYSTEM_PROMPT},
            {"role": "user", "content": text},
        ],
        model="gpt-4o-mini",
    )

    if isinstance(result, dict):
        payload = result.get("reply") or result.get("text") or result
    else:
        payload = result

    data: Dict[str, Any]
    try:
        if isinstance(payload, str):
            import json

            data = json.loads(payload)
        elif isinstance(payload, dict):
            data = payload
        else:
            data = {"intents": []}
    except Exception:
        data = {"intents": []}

    parsed: List[Dict[str, Any]] = []
    for item in data.get("intents", []) or []:
        parsed.append(
            {
                "kind": item.get("kind", "other"),
                "description": (item.get("description") or "").strip(),
                "confidence": float(item.get("confidence", 0.5)),
                "topics": topics,
                "mood": mood,
            }
        )

    return parsed


__all__ = ["extract_intents_for_entry"]
