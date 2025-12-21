from __future__ import annotations

import datetime as dt
from statistics import mean
from typing import Any, Dict, List

from sakhi.apps.api.core.db import q
from sakhi.apps.api.core.person_utils import resolve_person_id


def _trend_numeric(trend: str | None) -> float:
    if not trend:
        return 0.0
    t = trend.lower()
    if t == "up":
        return 0.1
    if t == "down":
        return -0.1
    return 0.0


async def compute_inner_conflict(person_id: str) -> Dict[str, Any]:
    resolved = await resolve_person_id(person_id) or person_id

    intents: List[Dict[str, Any]] = await q(
        "SELECT intent_name, strength, trend FROM intent_evolution WHERE person_id = $1",
        resolved,
    ) or []
    tasks: List[Dict[str, Any]] = await q(
        "SELECT id, title, status, auto_priority, energy_cost FROM tasks WHERE user_id = $1",
        resolved,
    ) or []
    pm_row = await q(
        "SELECT conflict_state, emotion_state, identity_state, coherence_report, pattern_sense, narrative_arcs FROM personal_model WHERE person_id = $1",
        resolved,
        one=True,
    ) or {}
    identity_state = pm_row.get("identity_state") or {}
    emotion_state = pm_row.get("emotion_state") or {}
    coherence_report = pm_row.get("coherence_report") or {}
    pattern_sense = pm_row.get("pattern_sense") or {}
    arcs = pm_row.get("narrative_arcs") or []

    alignment_row = await q(
        "SELECT alignment_map FROM daily_alignment_cache WHERE person_id = $1",
        resolved,
        one=True,
    ) or {}
    alignment_map = alignment_row.get("alignment_map") or {}

    conflicts: List[Dict[str, Any]] = []

    anchor_alignment = identity_state.get("anchor_alignment") or {}
    suppressed = [a for a, v in anchor_alignment.items() if float(v or 0) < 0.3]
    elevated = [a for a, v in anchor_alignment.items() if float(v or 0) > 0.6]
    for a in suppressed:
        for b in elevated:
            conflicts.append({"a": a, "b": b, "force": 0.2, "evidence": ["anchor collision"]})

    # intent contradictions: trend disagreement
    ups = [i for i in intents if _trend_numeric(i.get("trend")) > 0]
    downs = [i for i in intents if _trend_numeric(i.get("trend")) < 0]
    for u in ups:
        for d in downs:
            conflicts.append(
                {
                    "a": u.get("intent_name"),
                    "b": d.get("intent_name"),
                    "force": 0.25,
                    "evidence": ["intent trend contradiction"],
                }
            )

    emotion_trend = float(emotion_state.get("trend") or emotion_state.get("drift") or 0.0)
    for intent in intents:
        if float(intent.get("strength") or 0) > 0.5 and emotion_trend < -0.1:
            conflicts.append(
                {
                    "a": intent.get("intent_name"),
                    "b": "emotion",
                    "force": 0.2,
                    "evidence": ["emotional divergence"],
                }
            )

    high_priority_tasks = [
        t for t in tasks if (t.get("auto_priority") or 0) > 0.6 and (t.get("status") or "todo") != "done"
    ]
    if high_priority_tasks and emotion_trend < -0.1:
        conflicts.append(
            {
                "a": "discipline",
                "b": "comfort",
                "force": 0.15,
                "evidence": ["task avoidance with negative mood"],
            }
        )

    if float(coherence_report.get("confidence") or 1.0) < 0.4:
        conflicts.append({"a": "self", "b": "self", "force": 0.1, "evidence": ["low coherence confidence"]})

    # alignment_map competing anchor pressure
    if alignment_map.get("avoid_actions") and alignment_map.get("recommended_actions"):
        conflicts.append(
            {
                "a": "planner",
                "b": "emotion",
                "force": 0.1,
                "evidence": ["alignment map avoid vs recommend"],
            }
        )

    # pattern_sense behavior clusters can hint conflicts
    if pattern_sense.get("intent_couplings"):
        conflicts.append(
            {"a": "pattern", "b": "intent", "force": 0.1, "evidence": ["mixed intent couplings detected"]}
        )

    forces = [float(c.get("force") or 0) for c in conflicts] or [0.0]
    conflict_score = mean(forces)
    dominant_conflict = None
    if conflicts:
        dominant_conflict = max(conflicts, key=lambda c: float(c.get("force") or 0)).get("a")

    return {
        "conflict_score": conflict_score,
        "conflicts": conflicts,
        "dominant_conflict": dominant_conflict,
        "updated_at": dt.datetime.utcnow().isoformat(),
    }


__all__ = ["compute_inner_conflict"]
