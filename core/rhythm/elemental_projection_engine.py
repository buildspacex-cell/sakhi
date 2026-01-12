from datetime import timedelta
from typing import Dict, Any

from core.rhythm.constants import STM_TTL_DAYS
from core.rhythm.utils import clamp, normalize_distribution, now_utc


def _zero_dim() -> Dict[str, float]:
    return {"earth": 0.0, "water": 0.0, "fire": 0.0, "air": 0.0, "ether": 0.0}


def _zero_vector() -> Dict[str, Dict[str, float]]:
    return {
        "body": _zero_dim(),
        "mind": _zero_dim(),
        "emotion": _zero_dim(),
    }


def project_to_elements(signal: Dict[str, Any]) -> Dict[str, Any]:
    """
    Deterministically maps a neutral signal into elemental projections.
    Returns magnitude + distribution per dimension, plus confidence and expiry.
    """
    if not signal or "type" not in signal:
        raise ValueError("signal.type is required")
    ts = signal.get("ts") or now_utc()
    confidence = clamp(signal.get("confidence", 1.0))

    raw_vector = _zero_vector()

    sig_type = signal["type"]
    # Core mappings (additive, per dimension)
    if sig_type == "dryness":
        raw_vector["body"]["air"] += 0.2 * confidence

    if sig_type == "overactivation":
        raw_vector["mind"]["fire"] += 0.2 * confidence
        raw_vector["emotion"]["air"] += 0.1 * confidence

    if sig_type == "evening_clustering":
        raw_vector["mind"]["air"] += 0.15 * confidence

    if sig_type == "recovery_gap":
        raw_vector["body"]["earth"] += 0.1 * confidence
        raw_vector["emotion"]["water"] += 0.1 * confidence

    vector = {}
    for dimension, elements in raw_vector.items():
        magnitude = sum(elements.values())
        distribution = normalize_distribution(elements) if magnitude > 0 else _zero_dim()
        vector[dimension] = {
            "distribution": distribution,
            "magnitude": clamp(magnitude),
        }

    expires_at = ts + timedelta(days=STM_TTL_DAYS)
    return {
        "vector": vector,
        "confidence": confidence,
        "expires_at": expires_at,
    }
