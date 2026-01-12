from typing import Dict, Iterable

from core.rhythm.utils import clamp


def average_load(summaries: Iterable[Dict[str, float]]) -> float:
    vals = [s["fire_avg"] + s["air_avg"] for s in summaries]
    return sum(vals) / len(vals) if vals else 0.0


def average_grounding(summaries: Iterable[Dict[str, float]]) -> float:
    vals = [s["earth_avg"] + s["water_avg"] for s in summaries]
    return sum(vals) / len(vals) if vals else 0.0


def average_volatility(summaries: Iterable[Dict[str, float]]) -> float:
    vals = [s["volatility"] for s in summaries]
    return sum(vals) / len(vals) if vals else 0.0


def variance(values):
    if not values:
        return 0.0
    mean = sum(values) / len(values)
    return sum((v - mean) ** 2 for v in values) / len(values)


def circulation_score(summaries: Iterable[Dict[str, float]]) -> float:
    magnitudes = [
        s["earth_avg"] + s["water_avg"] + s["fire_avg"] + s["air_avg"] + s["ether_avg"]
        for s in summaries
    ]
    var = variance(magnitudes)
    return clamp(1.0 - var)


def depletion_penalty(activation_load: float, grounding_base: float) -> float:
    # Penalize when activation meaningfully exceeds grounding reserves.
    gap = max(0.0, activation_load - grounding_base)
    return clamp(gap * 0.5)


def inverse_recovery_rate(recovery_rate: float) -> float:
    # Higher rate means slower recovery; invert and clamp to [0,1].
    return clamp(1.0 - recovery_rate)
