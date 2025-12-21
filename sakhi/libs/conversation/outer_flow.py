"""Helpers for managing multi-turn outer intent clarification flows."""

from __future__ import annotations

import re
from typing import Any, Dict, Optional, Tuple

from .clarify_outer import next_question_with_step

OUTER_STEPS = ["timeline", "preferences", "constraints", "criteria", "assets"]
EXIT_PHRASES = (
    "that's all",
    "thats all",
    "nothing else",
    "no thanks",
    "no thank you",
    "we're good",
    "were good",
    "all good",
    "done",
    "forget it",
    "never mind",
    "nevermind",
)


def ensure_flow(metadata: Dict[str, Any]) -> Dict[str, Any]:
    """Ensure the metadata contains a mutable outer_flow state dict."""

    flow = metadata.setdefault("outer_flow", {})
    flow.setdefault("features", {})
    flow.setdefault("answers", {})
    flow.setdefault("notes", {})
    flow.setdefault("awaiting_step", None)
    flow.setdefault("last_question", None)
    flow.setdefault("closed", False)
    flow.setdefault("permission_offered", False)
    flow.setdefault("ready_for_plan", False)
    flow.setdefault("history", [])
    return flow


def record_user_message(flow: Dict[str, Any], message: str) -> None:
    _append_history(flow, "user", message)


def record_assistant_message(flow: Dict[str, Any], message: str) -> None:
    _append_history(flow, "assistant", message)


def merge_classification(flow: Dict[str, Any], new_features: Dict[str, Any]) -> Dict[str, Any]:
    """Blend classifier output into the stored feature snapshot."""

    features = flow.setdefault("features", {})
    if not new_features:
        return features

    features.update({k: v for k, v in new_features.items() if k != "g_mvs" and k != "timeline"})

    # Merge timeline information
    if "timeline" in new_features and isinstance(new_features["timeline"], dict):
        stored_timeline = features.setdefault("timeline", {})
        stored_timeline.update({k: v for k, v in new_features["timeline"].items() if v})

    # Merge g_mvs flags
    if "g_mvs" in new_features and isinstance(new_features["g_mvs"], dict):
        stored_g_mvs = features.setdefault(
            "g_mvs",
            {
                "target_horizon": False,
                "current_position": False,
                "constraints": False,
                "criteria": False,
                "assets_blockers": False,
            },
        )
        for key, value in new_features["g_mvs"].items():
            if isinstance(value, bool) and value:
                stored_g_mvs[key] = True

    if "tags" in new_features and isinstance(new_features["tags"], list) and new_features["tags"]:
        features["tags"] = list(dict.fromkeys(new_features["tags"]))

    return features


def build_classifier_context(flow: Dict[str, Any], *, base_prompt: str | None = None) -> str:
    """Construct a contextual prompt for intent classification."""

    parts: list[str] = []
    base = (base_prompt or "").strip()
    if base:
        parts.append(base)

    history = flow.get("history")
    if isinstance(history, list) and history:
        convo_lines = []
        for item in history[-6:]:
            role = item.get("role")
            content = str(item.get("content") or "").strip()
            if not content:
                continue
            prefix = "Assistant" if role == "assistant" else "User"
            convo_lines.append(f"{prefix}: {content}")
        if convo_lines:
            parts.append("\n".join(convo_lines))

    awaiting = flow.get("awaiting_step")
    if awaiting:
        parts.append(f"Awaiting detail for: {awaiting}.")

    features = flow.get("features") or {}
    intent_type = features.get("intent_type")
    if intent_type:
        parts.append(f"Intent type so far: {intent_type}.")
    timeline = features.get("timeline")
    if isinstance(timeline, dict) and timeline.get("horizon"):
        parts.append(f"Known timeline horizon: {timeline.get('horizon')}.")

    return "\n".join(part for part in parts if part)


def infer_timeline_horizon(answer: str) -> Optional[str]:
    """Heuristically map a short answer to a timeline horizon."""

    normalized = answer.strip().lower()
    tokens = set(normalized.split())
    if not normalized:
        return None
    if "today" in tokens or "tonight" in tokens:
        return "today"
    if "tomorrow" in tokens:
        return "tomorrow"
    if "weekend" in normalized:
        return "weekend"
    if "next week" in normalized or "week" in tokens:
        return "week"
    if "next month" in normalized or "month" in tokens:
        return "month"
    if "next quarter" in normalized or "quarter" in tokens:
        return "quarter"
    if "next year" in normalized or "year" in tokens:
        return "year"
    if re.search(r"\b\d{4}-\d{2}-\d{2}\b", normalized):
        return "custom_date"
    if re.search(r"\b\d{1,2}/\d{1,2}\b", normalized):
        return "custom_date"
    if "soon" in tokens:
        return "week"
    if "later" in tokens:
        return "month"
    return None


def apply_answer(flow: Dict[str, Any], answer: str) -> None:
    """Update the flow state with the user's answer to the pending step."""

    if flow.get("closed"):
        return

    awaiting = flow.get("awaiting_step")
    features = flow.setdefault("features", {})
    g_mvs = features.setdefault(
        "g_mvs",
        {
            "target_horizon": False,
            "current_position": False,
            "constraints": False,
            "criteria": False,
            "assets_blockers": False,
        },
    )

    normalized = answer.strip().lower()
    if normalized and any(phrase in normalized for phrase in EXIT_PHRASES):
        flow["closed"] = True
        flow["awaiting_step"] = None
        return

    flow.setdefault("answers", {})[awaiting or "unknown"] = answer
    flow.setdefault("notes", {})[awaiting or "unknown"] = answer
    _append_history(flow, "user", answer)

    if awaiting == "timeline":
        horizon = infer_timeline_horizon(answer)
        features["timeline"] = {"horizon": horizon or "custom_date"}
        if horizon == "custom_date":
            features["timeline"]["target_date"] = answer.strip()
        g_mvs["target_horizon"] = True
    elif awaiting == "preferences":
        tokens = [token.strip() for token in re.split(r"[;,]", answer) if token.strip()]
        if not tokens:
            tokens = [answer.strip()] if answer.strip() else []
        if tokens:
            features["tags"] = tokens
        ctx = features.get("context")
        if not isinstance(ctx, dict):
            ctx = {}
        features["context"] = ctx
        if answer.strip():
            ctx.setdefault("location", answer.strip())
        flow.setdefault("notes", {})["preferences"] = answer
    elif awaiting == "constraints":
        g_mvs["constraints"] = True
        flow.setdefault("notes", {})["constraints"] = answer
    elif awaiting == "criteria":
        g_mvs["criteria"] = True
        flow.setdefault("notes", {})["criteria"] = answer
    elif awaiting == "assets":
        g_mvs["assets_blockers"] = True
        flow.setdefault("notes", {})["assets"] = answer
    elif awaiting == "permission":
        if normalized in {"yes", "y", "yeah", "sure", "ok", "okay", "please do", "go ahead", "sounds good"}:
            flow.setdefault("notes", {})["permission"] = "affirm"
            flow["ready_for_plan"] = True
            flow["closed"] = True
        elif normalized in {"no", "nope", "not now", "later", "maybe later", "no thanks", "no thank you"}:
            flow.setdefault("notes", {})["permission"] = "decline"
            flow["ready_for_plan"] = False
            flow["closed"] = True
        else:
            flow.setdefault("notes", {})["permission"] = answer

    flow["awaiting_step"] = None


def prepare_next_question(flow: Dict[str, Any]) -> Tuple[str, Optional[str]]:
    """Determine the next follow-up question and the associated step."""

    if flow.get("closed"):
        flow["last_question"] = None
        flow["awaiting_step"] = None
        flow["ready_for_plan"] = True
        return "", None

    features = flow.setdefault("features", {})
    question, step = next_question_with_step(features)
    if question:
        flow["last_question"] = question
        flow["awaiting_step"] = step
        flow["ready_for_plan"] = False
        _append_history(flow, "assistant", question)
    else:
        flow["last_question"] = None
        flow["awaiting_step"] = None
        flow["ready_for_plan"] = True
    return question, step


def mark_closed(flow: Dict[str, Any]) -> None:
    """Mark the flow as closed/completed."""

    flow["closed"] = True
    flow["awaiting_step"] = None


def is_active(flow: Dict[str, Any]) -> bool:
    """Return True if the flow is still gathering details."""

    return not flow.get("closed")

def _append_history(flow: Dict[str, Any], role: str, content: str) -> None:
    if not content:
        return
    history = flow.setdefault("history", [])
    history.append({"role": role, "content": content})
    if len(history) > 6:
        del history[0]
