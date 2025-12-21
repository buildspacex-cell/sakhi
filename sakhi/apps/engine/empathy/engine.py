from __future__ import annotations

import datetime as dt
from typing import Any, Dict

from sakhi.apps.api.core.db import q, exec as dbexec
from sakhi.apps.api.core.person_utils import resolve_person_id


def _safe_float(val: Any, default: float = 0.0) -> float:
    try:
        return float(val)
    except Exception:
        return default


async def compute_empathy(person_id: str, input_text: str | None = None) -> Dict[str, Any]:
    person_id = await resolve_person_id(person_id) or person_id

    pm_row = await q(
        """
        SELECT emotion_state, forecast_state, conflict_state, coherence_state, empathy_state
        FROM personal_model
        WHERE person_id = $1
        """,
        person_id,
        one=True,
    ) or {}
    continuity_row = await q(
        "SELECT continuity_state FROM session_continuity WHERE person_id = $1",
        person_id,
        one=True,
    ) or {}

    emotion_state = pm_row.get("emotion_state") or {}
    forecast_state = pm_row.get("forecast_state") or {}
    conflict_state = pm_row.get("conflict_state") or {}
    coherence_state = pm_row.get("coherence_state") or {}
    last_emotions = (continuity_row.get("continuity_state") or {}).get("last_emotion_snapshots") or []

    emotion_fc = forecast_state.get("emotion_forecast") or {}
    risk_windows = forecast_state.get("risk_windows") or {}
    conflict_pressure = _safe_float(conflict_state.get("conflict_score"), 0.0)
    coherence_score = _safe_float(coherence_state.get("coherence_score"), 1.0)
    current_emotion = emotion_state.get("mode") or (emotion_fc.get("dominant") if isinstance(emotion_fc, dict) else None) or "neutral"
    intensity = max(
        0.0,
        min(
            1.0,
            abs(_safe_float(emotion_fc.get("fatigue") or emotion_fc.get("irritability") or 0))
            + abs(_safe_float(emotion_fc.get("motivation") or 0)) / 2,
        ),
    )
    trajectory = "rising" if _safe_float(emotion_state.get("drift"), 0) > 0 else "falling" if _safe_float(emotion_state.get("drift"), 0) < 0 else "stable"

    fatigue_high = _safe_float(emotion_fc.get("fatigue") or emotion_fc.get("fatigue_prob"), 0) > 0.65
    irritability_high = _safe_float(emotion_fc.get("irritability") or emotion_fc.get("irritability_prob"), 0) > 0.55
    motivation_high = _safe_float(emotion_fc.get("motivation") or emotion_fc.get("motivation_prob"), 0) > 0.6
    confusion_high = _safe_float((forecast_state.get("clarity_forecast") or {}).get("confusion_score"), 0) > 0.55
    overwhelm_window = (risk_windows.get("overwhelm") or "").lower()

    if fatigue_high:
        pattern = "gentle_grounding"
        instruction = "Acknowledge fatigue softly. Avoid tasks pressure. Offer small relief options."
    elif irritability_high:
        pattern = "non_challenging_validation"
        instruction = "Validate irritation without escalating. Avoid challenges. Maintain calm tone."
    elif overwhelm_window and overwhelm_window != "none":
        pattern = "soft_reassurance"
        instruction = "Simplify choices. Reduce cognitive load. Offer one gentle option at a time."
    elif confusion_high:
        pattern = "clarity_support"
        instruction = "Provide structure. Reduce ambiguity. Offer a clear path forward."
    elif motivation_high:
        pattern = "supportive_uplift"
        instruction = "Recognize motivation. Affirm momentum. Offer next-step clarity."
    else:
        pattern = "neutral_attunement"
        instruction = "Present, balanced tone. Light validation."

    empathy_state = {
        "pattern": pattern,
        "instruction": instruction,
        "emotion_context": {
            "current_emotion": current_emotion,
            "intensity": round(intensity, 3),
            "trajectory": trajectory,
            "coherence_factor": coherence_score,
            "conflict_pressure": conflict_pressure,
            "recent_emotions": last_emotions,
        },
        "updated_at": dt.datetime.utcnow().isoformat(),
    }

    # best-effort persistence
    try:
        await dbexec(
            """
            UPDATE personal_model
            SET empathy_state = $2
            WHERE person_id = $1
            """,
            person_id,
            empathy_state,
        )
    except Exception:
        pass

    return empathy_state


__all__ = ["compute_empathy"]
