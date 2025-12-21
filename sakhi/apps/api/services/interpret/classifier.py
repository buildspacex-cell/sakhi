from __future__ import annotations

from typing import Optional


def classify_archetype(text: str, summary: Optional[str]) -> str:
    sample = (text or "").lower()
    if any(keyword in sample for keyword in ("why", "reflect", "feel", "think", "emotion")):
        return "reflect"
    if any(keyword in sample for keyword in ("plan", "need", "schedule", "project", "task")):
        return "act"
    if any(keyword in sample for keyword in ("search", "find", "lookup", "research")):
        return "research"
    if any(keyword in sample for keyword in ("who", "what", "where", "when", "how")):
        return "curious"
    if summary and "goal" in summary.lower():
        return "act"
    return "dialog"
