from __future__ import annotations

import json
from typing import Any, Dict, List

from sakhi.apps.api.core.llm import call_llm
from sakhi.apps.worker.utils.db import db_find, db_insert, db_update


async def run_persona_mode_detector(person_id: str) -> None:
    turns = db_find("conversation_turns", {"user_id": person_id})[:10]
    rhythm = db_find("rhythm_insights", {"person_id": person_id})[:3]
    if not turns:
        return

    prompt = f"""
You are Sakhi’s situational detector.
Based on the following dialogues and rhythm summaries,
infer which mode is most appropriate now:
- Reflective (deep introspection)
- Action (focus, planning)
- Supportive (emotional care)
- Light (reset, ease, humor)

DATA:
{json.dumps({"turns": turns, "rhythm": rhythm}, indent=2)}

Respond with JSON:
{{
  "mode": "Reflective",
  "activation_score": 0.78,
  "signals": [
    {{"type": "emotion", "value": "tired", "confidence": 0.8}},
    {{"type": "intent", "value": "clarity", "confidence": 0.7}}
  ]
}}
""".strip()

    response = await call_llm(messages=[{"role": "user", "content": prompt}])
    payload = response.get("message") if isinstance(response, dict) else response
    try:
        data = json.loads(payload or "{}")
    except json.JSONDecodeError:
        data = {}

    for signal in data.get("signals", []):
        db_insert(
            "situational_signals",
            {
                "person_id": person_id,
                "signal_source": "conversation",
                "signal_type": signal.get("type"),
                "signal_value": signal.get("value"),
                "confidence": signal.get("confidence", 0.5),
            },
        )

    db_update(
        "persona_modes",
        {"person_id": person_id},
        {
            "mode_name": data.get("mode", "Reflective"),
            "activation_score": data.get("activation_score", 0.5),
            "last_activated": "now",
        },
    )


__all__ = ["run_persona_mode_detector"]
