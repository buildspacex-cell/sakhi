from __future__ import annotations

from typing import Any, Dict

from sakhi.apps.api.core.db import q
from sakhi.apps.api.core.person_utils import resolve_person_id
from .classifier import classify_task


def _window_from_forecast(category: str, forecast: Dict[str, Any]) -> tuple[str | None, str]:
    risk = forecast.get("risk_windows") or {}
    emotion_fc = forecast.get("emotion_forecast") or {}
    clarity_fc = forecast.get("clarity_forecast") or {}

    # basic heuristics per category
    if category == "high_focus":
        # prefer high clarity / motivation; avoid confusion window
        window = "late morning"
        if (clarity_fc.get("clarity_score") or 0) > 0.6:
            window = "morning"
        if (risk.get("confusion") or "").lower() not in ("", "none"):
            window = "after confusion window"
        reason = "high focus window based on clarity"
    elif category == "low_energy":
        window = "early afternoon" if (emotion_fc.get("calm") or 0) > 0.4 else "late afternoon"
        reason = "light work during lower energy slots"
    elif category == "creative":
        window = "post-lunch uplift" if (emotion_fc.get("motivation") or 0) > 0.3 else "mid-morning"
        reason = "creative slot aligned to motivation"
    elif category == "emotional":
        window = "calm window"
        if (emotion_fc.get("irritability") or 0) > 0.5:
            window = "after irritability window"
        reason = "emotional safety first"
    elif category == "physical":
        window = "morning" if (emotion_fc.get("energy") or emotion_fc.get("fatigue") or 0) < 0.4 else "evening"
        reason = "match energy for physical task"
    else:
        window = "midday"
        reason = "default medium slot"
    return window, reason


async def compute_routing(person_id: str, task: Dict[str, Any]) -> Dict[str, Any]:
    person_id = await resolve_person_id(person_id) or person_id
    forecast_row = await q(
        "SELECT forecast_state FROM forecast_cache WHERE person_id = $1",
        person_id,
        one=True,
    ) or {}
    forecast_state = forecast_row.get("forecast_state") or {}
    conflict_row = await q(
        "SELECT coherence_state, conflict_state FROM personal_model WHERE person_id = $1",
        person_id,
        one=True,
    ) or {}
    coherence_state = conflict_row.get("coherence_state") or {}
    conflict_state = conflict_row.get("conflict_state") or {}

    classification = task.get("classification") or classify_task(task.get("title") or task.get("text") or "")
    category = classification.get("category") or "medium"
    window, reason = _window_from_forecast(category, forecast_state)

    # adjust reason with coherence/conflict hints
    if (conflict_state.get("conflict_score") or 0) > 0.6:
        reason += "; softened due to conflict pressure"
    if (coherence_state.get("coherence_score") or 1) < 0.4:
        reason += "; guiding due to low coherence"

    return {
        "category": category,
        "recommended_window": window,
        "reason": reason,
        "forecast_snapshot": forecast_state,
    }


__all__ = ["compute_routing"]
