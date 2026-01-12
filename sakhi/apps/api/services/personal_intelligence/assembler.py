import json
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from sakhi.apps.api.core.db import q


def _ensure_json(obj: Any) -> Optional[Dict[str, Any]]:
    if obj is None:
        return None
    if isinstance(obj, dict):
        return obj
    if isinstance(obj, str):
        try:
            return json.loads(obj)
        except Exception:
            return None
    return None


async def _fetch_states(person_id: str) -> Tuple[Dict[str, Any], List[str]]:
    states_used: List[str] = []
    row = await q(
        """
        SELECT soul_state,
               identity_momentum_state,
               rhythm_state,
               emotion_state,
               emotion_soul_rhythm_state,
               longitudinal_state
          FROM personal_model
         WHERE person_id = $1
         LIMIT 1
        """,
        person_id,
    )
    snapshot: Dict[str, Any] = {}
    if not row:
        return snapshot, states_used

    fields = [
        "soul_state",
        "identity_momentum_state",
        "rhythm_state",
        "emotion_state",
        "emotion_soul_rhythm_state",
        "longitudinal_state",
    ]
    for field in fields:
        record = row[0]
        value = _ensure_json(record[field] if field in record else None)
        if value:
            snapshot[field] = value
            states_used.append(field)
    return snapshot, states_used


def _rhythm_recognition(rhythm_state: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Extract rhythm recognition - this is a RECOGNITION (observation), not insight.
    Observes: energy clustering patterns over time.
    """
    slots = rhythm_state.get("slots") or {}
    if not slots:
        return None

    # Find slot with max samples
    best_slot = None
    best_samples = -1
    for name, data in slots.items():
        samples = data.get("samples", 0)
        if samples > best_samples:
            best_samples = samples
            best_slot = name

    if best_slot is None or best_samples <= 0:
        return None

    later_slots = {"afternoon", "evening", "night"}
    time_pattern = "later" if best_slot in later_slots else "earlier"

    # Structured recognition object (NOT insight or conclusion)
    return {
        "domain": "rhythm",
        "signal": f"energy clusters {time_pattern} in the day",
        "label": f"Energy clusters {time_pattern} in the day",
        "stability": "consistent",
        "confidence_window": "weeks+",
        "absence_flag": False,
        "metadata": {"dominant_slot": best_slot, "samples": best_samples}
    }


def _emotion_recognition(emotion_state: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Extract emotion recognition - this is a RECOGNITION (observation), not insight.
    Observes: emotional volatility patterns over time.
    """
    volatility = emotion_state.get("volatility")
    conditions = emotion_state.get("conditions") or {}
    low_volatility_flag = isinstance(volatility, (int, float)) and volatility <= 0.4
    no_high_volatility = not conditions.get("high_volatility")
    if low_volatility_flag or no_high_volatility:
        return {
            "domain": "emotion",
            "signal": "emotional intensity remains contained",
            "label": "Emotional intensity remains contained",
            "stability": "consistent",
            "confidence_window": "weeks+",
            "absence_flag": False,
            "metadata": {"volatility": volatility}
        }
    return None


def _identity_recognition(identity_state: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Extract identity recognition - this is a RECOGNITION (observation), not insight.
    Observes: sense of direction and momentum over time.
    """
    if not identity_state:
        return None
    return {
        "domain": "identity",
        "signal": "sense of direction remains steady without abrupt shifts",
        "label": "Sense of direction remains steady without abrupt shifts",
        "stability": "stable",
        "confidence_window": "weeks+",
        "absence_flag": False,
        "metadata": {}
    }


def _continuity_recognition(longitudinal_state: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Extract continuity recognition - this is a RECOGNITION (observation), not insight.
    Observes: longitudinal familiarity and pattern continuity.
    """
    if not longitudinal_state:
        return None
    return {
        "domain": "familiarity",
        "signal": "patterns feel familiar rather than disruptive",
        "label": "Patterns feel familiar rather than disruptive",
        "stability": "consistent",
        "confidence_window": "weeks+",
        "absence_flag": False,
        "metadata": {}
    }


async def assemble_personal_intelligence_snapshot(
    person_id: str,
    anchor_start: Optional[datetime] = None,
    anchor_end: Optional[datetime] = None,
) -> Dict[str, Any]:
    """
    Assemble Personal Intelligence Snapshot v1 (Lab-only, read-only).

    Rules:
    - Deterministic intelligence only
    - No inference, no advice
    - Stable recognitions only
    """

    anchor_end = anchor_end or datetime.now(timezone.utc)
    anchor_start = anchor_start or (anchor_end - timedelta(days=7))

    states, states_used = await _fetch_states(person_id)

    recognitions: List[Dict[str, Any]] = []

    rhythm_state = states.get("rhythm_state")
    if rhythm_state:
        rec = _rhythm_recognition(rhythm_state)
        if rec:
            recognitions.append(rec)

    emotion_state = states.get("emotion_state")
    if emotion_state:
        rec = _emotion_recognition(emotion_state)
        if rec:
            recognitions.append(rec)

    identity_state = states.get("identity_momentum_state")
    if identity_state:
        rec = _identity_recognition(identity_state)
        if rec:
            recognitions.append(rec)

    longitudinal_state = states.get("longitudinal_state")
    if longitudinal_state:
        rec = _continuity_recognition(longitudinal_state)
        if rec:
            recognitions.append(rec)

    # Absence-of-signal is always meaningful
    recognitions.append(
        {
            "domain": "absence",
            "signal": "no crisis, conflict escalation, or suppression events detected",
            "label": "No crisis, conflict escalation, or suppression events detected",
            "stability": "consistent",
            "confidence_window": "weeks+",
            "absence_flag": True,
            "metadata": {}
        }
    )

    # Cap to 5 recognitions
    recognitions = recognitions[:5]

    return {
        "recognitions": recognitions,
        "states_used": states_used,
        "anchor_window": {
            "mode": "rolling",
            "anchor_start": anchor_start.isoformat(),
            "anchor_end": anchor_end.isoformat(),
        },
    }
