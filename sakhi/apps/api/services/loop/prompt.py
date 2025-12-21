from __future__ import annotations

from typing import Any, Mapping

import json

SYSTEM = """You are Sakhi, a warm clarity companion.
Layers to honor each turn:
- Hands: propose the smallest useful next step (finite actions).
- Journal: let the user process feelings; you may log reflections.
- Conversation/Tone: keep language empathetic; ask only one critical slot.
- Brain: use the rolling summary to stay coherent.
- Awareness/Breath: if mood is low or turns are long, slow the pace and prefer short actions.
- Soul: prefer options aligned to stated values/goals; note conflicts gently.
Valid actions include: plan_project, create_task, create_event, add_list_item, log_journal, summarize_reflection, search_entities, set_reminder.
Never invent business names. If no tool is available, emit a research task with a suggested query.
"""


def _format_context(ctx: Mapping[str, Any]) -> str:
    try:
        return json.dumps(ctx, default=str)
    except TypeError:
        return str(dict(ctx))


def build_prompt(
    user_text: str,
    ctx: Mapping[str, Any],
    objective: str,
    *,
    clarity_hint: str | None = None,
    personal_model_context: str | None = None,
) -> str:
    summary = ctx.get("summary", "")
    history = ctx.get("history", [])
    hist_str = "\n".join(f"{turn['role'].capitalize()}: {turn['text']}" for turn in history)
    context_blob = _format_context(ctx)
    hint_section = f"Suggested opening from companion: {clarity_hint}\n" if clarity_hint else ""
    personal_section = (
        f"Personal model context:\n{personal_model_context}\n"
        if personal_model_context
        else ""
    )
    return (
        f"Objective: {objective}\n"
        f"Session summary:\n{summary}\n"
        f"Recent turns:\n{hist_str}\n"
        f"Context extras: {context_blob}\n"
        f"{hint_section}"
        f"{personal_section}"
        f"Now, User: {user_text}\n"
        "Assistant:"
    )
