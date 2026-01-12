from __future__ import annotations

import datetime as dt
from math import sqrt
from typing import Any, Dict, List

TONES = {
    "stress": {"valence": -0.7, "activation": 0.7},
    "calm": {"valence": 0.4, "activation": 0.2},
    "frustration": {"valence": -0.6, "activation": 0.6},
    "relief": {"valence": 0.5, "activation": 0.3},
    "anxiety": {"valence": -0.7, "activation": 0.8},
    "contentment": {"valence": 0.6, "activation": 0.3},
    "overwhelm": {"valence": -0.8, "activation": 0.8},
    "gratitude": {"valence": 0.7, "activation": 0.4},
    "irritability": {"valence": -0.5, "activation": 0.6},
    "hope": {"valence": 0.6, "activation": 0.5},
}

NEGATIVE_VALENCE_THRESHOLD = -0.2
HIGH_ACTIVATION_THRESHOLD = 0.6
HIGH_VOLATILITY_THRESHOLD = 0.4
PERSISTENCE_THRESHOLD = 0.05


def _clamp(val: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, val))


def extract_emotion_state(entries: List[Dict[str, Any]], window_days: int) -> Dict[str, Any]:
    """
    Deterministic emotional signal extraction from text content.
    entries: list of {"content": str, "created_at": datetime}
    """
    if not entries:
        return {}

    tone_counts: Dict[str, int] = {k: 0 for k in TONES.keys()}
    valence_samples: List[float] = []

    for row in entries:
        text = (row.get("content") or "").lower()
        matched = False
        for tone, attrs in TONES.items():
            if tone in text:
                tone_counts[tone] += 1
                valence_samples.append(attrs["valence"])
                matched = True
        if not matched:
            # fallback: no tone hit; skip
            continue

    total_hits = sum(tone_counts.values())
    if total_hits == 0:
        return {}

    # Aggregate valence/activation
    valence = sum(valence_samples) / len(valence_samples)
    activation = 0.0
    for tone, count in tone_counts.items():
        if count > 0:
            activation += TONES[tone]["activation"] * count
    activation = activation / total_hits

    # Volatility = stddev of valence samples normalized
    mean_v = valence
    variance = sum((v - mean_v) ** 2 for v in valence_samples) / len(valence_samples)
    volatility = sqrt(variance)
    volatility = _clamp(volatility, 0.0, 1.0)

    # Persistence = fraction of window containing repeated tones
    persistence: Dict[str, float] = {}
    for tone, count in tone_counts.items():
        if count > 0:
            persistence[tone] = _clamp(count / len(entries), 0.0, 1.0)

    dominant = sorted(persistence.items(), key=lambda kv: kv[1], reverse=True)
    dominant_tones = [kv[0] for kv in dominant[:3]]

    conditions = {
        "persistent_negative": (
            valence <= NEGATIVE_VALENCE_THRESHOLD
            and any(
                tone in persistence and persistence[tone] >= PERSISTENCE_THRESHOLD
                for tone in ("stress", "overwhelm", "frustration", "anxiety")
            )
        ),
        "high_activation": activation >= HIGH_ACTIVATION_THRESHOLD,
        "high_volatility": volatility >= HIGH_VOLATILITY_THRESHOLD,
    }

    return {
        "valence": _clamp(valence, -1.0, 1.0),
        "activation": _clamp(activation, 0.0, 1.0),
        "volatility": volatility,
        "persistence": persistence,
        "dominant_tones": dominant_tones,
        "conditions": conditions,
        "window_days": window_days,
        "updated_at": dt.datetime.utcnow().isoformat(),
    }
