"""Dosha state computation — deterministic keyword-based scoring.

Computes a dosha (Vata/Pitta/Kapha) state vector from text, emotional
signals, rhythm signals, and optional body data.  Pure computation —
no DB, no LLM.

Dosha mapping:
- Vata (Adaptive): scattered, anxious, variable, creative, quick-thinking
- Pitta (Performance): intense, focused, irritable, driven, goal-oriented
- Kapha (Conservation): steady, slow, heavy, calm, resistant to change
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

# ---------------------------------------------------------------------------
# Keyword vocabularies
# ---------------------------------------------------------------------------

VATA_KEYWORDS: list[str] = [
    "scattered", "anxious", "worry", "racing", "overwhelmed", "distracted",
    "creative", "ideas", "brainstorm", "change", "varied", "variable",
    "restless", "insomnia", "couldn't sleep", "mind racing", "jumping",
]

PITTA_KEYWORDS: list[str] = [
    "intense", "focused", "productive", "deadline", "accomplished", "driven",
    "irritable", "frustrated", "angry", "impatient", "critical", "perfection",
    "competitive", "goal", "achievement", "pushed", "hard work",
]

KAPHA_KEYWORDS: list[str] = [
    "steady", "calm", "grounded", "stable", "routine", "consistent",
    "tired", "heavy", "sluggish", "drained", "stuck", "unmotivated",
    "rest", "comfort", "relaxed", "slow", "peaceful",
]

KEYWORD_WEIGHT: float = 0.15

# ---------------------------------------------------------------------------
# Core computation
# ---------------------------------------------------------------------------


def compute_dosha_state(
    summary_text: str,
    emotional_state: dict[str, Any],
    rhythm_state: dict[str, Any],
    body_dosha: dict[str, float] | None = None,
) -> dict[str, Any]:
    """Compute a dosha state vector from text + signals.

    Returns ``{"dosha": {vata, pitta, kapha}, "confidence": float,
    "computed_at": str}`` where dosha scores are normalised to sum to 1.0.

    If *body_dosha* is provided (e.g. from HealthKit), blends 60 % journal-
    derived scores with 40 % body-derived scores.
    """
    if not summary_text or not summary_text.strip():
        return {
            "dosha": {"vata": 0.33, "pitta": 0.33, "kapha": 0.34},
            "confidence": 0.3,
        }

    lowered = summary_text.lower()
    scores: dict[str, float] = {"vata": 0.0, "pitta": 0.0, "kapha": 0.0}

    # Keyword scoring
    for kw in VATA_KEYWORDS:
        if kw in lowered:
            scores["vata"] += KEYWORD_WEIGHT
    for kw in PITTA_KEYWORDS:
        if kw in lowered:
            scores["pitta"] += KEYWORD_WEIGHT
    for kw in KAPHA_KEYWORDS:
        if kw in lowered:
            scores["kapha"] += KEYWORD_WEIGHT

    # Integrate emotional state signals
    if emotional_state:
        activation = float(emotional_state.get("activation", 0.5))
        stability = float(emotional_state.get("stability", 0.5))
        valence = float(emotional_state.get("valence", 0.0))

        if activation > 0.6 and valence < -0.2:
            scores["pitta"] += 0.2
        if activation < 0.4:
            scores["kapha"] += 0.15
        if stability < 0.4:
            scores["vata"] += 0.2

    # Integrate rhythm state signals
    if rhythm_state:
        energy = float(rhythm_state.get("energy_level", 0.5))
        structure = float(rhythm_state.get("structure", 0.5))

        if energy < 0.4:
            scores["kapha"] += 0.15
        if energy > 0.6 and structure < 0.4:
            scores["vata"] += 0.15

    # Normalise journal-derived scores to sum to 1.0
    total = sum(scores.values())
    if total > 0:
        scores = {k: round(v / total, 2) for k, v in scores.items()}
    else:
        scores = {"vata": 0.33, "pitta": 0.33, "kapha": 0.34}

    # Blend with body dosha if available (60 % journal + 40 % body)
    if body_dosha and all(k in body_dosha for k in ("vata", "pitta", "kapha")):
        body_total = sum(body_dosha.values())
        if body_total > 0:
            norm_body = {k: v / body_total for k, v in body_dosha.items()}
            scores = {
                k: round(scores[k] * 0.6 + norm_body.get(k, 0.33) * 0.4, 3)
                for k in scores
            }
            blend_total = sum(scores.values())
            if blend_total > 0:
                scores = {k: round(v / blend_total, 2) for k, v in scores.items()}

    # Ensure exactly 1.0
    adjustment = 1.0 - sum(scores.values())
    scores["kapha"] = round(scores["kapha"] + adjustment, 2)

    confidence = min(0.85, 0.3 + total * 0.1)
    if body_dosha:
        confidence = min(0.95, confidence + 0.1)

    return {
        "dosha": scores,
        "confidence": round(confidence, 2),
        "computed_at": datetime.now(timezone.utc).isoformat(),
    }
