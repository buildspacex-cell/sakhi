from __future__ import annotations

import datetime as dt
from statistics import mean
from typing import Any, Dict, List

from sakhi.apps.api.core.db import q
from sakhi.apps.api.core.person_utils import resolve_person_id


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
    body_score = (wellness.get("body") or {}).get("score", 0) if isinstance(wellness.get("body"), dict) else 0
    mind_score = (wellness.get("mind") or {}).get("score", 0) if isinstance(wellness.get("mind"), dict) else 0
    emotion_score = (wellness.get("emotion") or {}).get("score", 0) if isinstance(wellness.get("emotion"), dict) else 0
    energy_score = (wellness.get("energy") or {}).get("score", 0) if isinstance(wellness.get("energy"), dict) else 0

    # personal model aggregates
    pm_row = await q(
        "SELECT narrative_arcs, identity_state, conflict_state, emotion_state, pattern_sense, coherence_report FROM personal_model WHERE person_id = $1",
        person_id,
        one=True,
    ) or {}
    arcs = pm_row.get("narrative_arcs") or []
    identity_state = pm_row.get("identity_state") or {}
    conflict_state = pm_row.get("conflict_state") or {}
    emotion_state = pm_row.get("emotion_state") or {}
    pattern_sense = pm_row.get("pattern_sense") or {}
    prior_confidence = float((pm_row.get("coherence_report") or {}).get("confidence") or 1.0)

    # emotion loop
    drift = float((emotion_state or {}).get("trend") or (emotion_state or {}).get("drift") or 0)
    volatility = float((emotion_state or {}).get("volatility") or 0)

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
    alignment_map = alignment.get("alignment_map") or {}

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
    anchor_alignment = identity_state.get("anchor_alignment") or {}
    identity_score = _safe_mean([float(v or 0) for v in anchor_alignment.values()]) if anchor_alignment else 0.6

    # alignment coherence
    alignment_score = 0.7
    if alignment_map.get("avoid_actions") and alignment_map.get("recommended_actions"):
        alignment_score -= 0.2

    # narrative coherence
    arc_momentum = [float(a.get("momentum") or 0) for a in arcs]
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
    conflict_density = len(conflict_state.get("conflicts") or []) * 0.05
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
