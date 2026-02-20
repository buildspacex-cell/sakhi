"""Guna state computation — deterministic keyword-based scoring.

Computes a guna (Sattva/Rajas/Tamas) operating-mode vector from text
and emotional signals.  Pure computation — no DB, no LLM.

Guna mapping (Operating Modes):
- Sattva (Clarity): balanced, clear, peaceful, aligned
- Rajas (Activation): active, driven, restless, ambitious
- Tamas (Recovery): heavy, slow, foggy, resistant
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

# ---------------------------------------------------------------------------
# Keyword vocabularies
# ---------------------------------------------------------------------------

SATTVA_KEYWORDS: list[str] = [
    "clarity", "clear", "peaceful", "balanced", "aligned", "centered",
    "grateful", "content", "harmony", "flow", "present", "mindful",
    "insight", "understanding", "calm focus", "serene",
]

RAJAS_KEYWORDS: list[str] = [
    "busy", "active", "productive", "rushing", "deadline", "meetings",
    "ambitious", "driven", "restless", "anxious", "scattered", "racing",
    "stressed", "overwhelmed", "too much", "multitasking",
]

TAMAS_KEYWORDS: list[str] = [
    "tired", "heavy", "sluggish", "unmotivated", "foggy", "drained",
    "stuck", "resistant", "avoidant", "procrastinating", "low energy",
    "need rest", "exhausted", "burnt out", "numb",
]

KEYWORD_WEIGHT: float = 0.2

# ---------------------------------------------------------------------------
# Core computation
# ---------------------------------------------------------------------------


def compute_guna_state(
    summary_text: str,
    emotional_state: dict[str, Any],
) -> dict[str, Any]:
    """Compute a guna state vector from text + emotional signals.

    Returns ``{"sattva": float, "rajas": float, "tamas": float,
    "confidence": float, "computed_at": str}`` where the three guna
    scores are normalised to sum to 1.0.
    """
    if not summary_text or not summary_text.strip():
        return {
            "sattva": 0.33,
            "rajas": 0.34,
            "tamas": 0.33,
            "confidence": 0.3,
        }

    lowered = summary_text.lower()
    scores: dict[str, float] = {"sattva": 0.0, "rajas": 0.0, "tamas": 0.0}

    # Keyword scoring
    for kw in SATTVA_KEYWORDS:
        if kw in lowered:
            scores["sattva"] += KEYWORD_WEIGHT
    for kw in RAJAS_KEYWORDS:
        if kw in lowered:
            scores["rajas"] += KEYWORD_WEIGHT
    for kw in TAMAS_KEYWORDS:
        if kw in lowered:
            scores["tamas"] += KEYWORD_WEIGHT

    # Integrate emotional state
    if emotional_state:
        valence = float(emotional_state.get("valence", 0.0))
        activation = float(emotional_state.get("activation", 0.5))
        stability = float(emotional_state.get("stability", 0.5))

        if valence > 0.2 and stability > 0.6:
            scores["sattva"] += 0.25
        if activation > 0.6 and stability < 0.5:
            scores["rajas"] += 0.25
        if activation < 0.4 and valence < 0:
            scores["tamas"] += 0.25

    # Normalise to sum to 1.0
    total = sum(scores.values())
    if total > 0:
        scores = {k: round(v / total, 2) for k, v in scores.items()}
    else:
        scores = {"sattva": 0.33, "rajas": 0.34, "tamas": 0.33}

    # Ensure exactly 1.0
    adjustment = 1.0 - sum(scores.values())
    scores["tamas"] = round(scores["tamas"] + adjustment, 2)

    confidence = min(0.85, 0.3 + total * 0.1)

    return {
        "sattva": scores["sattva"],
        "rajas": scores["rajas"],
        "tamas": scores["tamas"],
        "confidence": round(confidence, 2),
        "computed_at": datetime.now(timezone.utc).isoformat(),
    }
