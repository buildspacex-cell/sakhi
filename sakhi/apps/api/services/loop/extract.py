from __future__ import annotations

import json
from typing import Dict, List, Tuple


def extract_actions_and_reply(llm_out: str) -> Tuple[str, List[Dict]]:
    reply = llm_out
    actions: List[Dict] = []

    if "```json" not in llm_out:
        return reply, actions

    try:
        json_section = llm_out.split("```json", 1)[1].split("```", 1)[0]
        payload = json.loads(json_section)
        if isinstance(payload, dict) and "actions" in payload and isinstance(payload["actions"], list):
            actions = payload["actions"]
    except (IndexError, json.JSONDecodeError):
        actions = []

    reply = llm_out.split("```json", 1)[0].strip()
    return reply, actions
