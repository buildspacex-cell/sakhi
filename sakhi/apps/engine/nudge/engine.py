from __future__ import annotations

import datetime as dt
from typing import Any, Dict

from sakhi.apps.api.core.db import q
from sakhi.apps.api.core.person_utils import resolve_person_id


def _latest_nudge_ts(nudge_state: Dict[str, Any]) -> dt.datetime | None:
    ts = (nudge_state or {}).get("last_sent_at")
    if not ts:
        return None
    try:
        return dt.datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except Exception:
        return None


def _cooldown_active(nudge_state: Dict[str, Any]) -> bool:
    last_ts = _latest_nudge_ts(nudge_state)
    if not last_ts:
        return False
    return (dt.datetime.utcnow() - last_ts).total_seconds() < 3 * 3600


def _tone_prefix(tone_state: Dict[str, Any]) -> str:
    final = (tone_state or {}).get("final")
    if final:
        return final
    base = (tone_state or {}).get("base") or "warm"
    modifiers = (tone_state or {}).get("modifiers") or []
    return base if not modifiers else f"{base} + {' + '.join(modifiers)}"


async def compute_nudge(person_id: str, forecast_state: Dict[str, Any] | None, tone_state: Dict[str, Any] | None) -> Dict[str, Any]:
    person_id = await resolve_person_id(person_id) or person_id
    forecast_state = forecast_state or {}

    pm_row = await q(
        "SELECT nudge_state FROM personal_model WHERE person_id = $1",
        person_id,
        one=True,
    ) or {}
    nudge_state = pm_row.get("nudge_state") or {}

    result: Dict[str, Any] = {
        "category": None,
        "message": None,
        "forecast_snapshot": forecast_state,
        "should_send": False,
    }

    if _cooldown_active(nudge_state):
        return result

    emotion_fc = forecast_state.get("emotion_forecast") or {}
    clarity_fc = forecast_state.get("clarity_forecast") or {}
    behavior_fc = forecast_state.get("behavior_forecast") or {}
    risk_windows = forecast_state.get("risk_windows") or {}

    fatigue_prob = float(emotion_fc.get("fatigue") or emotion_fc.get("fatigue_prob") or 0)
    irritability_prob = float(emotion_fc.get("irritability") or emotion_fc.get("irritability_prob") or 0)
    confusion_score = float(clarity_fc.get("confusion_score") or 0)
    procrastination_prob = float(behavior_fc.get("procrastination_prob") or 0)
    overwhelm_window = (risk_windows.get("overwhelm") or "").lower()

    tone_label = _tone_prefix(tone_state or {})

    category = None
    if fatigue_prob > 0.65:
        category = "energy"
        message = f"{tone_label}: You may feel a small dip soon. A 2-min stretch could help."
    elif irritability_prob > 0.55:
        category = "calming"
        message = f"{tone_label}: You might run into some friction later. Try slower pacing."
    elif confusion_score > 0.55:
        category = "clarity"
        message = f"{tone_label}: Clarity may be low later. Keep big decisions for morning."
    elif procrastination_prob > 0.6:
        category = "focus"
        message = f"{tone_label}: You may drift off-task soon. Want to reorganize your plan?"
    elif overwhelm_window and overwhelm_window != "none":
        category = "grounding"
        message = f"{tone_label}: Overwhelm possible soon. Want me to simplify?"
    else:
        return result

    result.update(
        {
            "category": category,
            "message": message,
            "forecast_snapshot": forecast_state,
            "should_send": True,
        }
    )
    return result


__all__ = ["compute_nudge"]
