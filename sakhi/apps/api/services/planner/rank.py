from __future__ import annotations

from typing import Dict, List


async def rank_intents(person_id: str, intents: List[Dict[str, any]]) -> List[Dict[str, any]]:
    """
    Lightweight ranking using priority + horizon urgency + energy match.
    """

    def score(intent: Dict[str, any]) -> float:
        base = float(intent.get("priority") or 1)
        time_window = intent.get("time_window") or {}
        kind = str(time_window.get("kind") or "unspecified").lower()
        timeline_bonus = {
            "today": 1.0,
            "tomorrow": 0.8,
            "this_week": 0.6,
            "this_month": 0.3,
            "this_quarter": 0.1,
            "unspecified": 0.0,
        }.get(kind, 0.0)
        energy = str(intent.get("energy_hint") or "").lower()
        energy_bonus = {"high": 0.2, "medium": 0.1, "low": 0.0}.get(energy, 0.0)
        return base + timeline_bonus + energy_bonus

    return sorted(intents, key=score, reverse=True)


__all__ = ["rank_intents"]
