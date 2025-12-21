from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any, Callable, Iterable, List


def recency_decay(days: float, tau: float) -> float:
    return math.exp(-max(0.0, days) / float(tau))


def fatigue_penalty(last_surfaced_at: datetime | None) -> float:
    if last_surfaced_at is None:
        return 0.0
    delta_hours = (datetime.now(timezone.utc) - last_surfaced_at).total_seconds() / 3600.0
    return 0.2 if delta_hours < 24 else 0.0


def score_stm(sim: float, days: float, intent: float, domain: float, pref: float, fatigue: float) -> float:
    rec = recency_decay(days, tau=7)
    return 0.45 * sim + 0.25 * rec + 0.10 * intent + 0.10 * domain + 0.10 * pref - 0.10 * fatigue


def score_mtm(sim: float, days: float, salience: float, significance: float, intent: float, domain: float, fatigue: float) -> float:
    rec = recency_decay(days, tau=21)
    return 0.30 * sim + 0.15 * rec + 0.20 * salience + 0.25 * significance + 0.10 * intent + 0.10 * domain - 0.10 * fatigue


def score_ltm(sim: float, days: float, salience: float, significance: float, pref: float, domain: float, fatigue: float) -> float:
    rec = recency_decay(days, tau=60)
    return 0.25 * sim + 0.10 * rec + 0.20 * salience + 0.30 * significance + 0.10 * pref + 0.10 * domain - 0.05 * fatigue


THRESH_SOFT = 0.55


def dedupe_keep_top(
    candidates: Iterable[dict[str, Any]],
    cosine: Callable[[List[float], List[float]], float],
    *,
    sim_threshold: float = 0.9,
    k: int = 3,
) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    for candidate in sorted(candidates, key=lambda item: item.get("score", 0.0), reverse=True):
        vec = candidate.get("vec")
        if not isinstance(vec, list):
            continue
        if any(cosine(vec, item.get("vec") or []) >= sim_threshold for item in selected if isinstance(item.get("vec"), list)):
            continue
        selected.append(candidate)
        if len(selected) >= k:
            break
    return selected


def should_surface(score: float, *, intent: bool = False, domain: bool = False) -> bool:
    return score >= THRESH_SOFT or (score >= 0.50 and (intent or domain))


__all__ = [
    "recency_decay",
    "fatigue_penalty",
    "score_stm",
    "score_mtm",
    "score_ltm",
    "dedupe_keep_top",
    "should_surface",
]
