from __future__ import annotations

import datetime as dt
from typing import Any, Dict, List

from sakhi.apps.api.core.db import q, exec as dbexec
from sakhi.apps.api.core.person_utils import resolve_person_id


async def compute_tone(person_id: str) -> Dict[str, Any]:
    """Deterministic tone computation based on persona, coherence, conflict, forecast, and emotion."""
    resolved = await resolve_person_id(person_id) or person_id

    pm_row = await q(
        """
        SELECT persona_state, coherence_state, conflict_state, forecast_state, emotion_state
        FROM personal_model
        WHERE person_id = $1
        """,
        resolved,
        one=True,
    ) or {}
    persona_state = pm_row.get("persona_state") or {}
    coherence_state = pm_row.get("coherence_state") or {}
    conflict_state = pm_row.get("conflict_state") or {}
    forecast_state = pm_row.get("forecast_state") or {}
    emotion_state = pm_row.get("emotion_state") or {}

    base_tone = persona_state.get("custom_tone") or "warm"
    modifiers: List[str] = []

    conflict_pressure = float(conflict_state.get("conflict_score") or 0)
    if conflict_pressure > 0.6:
        modifiers.append("de-escalating")

    coherence_map = coherence_state.get("coherence_map") if isinstance(coherence_state, dict) else {}
    clarity = float(coherence_map.get("thought") or coherence_state.get("coherence_score") or 0)
    if clarity < 0.4:
        modifiers.append("guiding")

    emotion_forecast = (forecast_state.get("emotion_forecast") if isinstance(forecast_state, dict) else {}) or {}
    fatigue_prob = float(emotion_forecast.get("fatigue") or 0)
    irritability_prob = float(emotion_forecast.get("irritability") or 0)
    motivation_prob = float(emotion_forecast.get("motivation") or 0)
    if fatigue_prob > 0.6:
        modifiers.append("soft")
    if irritability_prob > 0.5:
        modifiers.append("non-challenging")
    if motivation_prob > 0.6:
        modifiers.append("uplifting")

    mode = (emotion_state.get("mode") or "").lower() if isinstance(emotion_state, dict) else ""
    if mode == "falling" and "soft" not in modifiers:
        modifiers.append("soft")

    final_tone = " + ".join([base_tone] + modifiers) if modifiers else base_tone
    payload = {
        "base": base_tone,
        "modifiers": modifiers,
        "final": final_tone,
        "updated_at": dt.datetime.utcnow().isoformat(),
    }

    try:
        await dbexec(
            "UPDATE personal_model SET tone_state = $2::jsonb, updated_at = NOW() WHERE person_id = $1",
            resolved,
            payload,
        )
    except Exception:
        # best-effort write; do not break turn flow
        pass
    return payload


__all__ = ["compute_tone"]
