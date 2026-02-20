"""Context tag extraction — deterministic keyword-to-tag mapping.

Extracts lightweight semantic tags from text for longitudinal learning.
Each tag carries a dimension, signal key, polarity, and intensity.

Pure computation — no DB, no LLM.
"""

from __future__ import annotations


def extract_context_tags(text: str) -> list[dict[str, str]]:
    """Extract up to 5 context tags from *text*.

    Each tag is a dict with keys: ``dimension``, ``signal_key``,
    ``polarity``, ``intensity``.
    """
    if not isinstance(text, str) or not text.strip():
        return []

    lowered = text.lower()
    tags: list[dict[str, str]] = []

    def add_tag(
        dimension: str,
        signal_key: str,
        polarity: str,
        intensity: str = "medium",
    ) -> None:
        if len(tags) >= 5:
            return
        tags.append(
            {
                "dimension": dimension,
                "signal_key": signal_key,
                "polarity": polarity,
                "intensity": intensity,
            }
        )

    if any(k in lowered for k in ["sleep", "rested", "fatigue", "tired", "exhausted"]):
        add_tag("body", "energy_rest", "neutral")
    if any(k in lowered for k in ["back pain", "stiff neck", "ache", "sore"]):
        add_tag("body", "discomfort", "up")
    if any(k in lowered for k in ["stress", "anxiety", "overwhelm"]):
        add_tag("emotion", "stress", "up")
    if any(k in lowered for k in ["calm", "relief", "grounded"]):
        add_tag("emotion", "calm", "down")
    if any(k in lowered for k in ["energized", "productive", "focus"]):
        add_tag("energy", "activation", "up")
    if any(k in lowered for k in ["sluggish", "drained", "tired"]):
        add_tag("energy", "activation", "down")
    if any(k in lowered for k in ["meeting", "deadline", "calls", "workload"]):
        add_tag("work", "load", "up")
    if any(k in lowered for k in ["break", "walk", "rest"]):
        add_tag("work", "recovery", "down")
    if any(k in lowered for k in ["clarity", "plan", "organized"]):
        add_tag("mind", "clarity", "up")
    if any(k in lowered for k in ["scattered", "distracted", "fragmented"]):
        add_tag("mind", "clarity", "down")

    return tags
