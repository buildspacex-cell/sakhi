from __future__ import annotations

import datetime
from typing import Any, Mapping

from sakhi.apps.api.core.db import q, exec as dbexec
from sakhi.apps.api.core.person_utils import resolve_person_id


def _kw_score(text: str, keywords: list[str]) -> float:
    lowered = text.lower()
    return float(sum(1 for k in keywords if k in lowered)) / max(len(keywords), 1)


async def compute_microreg(person_id: str, input_text: str) -> dict[str, Any]:
    """
    Deterministic micro-regulation state.
    """
    resolved = await resolve_person_id(person_id) or person_id
    try:
        row: Mapping[str, Any] = await q(
            "SELECT emotion_state, forecast_state, conflict_state, coherence_state FROM personal_model WHERE person_id = $1",
            resolved,
            one=True,
        ) or {}
    except Exception:
        row = {}

    emotion_state = row.get("emotion_state") or {}
    forecast_state = row.get("forecast_state") or {}
    conflict_state = row.get("conflict_state") or {}
    coherence_state = row.get("coherence_state") or {}

    last_snapshots = (forecast_state.get("emotion_snapshots") or [])[:3] if isinstance(forecast_state, dict) else []
    prev_vals = [snap.get("intensity", 0.5) for snap in last_snapshots if isinstance(snap, dict)]
    prev_avg = sum(prev_vals) / len(prev_vals) if prev_vals else 0.5

    fatigue_prob = (forecast_state.get("emotion_forecast") or {}).get("fatigue_prob") or 0.0
    irritability_prob = (forecast_state.get("emotion_forecast") or {}).get("irritability_prob") or 0.0
    motivation_prob = (forecast_state.get("emotion_forecast") or {}).get("motivation_prob") or 0.0
    overwhelm_window = (forecast_state.get("risk_windows") or {}).get("overwhelm_window")
    confusion_score = (forecast_state.get("clarity_forecast") or {}).get("confusion_score") or 0.0

    kw_fatigue = _kw_score(input_text, ["tired", "exhausted", "fatigue", "sleepy"])
    kw_irritability = _kw_score(input_text, ["annoyed", "frustrated", "irritated", "angry"])
    kw_confusion = _kw_score(input_text, ["confused", "lost", "unclear"])
    kw_motivation = _kw_score(input_text, ["excited", "motivated", "ready", "pumped"])

    base_intensity = 0.5 + (kw_motivation * 0.2) - (kw_fatigue * 0.2) + (motivation_prob * 0.1) - (fatigue_prob * 0.1)
    base_intensity = min(1.0, max(0.0, base_intensity))

    amplitude = abs(base_intensity - prev_avg)
    if amplitude > 0.5 or (conflict_state.get("conflict_score") or 0) > 0.4:
        risk = "high"
    elif amplitude > 0.25:
        risk = "medium"
    else:
        risk = "low"

    if base_intensity < prev_avg - 1e-6:
        shift = "downward"
    elif base_intensity > prev_avg + 1e-6:
        shift = "upward"
    elif len(prev_vals) > 1 and (max(prev_vals) - min(prev_vals)) > 0.3:
        shift = "volatile"
    else:
        shift = "flat"

    pattern = "neutral_balance"
    if (fatigue_prob > 0.35 or kw_fatigue > 0.1) and shift == "downward":
        pattern = "grounding"
    elif (irritability_prob > 0.35 or kw_irritability > 0.1) and shift == "volatile":
        pattern = "stabilizing"
    elif overwhelm_window and risk == "high":
        pattern = "simplification"
    elif (confusion_score > 0.3 or kw_confusion > 0.1) and shift == "downward":
        pattern = "clarity_microstructure"
    elif (motivation_prob > 0.35 or kw_motivation > 0.1) and shift == "upward":
        pattern = "supportive_momentum"

    instructions = {
        "grounding": "Use slow pacing; reduce cognitive load; avoid many options.",
        "stabilizing": "Keep tone calm and even; avoid complex requests; reduce reactivity.",
        "simplification": "Offer one simple step; avoid branching choices; keep reply short.",
        "clarity_microstructure": "Provide small structure; avoid abstract language; keep steps clear.",
        "supportive_momentum": "Affirm motivation; keep tone uplifting but steady; offer one next step.",
        "neutral_balance": "Balanced tone; mild validation; ordinary pacing.",
    }

    payload = {
        "pattern": pattern,
        "instruction": instructions.get(pattern, instructions["neutral_balance"]),
        "shift": shift,
        "amplitude": amplitude,
        "risk": risk,
        "updated_at": datetime.datetime.utcnow().isoformat(),
    }

    try:  # best effort persistence
        await dbexec("UPDATE personal_model SET microreg_state = $2 WHERE person_id = $1", resolved, payload)
    except Exception:
        pass

    return payload


__all__ = ["compute_microreg"]
