from __future__ import annotations

from typing import Dict


def classify_task(text: str) -> Dict[str, str | float]:
    t = (text or "").lower()
    category = "medium"
    if any(k in t for k in ["analyze", "report", "study", "learn", "deep"]):
        category = "high_focus"
    elif any(k in t for k in ["write", "plan", "organize"]):
        category = "medium"
    elif any(k in t for k in ["call", "email", "clean", "sort"]):
        category = "low_energy"
    elif any(k in t for k in ["design", "brainstorm", "create"]):
        category = "creative"
    elif any(k in t for k in ["journal", "feel", "discuss", "emotional"]):
        category = "emotional"
    elif any(k in t for k in ["walk", "gym", "exercise", "run"]):
        category = "physical"
    return {"category": category, "confidence": 1.0}


__all__ = ["classify_task"]
