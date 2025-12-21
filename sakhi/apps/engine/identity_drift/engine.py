from __future__ import annotations

import datetime as dt
from statistics import mean
from typing import Any, Dict, List

from sakhi.apps.api.core.db import q
from sakhi.apps.api.core.person_utils import resolve_person_id


def _intent_trend_value(trend: str | None) -> float:
    if not trend:
        return 0.0
    trend = trend.lower()
    if trend == "up":
        return 0.1
    if trend == "down":
        return -0.1
    return 0.0


def _energy_numeric(profile: str | None) -> float:
    if profile == "low":
        return -0.1
    if profile == "high":
        return 0.1
    return 0.0


async def compute_identity_state(person_id: str) -> Dict[str, Any]:
    """Compute identity anchors, alignment, drift, and opportunities/dangers."""
    resolved = await resolve_person_id(person_id) or person_id

    intents: List[Dict[str, Any]] = await q(
        "SELECT intent_name, strength, trend, emotional_alignment FROM intent_evolution WHERE person_id = $1",
        resolved,
    ) or []

    pm_row = await q(
        "SELECT narrative_arcs, pattern_sense, emotion_state, coherence_report, inner_dialogue_state, long_term FROM personal_model WHERE person_id = $1",
        resolved,
        one=True,
    ) or {}
    arcs = pm_row.get("narrative_arcs") or []
    pattern_sense = pm_row.get("pattern_sense") or {}
    emotion_state = pm_row.get("emotion_state") or {}
    coherence_report = pm_row.get("coherence_report") or {}
    inner_dialogue = pm_row.get("inner_dialogue_state") or {}
    long_term = pm_row.get("long_term") or {}
    layers = long_term.get("layers") if isinstance(long_term, dict) else {}

    alignment_map_row = await q(
        "SELECT alignment_map FROM daily_alignment_cache WHERE person_id = $1",
        resolved,
        one=True,
    ) or {}
    alignment_map = alignment_map_row.get("alignment_map") or {}

    wellness = await q(
        "SELECT body, mind, emotion, energy FROM wellness_state_cache WHERE person_id = $1",
        resolved,
        one=True,
    ) or {}

    anchors = ["creative", "learning-driven", "disciplined", "connected", "balanced", "impact-driven"]
    anchor_alignment: Dict[str, float] = {}

    intent_strength_map = {i.get("intent_name", "").lower(): float(i.get("strength") or 0) for i in intents}
    arc_momentum_avg = mean([float(a.get("momentum") or 0) for a in arcs]) if arcs else 0.0
    emotion_trend = float(emotion_state.get("trend") or emotion_state.get("drift") or 0.0)

    for anchor in anchors:
        score = 0.2
        # simple boosts based on intents and arcs keywords
        if "learn" in anchor and any("learn" in name for name in intent_strength_map):
            score += 0.2
        if "discipline" in anchor and layers.get("soul", {}).get("summary", ""):
            score += 0.1
        score += arc_momentum_avg * 0.2
        score += max(intent_strength_map.values()) * 0.2 if intent_strength_map else 0
        score += max(0.0, emotion_trend) * 0.1
        anchor_alignment[anchor] = max(0.0, min(1.0, score))

    intent_trends = [_intent_trend_value(i.get("trend")) for i in intents] or [0.0]
    drift_components = [
        emotion_trend,
        mean(intent_trends),
        arc_momentum_avg * 0.5,
        (float(coherence_report.get("confidence") or 1.0) - 1.0),
        _energy_numeric(alignment_map.get("energy_profile")),
    ]
    drift_score = mean(drift_components)
    identity_movement = "stable"
    if drift_score > 0.1:
        identity_movement = "upward"
    elif drift_score < -0.1:
        identity_movement = "downward"

    warnings: List[str] = []
    for anchor, score in anchor_alignment.items():
        if score < 0.3:
            warnings.append(f"Anchor '{anchor}' under-activated")
    for intent in intents:
        if float(intent.get("strength") or 0) > 0.6 and emotion_trend < -0.1:
            warnings.append("Strong intent but negative emotional slope")
    for arc in arcs:
        if arc.get("stage") in {"Plateau"}:
            warnings.append("Arc plateau detected")

    opportunities: List[str] = []
    for anchor, score in anchor_alignment.items():
        if score > 0.4 and anchor not in [w.split("'")[1] for w in warnings if "'" in w]:
            opportunities.append(f"Lean into {anchor}")
    for arc in arcs:
        if arc.get("stage") in {"Rising Action", "Climax"}:
            opportunities.append(f"Reinforce momentum in {arc.get('intent') or 'current arc'}")

    return {
        "anchors": anchors,
        "drift_score": drift_score,
        "anchor_alignment": anchor_alignment,
        "identity_movement": identity_movement,
        "warnings": warnings,
        "opportunities": opportunities,
        "updated_at": dt.datetime.utcnow().isoformat(),
    }


__all__ = ["compute_identity_state"]
