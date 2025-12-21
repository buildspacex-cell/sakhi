from __future__ import annotations

import datetime as dt
from typing import Any, Dict

from sakhi.apps.api.core.db import q
from sakhi.apps.api.core.person_utils import resolve_person_id
from sakhi.apps.engine.coherence import engine as coherence_engine
from sakhi.apps.engine.alignment import engine as alignment_engine
from sakhi.apps.engine.narrative import engine as narrative_engine
from sakhi.apps.engine.pattern_sense import engine as pattern_engine
from sakhi.apps.engine.emotion_loop import engine as emotion_engine


async def compute_inner_dialogue(person_id: str, last_message: str = "", context: Dict[str, Any] | None = None) -> Dict[str, Any]:
    person_id = await resolve_person_id(person_id) or person_id
    context = context or {}

    # fetch supporting states
    try:
        alignment_map = await alignment_engine.compute_alignment_map(person_id)
    except Exception:
        alignment_map = {}
    try:
        coherence_report = await coherence_engine.compute_coherence(person_id)
    except Exception:
        coherence_report = {}
    try:
        arcs = await narrative_engine.compute_narrative_arcs(person_id)
    except Exception:
        arcs = []
    try:
        patterns = await pattern_engine.compute_patterns(person_id)
    except Exception:
        patterns = {}
    try:
        emotion_state = await emotion_engine.compute_emotion_loop_for_person(person_id)
    except Exception:
        emotion_state = {}
    # wellness
    wellness = await q(
        "SELECT body, mind, emotion, energy FROM wellness_state_cache WHERE person_id = $1",
        person_id,
        one=True,
    ) or {}
    mind_score = (wellness.get("mind") or {}).get("score", 0) if isinstance(wellness.get("mind"), dict) else 0

    reflections = []
    drift = float(emotion_state.get("drift") or 0)
    mode = emotion_state.get("mode") or ""
    if drift < -0.2:
        reflections.append("Emotional drift is negative; tread gently.")
    if arcs:
        reflections.append(f"Key arc stage: {arcs[0].get('stage')}")
    if coherence_report.get("issues"):
        reflections.append("Coherence issues present.")
    if alignment_map.get("recommended_actions"):
        reflections.append("There are recommended actions suitable for today.")

    # guidance intention
    guidance = "gentle accompaniment"
    if drift < -0.2:
        guidance = "grounding"
    elif arcs and float(arcs[0].get("momentum") or 0) > 0.6:
        guidance = "encourage forward movement"
    elif wellness and ((wellness.get("energy") or {}).get("score", 0) or 0) < -0.3:
        guidance = "energy-protection"
    if coherence_report.get("issues"):
        guidance = "soft realignment"

    tone = "neutral-soft"
    if mode == "falling":
        tone = "warm"
    elif mind_score > 2:
        tone = "calm"
    elif arcs and float(arcs[0].get("momentum") or 0) > 0.6:
        tone = "bright"

    signals = []
    energy_score = (wellness.get("energy") or {}).get("score", 0) if isinstance(wellness.get("energy"), dict) else 0
    if energy_score < -0.2 and alignment_map.get("recommended_actions"):
        signals.append("avoid push")
    if drift < -0.2:
        signals.append("avoid confrontation")
    if arcs and arcs[0].get("stage") in {"Climax", "Rising Action"}:
        signals.append("reinforce wins")

    return {
        "reflections": reflections,
        "guidance_intention": guidance,
        "tone": tone,
        "signals": signals,
        "updated_at": dt.datetime.utcnow().isoformat(),
    }


__all__ = ["compute_inner_dialogue"]
