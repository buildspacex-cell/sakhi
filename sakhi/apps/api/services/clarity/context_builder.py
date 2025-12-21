from __future__ import annotations

import json
from typing import Any, Dict, List

from sakhi.apps.api.core.db import dbfetchrow
from sakhi.apps.api.core.telemetry import log_trace_event
from sakhi.apps.api.services.memory.context_select import fetch_relevant_long_term


async def build_conversation_context(person_id: str, latest_message: str) -> str:
    """Construct prompt context combining short-term signals with relevant long-term slices."""
    person = await dbfetchrow(
        """
        SELECT short_term
        FROM personal_model
        WHERE person_id = $1
    """,
        person_id,
    )

    short_term = _ensure_dict((person or {}).get("short_term"))
    relevant_longterm = await fetch_relevant_long_term(person_id, latest_message)

    longterm_for_tone: List[Dict[str, Any]] = []
    for item in relevant_longterm:
        if not isinstance(item, dict):
            continue
        text_value = item.get("content") or ""
        if not isinstance(text_value, str):
            try:
                text_value = json.dumps(text_value, ensure_ascii=False)
            except (TypeError, ValueError):
                text_value = str(text_value)
        longterm_for_tone.append({"text": text_value})

    tone_hint = derive_tone(longterm_for_tone)

    context_prompt = f"""
You are Sakhi, the clarity & rhythm companion who remembers this person deeply.

Relevant Long-Term Insights:
{json.dumps(relevant_longterm, ensure_ascii=False, indent=2)}

Current Situation:
{json.dumps(short_term, ensure_ascii=False, indent=2)}

Latest Message:
"{latest_message}"

Respond as Sakhi:
- Empathize with emotion and body cues.
- Weave awareness of their patterns, goals, rhythm.
- Stay calm, warm, reflective, never prescriptive.
Tone: {tone_hint}.
"""
    await log_trace_event(
        "memory.longterm_used",
        {"count": len(relevant_longterm)},
    )
    return context_prompt


def derive_tone(relevant_longterm: List[Dict[str, Any]]) -> str:
    """Infer a tone hint by scanning the retrieved long-term snippets."""
    if not relevant_longterm:
        return "balanced and warm"

    combined = " ".join(
        str(entry.get("text") or "")
        for entry in relevant_longterm
        if isinstance(entry, dict)
    ).lower()

    if "tired" in combined:
        return "gentle and restorative"
    if "fear" in combined or "anxious" in combined:
        return "reassuring and steady"
    if "enthusiasm" in combined:
        return "encouraging but grounded"
    return "balanced and warm"


def _ensure_dict(value: Any) -> dict:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return {}
    return {}
