from __future__ import annotations

import json
from typing import Any, Dict, List

from sakhi.apps.api.core.llm import call_llm
from sakhi.apps.worker.utils.db import db_find, db_insert


async def run_tone_analysis(person_id: str) -> None:
    reflections: List[Dict[str, Any]] = db_find("reflections", {"user_id": person_id})[:10]
    if not reflections:
        return

    for reflection in reflections:
        content = reflection.get("content")
        if not content:
            continue

        prompt = f"""
Analyze the emotional tone of this reflection text:
"{content}"

Output JSON:
{{
  "dominant_emotion": "calm / sad / inspired / anxious / hopeful / reflective / motivated",
  "tone_style": "warm / gentle / direct / playful / serious",
  "polarity": -1 to +1,
  "energy_level": 0-1
}}
""".strip()

        resp = await call_llm(messages=[{"role": "user", "content": prompt}])
        payload = resp.get("message") if isinstance(resp, dict) else resp
        try:
            tone = json.loads(payload or "{}")
        except json.JSONDecodeError:
            tone = {}

        db_insert(
            "emotional_tones",
            {
                "person_id": person_id,
                "reflection_id": reflection.get("id"),
                "dominant_emotion": tone.get("dominant_emotion"),
                "tone_style": tone.get("tone_style"),
                "polarity": tone.get("polarity", 0.0),
                "energy_level": tone.get("energy_level", 0.5),
            },
        )


__all__ = ["run_tone_analysis"]
