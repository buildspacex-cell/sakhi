from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Dict

try:
    import pandas as pd
except ModuleNotFoundError:  # pragma: no cover - optional dependency
    pd = None  # type: ignore[assignment]


def detect_circadian_pattern(df: pd.DataFrame) -> Dict[str, Any]:
    grouped = df.groupby("phase")["energy_level"].mean()
    best_phase = grouped.idxmax()
    worst_phase = grouped.idxmin()
    return {
        "pattern_type": "circadian",
        "summary": f"Highest energy during {best_phase}, lowest at {worst_phase}.",
        "recommendation": f"Schedule deep work in the {best_phase} slot.",
        "confidence": round(abs(grouped[best_phase] - grouped[worst_phase]) / 10, 2),
    }


def detect_infradian_cycle(df: pd.DataFrame) -> Dict[str, Any] | None:
    # rolling 28-day average for cycle-linked patterns
    if len(df) < 14:
        return None
    df = df.copy()
    df["rolling_mean"] = df["energy_level"].rolling(5, min_periods=3).mean()
    dip_days = df[df["rolling_mean"] < df["rolling_mean"].mean() - 1]
    if dip_days.empty:
        return None
    return {
        "pattern_type": "infradian",
        "summary": "Recurring low-energy phase roughly every 27–30 days.",
        "recommendation": "Plan lighter work and rest during this phase.",
        "confidence": 0.8,
    }


__all__ = ["detect_circadian_pattern", "detect_infradian_cycle"]
