from __future__ import annotations

import json
from typing import Any, Dict, Optional

from sakhi.apps.api.core.config_loader import get_policy, get_prompt
from sakhi.apps.api.core.llm import LLMResponseError, call_llm
from sakhi.apps.api.core.llm_schemas import PhraseOutput
from sakhi.apps.api.core.response_policy import should_suggest
from sakhi.apps.api.core.suggestions import has_recent_duplicate, record_suggestion
from sakhi.apps.api.services.consolidate import mark_surfaced


async def generate_phrase(person_id: str, ctx: Dict[str, Any], llm_payload: Dict[str, Any] | None) -> Dict[str, Any]:
    state_vector = ctx.get("state_vector") or {}
    state_confidence = None
    if isinstance(state_vector, dict):
        state_confidence = state_vector.get("confidence")

    numeric_conf = state_confidence if isinstance(state_confidence, (int, float)) else None
    policy_decision = await should_suggest(
        person_id,
        state_confidence=numeric_conf,
        need=ctx.get("intent_need"),
    )
    if not policy_decision.allow:
        return {
            "lines": [],
            "style": "silence",
            "confidence": float(numeric_conf or 0.0),
            "meta": {"skipped": True, "reason": policy_decision.reason, **policy_decision.meta},
        }

    prompt_def = get_prompt("phrase")
    messages = []

    system_content = prompt_def.get("system") or "You are Sakhi, a reflective, supportive companion."
    context_fragments: list[str] = []
    themes_summary = ctx.get("themes_summary")
    recent_notes = ctx.get("recent_notes")
    if themes_summary:
        context_fragments.append(f"Themes: {themes_summary}")
    if recent_notes:
        context_fragments.append(f"Recent notes:\n{recent_notes}")
    if context_fragments:
        system_content = system_content.strip() + "\n\nContext:\n" + "\n".join(context_fragments)
    messages.append({"role": "system", "content": system_content})

    for shot in prompt_def.get("few_shots", []):
        user = shot.get("input")
        assistant = shot.get("output")
        if user:
            messages.append({"role": "user", "content": json.dumps(user, ensure_ascii=False)})
        if assistant:
            messages.append({"role": "assistant", "content": json.dumps(assistant, ensure_ascii=False)})

    payload = {
        "need": ctx.get("intent_need"),
        "input": ctx.get("input_text"),
        "state": state_vector,
        "anchors": ctx.get("support", {}).get("aspects", []),
        "options": (llm_payload or {}).get("options"),
        "short_horizon": ctx.get("short_horizon"),
        "themes_summary": themes_summary,
        "recent_notes": recent_notes,
    }
    messages.append({"role": "user", "content": json.dumps(payload, ensure_ascii=False)})

    policy = get_policy("response_policy")
    min_phrase_conf = float(policy.get("min_phrase_confidence", 0.0))
    anti_repeat_hours = float(policy.get("anti_repeat_hours", 0.0))

    try:
        result: PhraseOutput = await call_llm(messages=messages, schema=PhraseOutput)
    except LLMResponseError:
        return {
            "lines": [],
            "style": "silence",
            "confidence": float(numeric_conf or 0.0),
            "meta": {"skipped": True, "reason": "llm_error"},
        }

    phrase_conf = float(result.confidence)
    if phrase_conf < min_phrase_conf:
        return {
            "lines": [],
            "style": result.style,
            "confidence": phrase_conf,
            "meta": {
                "skipped": True,
                "reason": "phrase_confidence_low",
                "min_required": min_phrase_conf,
            },
        }

    lines = [line.strip() for line in result.lines if isinstance(line, str) and line.strip()]
    if not lines:
        return {
            "lines": [],
            "style": result.style,
            "confidence": phrase_conf,
            "meta": {"skipped": True, "reason": "empty_phrase"},
        }

    primary_line = lines[0]
    if anti_repeat_hours > 0 and await has_recent_duplicate(person_id, primary_line, window_hours=anti_repeat_hours):
        return {
            "lines": [],
            "style": result.style,
            "confidence": phrase_conf,
            "meta": {
                "skipped": True,
                "reason": "duplicate_recent",
                "window_hours": anti_repeat_hours,
            },
        }

    await record_suggestion(
        person_id,
        suggestion=primary_line,
        style=result.style,
        confidence=phrase_conf,
        payload={
            "need": ctx.get("intent_need"),
            "anchors": ctx.get("support", {}).get("aspects", []),
            "state_confidence": numeric_conf,
            "options": (llm_payload or {}).get("options"),
            "themes_summary": themes_summary,
        },
    )

    primary_theme: Optional[str] = ctx.get("primary_theme")
    if primary_theme:
        await mark_surfaced(person_id, f"theme:{primary_theme}")

    payload = result.dict()
    payload["lines"] = lines
    payload["meta"] = {
        "skipped": False,
        "reason": "delivered",
        "policy": policy_decision.meta,
    }
    return payload
