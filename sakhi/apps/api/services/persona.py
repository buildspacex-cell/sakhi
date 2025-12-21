from __future__ import annotations

from typing import Any, Dict


def select_archetype_from_context(person_model: Dict[str, Any] | None) -> str:
    """
    Choose an interaction persona based on personal model context.
    """
    if not isinstance(person_model, dict):
        return "companion"

    emotion = str(person_model.get("emotion", "")).lower()
    patterns = " ".join(str(v).lower() for v in person_model.get("patterns", []) if isinstance(v, str))
    preferred_style = str(person_model.get("style", "")).lower()

    if "grounded" in preferred_style or "reflective" in emotion:
        return "sage"
    if "playful" in preferred_style or "creative" in patterns:
        return "muse"
    if "tired" in emotion or "low" in emotion:
        return "caretaker"
    if "focused" in patterns or "driven" in preferred_style:
        return "coach"

    return "companion"
