from __future__ import annotations

import datetime as dt
from statistics import mean
from typing import Any, Dict, List

from sakhi.apps.api.core.db import q
from sakhi.apps.api.core.person_utils import resolve_person_id


def _safe_mean(values: List[float]) -> float:
    return mean(values) if values else 0.0


async def compute_forecast(person_id: str) -> Dict[str, Any]:
    person_id = await resolve_person_id(person_id) or person_id

    # pull supporting signals
    pm_row = await q(
        """
        SELECT identity_state, conflict_state, coherence_state, pattern_sense, forecast_state
        FROM personal_model
        WHERE person_id = $1
        """,
        person_id,
        one=True,
    ) or {}
    identity_state = pm_row.get("identity_state") or {}
    conflict_state = pm_row.get("conflict_state") or {}
    coherence_state = pm_row.get("coherence_state") or {}
    pattern_sense = pm_row.get("pattern_sense") or {}

    emotion_row = await q(
        "SELECT emotion_loop FROM memory_episodic WHERE person_id = $1 ORDER BY ts DESC LIMIT 30",
        person_id,
    ) or []
    emotion_points = []
    for row in emotion_row:
        loop = row.get("emotion_loop") if isinstance(row, dict) else {}
        if loop and isinstance(loop, dict):
            emotion_points.append(float(loop.get("trend") or loop.get("drift") or 0))
    emotion_slope = _safe_mean(emotion_points)
    volatility = _safe_mean([abs(p) for p in emotion_points])

    intents = await q(
        "SELECT intent_name, strength, trend FROM intent_evolution WHERE person_id = $1",
        person_id,
    ) or []
    intent_strengths = [float(i.get("strength") or 0) for i in intents]

    tasks = await q(
        "SELECT status, auto_priority, energy_cost, updated_at FROM tasks WHERE user_id = $1 ORDER BY updated_at DESC LIMIT 20",
        person_id,
    ) or []
    completions = [t for t in tasks if (t.get("status") or "").lower() == "done"]

    # emotion forecast probabilities (simple heuristics)
    calm_prob = max(0.1, 0.6 - volatility)
    irritability_prob = max(0.1, 0.2 + max(0, -emotion_slope))
    fatigue_prob = max(0.1, 0.2 + volatility / 2)
    motivation_prob = max(0.1, 0.2 + max(0, emotion_slope))
    focus_prob = max(0.1, 0.3 + _safe_mean(intent_strengths) * 0.3)

    # clarity forecast
    fragmentation = float(coherence_state.get("fragmentation_index") or 0)
    drift_slope = float(identity_state.get("drift_score") or 0)
    clarity_score = max(0.0, min(1.0, 0.8 - fragmentation - max(0, -drift_slope)))
    confusion_score = max(0.0, min(1.0, 0.4 + fragmentation))

    # behavior forecast
    adherence = max(0.0, min(1.0, 0.6 - fragmentation + len(completions) * 0.02))
    procrastination_window = "afternoon" if irritability_prob > 0.3 else "evening"
    action_window = "late morning" if motivation_prob > 0.3 else "midday"

    # risk windows
    risk_windows = {
        "overwhelm": "early afternoon" if fragmentation > 0.3 else "none",
        "low_energy": "morning" if fatigue_prob > 0.3 else "none",
        "confusion": "midday" if confusion_score > 0.4 else "none",
    }

    summary_parts = []
    if fatigue_prob > 0.35 and calm_prob < 0.4:
        summary_parts.append("slow start expected")
    if motivation_prob > 0.35:
        summary_parts.append("productive burst likely late morning")
    if irritability_prob > 0.3:
        summary_parts.append("friction expected in afternoon")
    summary_text = "; ".join(summary_parts) if summary_parts else "stable day expected"

    return {
        "emotion_forecast": {
            "calm": calm_prob,
            "irritability": irritability_prob,
            "fatigue": fatigue_prob,
            "motivation": motivation_prob,
            "focus": focus_prob,
        },
        "clarity_forecast": {
            "clarity_score": clarity_score,
            "confusion_score": confusion_score,
        },
        "behavior_forecast": {
            "adherence": adherence,
            "procrastination_window": procrastination_window,
            "action_window": action_window,
        },
        "risk_windows": risk_windows,
        "summary_text": summary_text,
        "updated_at": dt.datetime.utcnow().isoformat(),
    }


__all__ = ["compute_forecast"]
