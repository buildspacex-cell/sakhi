from __future__ import annotations

from typing import List, Optional

from .policy_loader import policy


def score_ask(
    dialog_act: str,
    info_gaps: List[str],
    sentiment: Optional[float],
    beat_label: str,
    turn_len: int,
) -> float:
    p = policy()
    act_config = p["dialog_act_weights"].get(dialog_act, {})
    weight = act_config.get("weight", 0.5)
    essential = set(act_config.get("essential_gaps", []))
    gaps = len(essential.intersection(info_gaps))
    info_gain = min(1.0, gaps / 2) * weight

    beat_mod = p["beat_modifiers"].get(beat_label, 0.0)
    overload = 1.0 if turn_len > 800 else (turn_len / 800.0)
    senti_mod = -0.1 if (sentiment is not None and sentiment < -0.5) else 0.0

    score = 0.6 * info_gain + 0.2 * (1 - overload) + 0.2 * beat_mod + senti_mod
    return max(0.0, min(1.0, score))
