from __future__ import annotations

import math
import datetime as dt
from typing import Any, Dict, List

from sakhi.apps.api.core.db import q
from sakhi.apps.api.core.person_utils import resolve_person_id


def _linear_regression_slope(values: List[float]) -> float:
    n = len(values)
    if n < 2:
        return 0.0
    x_mean = (n - 1) / 2
    y_mean = sum(values) / n
    numerator = sum((i - x_mean) * (v - y_mean) for i, v in enumerate(values))
    denominator = sum((i - x_mean) ** 2 for i in range(n)) or 1.0
    return numerator / denominator


def compute_emotion_loop(person_id: str, sentiments: List[float] | None = None) -> Dict[str, Any]:
    """
    Compute drift/volatility/inertia from recent sentiments.
    """
    if sentiments is None:
        sentiments = []
    mode = "stable"
    trend = _linear_regression_slope(sentiments) if sentiments else 0.0
    volatility = 0.0
    inertia = 0.0
    is_recovery = False

    if len(sentiments) >= 2:
        mean = sum(sentiments) / len(sentiments)
        volatility = math.sqrt(sum((v - mean) ** 2 for v in sentiments) / len(sentiments))
        inertia = sum(abs(b - a) for a, b in zip(sentiments, sentiments[1:])) / (len(sentiments) - 1)
        # simple previous trend using first half
        mid = max(2, len(sentiments) // 2)
        prev_trend = _linear_regression_slope(sentiments[:mid])
        is_recovery = trend > 0 and prev_trend < 0

    POS_T = 0.05
    NEG_T = -0.05
    VOL_T = 0.5
    if volatility > VOL_T:
        mode = "volatile"
    elif is_recovery:
        mode = "recovery"
    elif trend > POS_T:
        mode = "rising"
    elif trend < NEG_T:
        mode = "falling"
    else:
        mode = "stable"

    return {
        "mode": mode,
        "trend": round(trend, 4),
        "drift": round(trend, 4),
        "inertia": round(inertia, 4),
        "volatility": round(volatility, 4),
        "is_recovery": is_recovery,
        "updated_at": dt.datetime.utcnow().isoformat(),
    }


async def compute_emotion_loop_for_person(person_id: str) -> Dict[str, Any]:
    person_id = await resolve_person_id(person_id) or person_id
    rows = await q(
        """
        SELECT triage
        FROM memory_episodic
        WHERE person_id = $1
        ORDER BY updated_at DESC
        LIMIT 20
        """,
        person_id,
    )
    sentiments: List[float] = []
    for row in rows or []:
        triage = row.get("triage") or {}
        mood = (triage.get("slots") or {}).get("mood_affect") if isinstance(triage, dict) else {}
        sentiments.append(float((mood or {}).get("score") or 0))
    return compute_emotion_loop(person_id, sentiments)


__all__ = ["compute_emotion_loop", "compute_emotion_loop_for_person"]
