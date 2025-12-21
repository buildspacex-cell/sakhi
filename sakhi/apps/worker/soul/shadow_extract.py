from __future__ import annotations

from typing import Dict, Any

from sakhi.apps.api.core.llm import call_llm

SHADOW_PROMPT = """
Return JSON with exactly these keys:
{
  "shadow_patterns": [],
  "light_patterns": [],
  "conflict_cycles": [],
  "value_friction": []
}
Rules:
- No prose, no explanation.
- shadow_patterns: behaviors or tendencies that hold the user back.
- light_patterns: uplifting/strength patterns.
- conflict_cycles: brief phrases of recurring inner conflicts.
- value_friction: short phrases of value mismatches (value vs action).
- Keep lists concise; omit if not present.
"""


async def extract_shadow_light(text: str) -> Dict[str, Any]:
    """
    Uses LLM router to extract shadow/light/conflict/friction facets.
    """
    try:
        return await call_llm(
            prompt=None,
            messages=[
                {"role": "system", "content": SHADOW_PROMPT},
                {"role": "user", "content": text},
            ],
            schema=None,
            model=None,
        )
    except Exception:
        return {
            "shadow_patterns": [],
            "light_patterns": [],
            "conflict_cycles": [],
            "value_friction": [],
        }


__all__ = ["extract_shadow_light"]
