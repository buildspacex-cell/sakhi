import logging
from datetime import datetime, timezone
from typing import Dict

from core.rhythm.constants import MIN_VAL, MAX_VAL, VECTOR_DECAY, CONFIDENCE_DECAY

log = logging.getLogger(__name__)


def now_utc() -> datetime:
    return datetime.now(tz=timezone.utc)


def clamp(value: float) -> float:
    return max(MIN_VAL, min(MAX_VAL, value))


def normalize_distribution(values: Dict[str, float]) -> Dict[str, float]:
    total = sum(values.values())
    if total <= 0:
        return {k: 0.0 for k in values}
    return {k: clamp(v / total) for k, v in values.items()}


def decay_weight(age_days: int, magnitude: float, confidence: float) -> float:
    """Weight magnitude by age-based decay and confidence decay."""
    vector_factor = VECTOR_DECAY ** age_days
    confidence_factor = CONFIDENCE_DECAY ** age_days
    return magnitude * confidence * vector_factor * confidence_factor
