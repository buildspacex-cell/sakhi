from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, List

from sakhi.apps.api.core.llm import call_llm
from sakhi.apps.worker.utils.db import db_find, db_insert, db_upsert


async def run_soul_reasoner(person_id: str) -> None:
    # 1. Pull latest rhythm insights + reflections + journal themes
    rhythm = db_find("rhythm_insights", {"person_id": person_id})[-5:]
    reflections = db_find("reflections", {"user_id": person_id})[-5:]
    themes = db_find("journal_themes", {"user_id": person_id})

    if not themes:
        return

    prompt = f"""
    You are Sakhi's Soul Layer. Integrate user's rhythm, emotional, and thematic data.

    THEMES: {[t.get('theme') for t in themes]}
    RHYTHM: {[r.get('summary') for r in rhythm]}
    REFLECTIONS: {[r.get('content') for r in reflections]}

    Find meaningful cross-theme relationships, harmony/conflicts, and actionable alignment suggestions.
    """

    llm_response = await call_llm(messages=[{"role": "user", "content": prompt}])
    content = llm_response.get("message") if isinstance(llm_response, dict) else llm_response
    try:
        insights = json.loads(content or "{}")
    except json.JSONDecodeError:
        return

    for link in insights.get("links", []):
        payload = {
            "person_id": person_id,
            "theme_a": link.get("a"),
            "theme_b": link.get("b"),
            "relation": link.get("relation"),
            "strength": link.get("strength"),
            "created_at": datetime.utcnow().isoformat(),
        }
        db_insert("theme_links", payload)

    for state in insights.get("states", []):
        payload = {
            "person_id": person_id,
            "theme": state.get("theme"),
            "clarity_score": state.get("clarity", 0.0),
            "emotional_state": state.get("emotional_state", {}),
        }
        db_upsert("theme_states", payload)

    for reflection in insights.get("reflections", []):
        payload = {
            "person_id": person_id,
            "kind": "reflection",
            "message": reflection.get("message"),
            "confidence": reflection.get("confidence", 0.6),
            "created_at": datetime.utcnow().isoformat(),
        }
        db_insert("insights", payload)


__all__ = ["run_soul_reasoner"]
