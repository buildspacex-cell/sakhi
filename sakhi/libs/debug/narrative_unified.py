from __future__ import annotations

from typing import Any, Dict


def build_unified_narrative(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Build a human-readable narrative used by journaling and conversation flows.
    """

    text = payload.get("input_text") or ""
    reply = payload.get("reply_text") or ""
    triage = payload.get("triage") or {}
    reasoning = payload.get("reasoning") or {}
    memory_context = payload.get("memory_context", "")
    intents = payload.get("intents") or []
    topics = payload.get("topics") or []
    emotion = payload.get("emotion") or {}
    personal_model = payload.get("personal_model") or {}
    planner = payload.get("planner") or {}
    layer = payload.get("layer") or "unknown"

    story = []
    if text:
        story.append(f"You expressed: “{text}”.")
    if intents:
        story.append(f"The message indicates intentions around {', '.join(str(i) for i in intents)}.")
    if emotion:
        tone = emotion.get("label") if isinstance(emotion, dict) else emotion
        story.append(f"The emotional tone detected was: {tone}.")
    if topics:
        story.append(f"This relates to themes/topics such as {', '.join(str(t) for t in topics)}.")
    if triage:
        story.append("The system extracted structural meaning (time windows, tasks, context).")
    if memory_context:
        story.append("Relevant past memories were pulled in to give context.")
    if reasoning:
        story.append("Higher-level reasoning looked for patterns, contradictions, and opportunities.")
    if personal_model:
        story.append("Your personal model was updated based on new observations.")
    if planner:
        story.append("Planning logic reviewed whether any actionable next steps were implied.")
    if reply:
        story.append(f"Sakhi responded with: “{reply}”.")

    return {
        "story": " ".join(story),
        "inputs": {"text": text, "emotion": emotion, "intents": intents},
        "interpretation": triage,
        "reasoning_used": reasoning,
        "memory_used": memory_context,
        "personal_model": personal_model,
        "topics": topics,
        "planner": planner,
        "layer": layer,
    }


__all__ = ["build_unified_narrative"]
