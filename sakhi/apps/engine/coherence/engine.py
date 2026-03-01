from __future__ import annotations

import datetime as dt
import json
from statistics import mean
from typing import Any, Dict, List

from sakhi.apps.api.core.db import q
from sakhi.apps.api.core.person_utils import resolve_person_id


def _parse_json(value: Any, default: Any) -> Any:
    """Return a parsed dict/list from a DB value that may be a string-encoded JSON.

    asyncpg returns JSONB columns as serialized strings, not Python objects.
    This normalises both cases so callers can always use .get() safely.
    """
    if value is None:
        return default
    if isinstance(value, (dict, list)):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return parsed if parsed is not None else default
        except Exception:
            return default
    return default


async def compute_coherence(person_id: str) -> Dict[str, Any]:
    person_id = await resolve_person_id(person_id) or person_id
    issues: List[str] = []
    adjustments: List[str] = []

    # wellness
    wellness = await q(
        "SELECT body, mind, emotion, energy FROM wellness_state_cache WHERE person_id = $1",
        person_id,
        one=True,
    ) or {}
    body_score = _parse_json(wellness.get("body"), {}).get("score", 0)
    mind_score = _parse_json(wellness.get("mind"), {}).get("score", 0)
    emotion_score = _parse_json(wellness.get("emotion"), {}).get("score", 0)
    energy_score = _parse_json(wellness.get("energy"), {}).get("score", 0)

    # personal model aggregates
    pm_row = await q(
        "SELECT narrative_arcs, identity_state, conflict_state, emotion_state, pattern_sense, coherence_report FROM personal_model WHERE person_id = $1",
        person_id,
        one=True,
    ) or {}
    arcs = _parse_json(pm_row.get("narrative_arcs"), [])
    identity_state = _parse_json(pm_row.get("identity_state"), {})
    conflict_state = _parse_json(pm_row.get("conflict_state"), {})
    emotion_state = _parse_json(pm_row.get("emotion_state"), {})
    pattern_sense = _parse_json(pm_row.get("pattern_sense"), {})
    coherence_report = _parse_json(pm_row.get("coherence_report"), {})
    prior_confidence = float(coherence_report.get("confidence") or 1.0)

    # emotion loop
    drift = float(emotion_state.get("trend") or emotion_state.get("drift") or 0)
    volatility = float(emotion_state.get("volatility") or 0)

    # intents
    intents = await q(
        "SELECT intent_name, strength, emotional_alignment, trend FROM intent_evolution WHERE person_id = $1",
        person_id,
    ) or []

    # alignment map
    alignment = await q(
        "SELECT alignment_map FROM daily_alignment_cache WHERE person_id = $1",
        person_id,
        one=True,
    ) or {}
    alignment_map = _parse_json(alignment.get("alignment_map"), {})

    # tasks
    tasks = await q(
        """
        SELECT id, title, energy_cost, auto_priority, status
        FROM tasks
        WHERE user_id = $1
        """,
        person_id,
    ) or []

    # helper means
    def _safe_mean(values: List[float]) -> float:
        return mean(values) if values else 0.0

    # thought coherence (intent consistency)
    strong_intents = [i for i in intents if float(i.get("strength") or 0) > 0.5]
    thought_score = 0.7 - max(0, (len(strong_intents) - 2) * 0.1)

    # emotion coherence
    emotion_coherence = 0.7 + (drift * 0.5)
    if strong_intents and drift < -0.1:
        emotion_coherence -= 0.2

    # behavior coherence
    open_heavy = [t for t in tasks if (t.get("status") or "todo") != "done" and (t.get("auto_priority") or 0) > 0.6]
    behavior_score = 0.8 - (len(open_heavy) * 0.05)

    # identity coherence
    anchor_alignment = _parse_json(identity_state.get("anchor_alignment"), {})
    identity_score = _safe_mean([float(v or 0) for v in anchor_alignment.values()]) if anchor_alignment else 0.6

    # alignment coherence
    alignment_score = 0.7
    if alignment_map.get("avoid_actions") and alignment_map.get("recommended_actions"):
        alignment_score -= 0.2

    # narrative coherence
    arc_momentum = [float(a.get("momentum") or 0) for a in arcs if isinstance(a, dict)]
    narrative_score = 0.7 + (_safe_mean(arc_momentum) * 0.2)

    coherence_map = {
        "thought": max(0.0, min(1.0, thought_score)),
        "emotion": max(0.0, min(1.0, emotion_coherence)),
        "behavior": max(0.0, min(1.0, behavior_score)),
        "identity": max(0.0, min(1.0, identity_score)),
        "alignment": max(0.0, min(1.0, alignment_score)),
        "narrative": max(0.0, min(1.0, narrative_score)),
    }

    coherence_score = _safe_mean(list(coherence_map.values()))

    # fragmentation index
    intent_switch = max(0, (len(strong_intents) - 1) * 0.1)
    drift_slope = float(identity_state.get("drift_score") or 0)
    conflicts_raw = _parse_json(conflict_state.get("conflicts"), [])
    conflict_density = len(conflicts_raw) * 0.05
    fragmentation_index = _safe_mean(
        [
            abs(volatility),
            intent_switch,
            abs(drift_slope),
            conflict_density,
            max(0, -drift),
        ]
    )

    for dim, score in coherence_map.items():
        if score < 0.5:
            issues.append(f"Low coherence in {dim}")
    if coherence_score < 0.6:
        adjustments.append("Consider simplifying plans and adding micro-steps")

    confidence = max(0.5, min(1.0, prior_confidence * (1 - fragmentation_index)))
    summary = "; ".join(issues) if issues else "Coherence stable"

    return {
        "coherence_score": coherence_score,
        "fragmentation_index": fragmentation_index,
        "coherence_map": coherence_map,
        "issues": issues,
        "adjustments": adjustments,
        "summary": summary,
        "confidence": confidence,
        "updated_at": dt.datetime.utcnow().isoformat(),
    }


__all__ = ["compute_coherence"]
