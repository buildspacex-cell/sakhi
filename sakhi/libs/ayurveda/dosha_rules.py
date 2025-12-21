from __future__ import annotations

from typing import Dict


def rhythm_modifiers(dosha_vec: Dict[str, float]) -> Dict[str, object]:
    """Return schedule adjustments derived from dosha proportions."""

    v = float(dosha_vec.get("vata", 0.0) or 0.0)
    p = float(dosha_vec.get("pitta", 0.0) or 0.0)
    k = float(dosha_vec.get("kapha", 0.0) or 0.0)
    modifiers: Dict[str, object] = {
        "wind_down_delta_min": 0,
        "midday_break_min": 0,
        "morning_activation": "none",
    }
    if v > 0.6:
        modifiers["wind_down_delta_min"] = 30
    if p > 0.6:
        modifiers["midday_break_min"] = 15
    if k > 0.6:
        modifiers["morning_activation"] = "walk-10m"
    return modifiers
