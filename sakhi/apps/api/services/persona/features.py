from __future__ import annotations

import json
from typing import Any, Dict

from sakhi.apps.api.core.llm import call_llm


async def analyze_persona_features(text: str) -> Dict[str, Any]:
    prompt = (
        "Analyze the following user message for persona signals. "
        "Return ONLY JSON with keys: "
        '{"warmth":0-1,"reflectiveness":0-1,"humor":0-1,"expressiveness":0-1,"tone_bias":"warm"|'
        '"neutral"|"direct"|null}.\n\n'
        f"{text}"
    )

    response = await call_llm(messages=[{"role": "user", "content": prompt}], model="gpt-4o-mini")
    payload = response if isinstance(response, str) else json.dumps(response)
    try:
        data = json.loads(payload)
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    return {
        "warmth": None,
        "reflectiveness": None,
        "humor": None,
        "expressiveness": None,
        "tone_bias": None,
    }


__all__ = ["analyze_persona_features"]
