from __future__ import annotations

import json
from typing import Any, Dict, List

from sakhi.apps.api.core.llm import call_llm
from sakhi.apps.worker.utils.db import db_find, db_insert


async def run_persona_updater(person_id: str) -> None:
    convo_turns: List[Dict[str, Any]] = db_find("conversation_turns", {"user_id": person_id})[:20]
    if not convo_turns:
        return

    user_msgs = [turn.get("text") for turn in convo_turns if turn.get("role") == "user" and turn.get("text")]
    assistant_msgs = [turn.get("text") for turn in convo_turns if turn.get("role") == "assistant" and turn.get("text")]

    prompt = f"""
Analyze the overall communication style and tone from the following dialogues.

USER MESSAGES:
{json.dumps(user_msgs, indent=2)}

SAKHI MESSAGES:
{json.dumps(assistant_msgs, indent=2)}

Describe the evolving persona traits that Sakhi should adopt to stay emotionally attuned:
- tone_bias: e.g. warm, formal, lighthearted
- expressiveness: 0–1
- humor: 0–1
- reflectiveness: 0–1
- warmth: 0–1
Output JSON.
""".strip()

    resp = await call_llm(messages=[{"role": "user", "content": prompt}])
    payload = resp.get("message") if isinstance(resp, dict) else resp
    try:
        traits = json.loads(payload or "{}")
    except json.JSONDecodeError:
        traits = {}

    modes = db_find("persona_modes", {"person_id": person_id})
    active_mode = modes[0] if modes else {}
    mode_name = active_mode.get("mode_name")
    if mode_name == "Supportive":
        traits["warmth"] = min(1.0, float(traits.get("warmth", 0.8)) + 0.1)
    elif mode_name == "Action":
        traits["conciseness"] = min(1.0, float(traits.get("conciseness", 0.6)) + 0.1)
    elif mode_name == "Light":
        traits["humor"] = min(1.0, float(traits.get("humor", 0.3)) + 0.15)

    db_insert(
        "persona_traits",
        {
            "person_id": person_id,
            "style_profile": traits,
            "tone_bias": traits.get("tone_bias"),
            "expressiveness": traits.get("expressiveness", 0.5),
            "humor": traits.get("humor", 0.3),
            "reflectiveness": traits.get("reflectiveness", 0.7),
            "warmth": traits.get("warmth", 0.8),
            "last_updated": "now",
        },
    )


__all__ = ["run_persona_updater"]
