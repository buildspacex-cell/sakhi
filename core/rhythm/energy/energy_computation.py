from typing import Dict, Any, Iterable

from core.rhythm.energy.energy_metrics import (
    average_load,
    average_grounding,
    average_volatility,
    circulation_score,
    depletion_penalty,
    inverse_recovery_rate,
)
from core.rhythm.utils import clamp


def compute_energy_primitives(
    *,
    weekly_elementals: Iterable[Dict[str, Any]],
    recovery_rates: Dict[str, float],
) -> Dict[str, float]:
    """
    Compute deterministic energy primitives from weekly elemental summaries and personal recovery rates.
    weekly_elementals: iterable of summaries (one per dimension) with earth_avg, water_avg, fire_avg, air_avg, ether_avg, volatility.
    recovery_rates: mapping of dimension -> recovery_rate (0..1). Missing values default to 0.5.
    """
    def _clean_summary(s: Dict[str, Any]) -> Dict[str, float]:
        return {
            "earth_avg": float(s.get("earth_avg", 0.0)),
            "water_avg": float(s.get("water_avg", 0.0)),
            "fire_avg": float(s.get("fire_avg", 0.0)),
            "air_avg": float(s.get("air_avg", 0.0)),
            "ether_avg": float(s.get("ether_avg", 0.0)),
            "volatility": float(s.get("volatility", 0.0)),
        }

    summaries = [_clean_summary(s) for s in weekly_elementals]
    if not summaries:
        return {
            "activation_load": 0.0,
            "grounding": 0.0,
            "circulation": 0.0,
            "recovery_efficiency": 0.0,
        }

    act_load = average_load(summaries)
    vol_avg = average_volatility(summaries)
    activation_load = clamp(act_load * (1.0 + vol_avg))

    ground_base = average_grounding(summaries)
    grounding = clamp(ground_base - depletion_penalty(activation_load, ground_base))

    circulation = circulation_score(summaries)

    if recovery_rates:
        inv_rates = [inverse_recovery_rate(recovery_rates.get(dim, 0.5)) for dim in ["body", "mind", "emotion"]]
    else:
        inv_rates = [inverse_recovery_rate(0.5) for _ in range(3)]
    recovery_efficiency = clamp(sum(inv_rates) / len(inv_rates))

    return {
        "activation_load": activation_load,
        "grounding": grounding,
        "circulation": circulation,
        "recovery_efficiency": recovery_efficiency,
    }
