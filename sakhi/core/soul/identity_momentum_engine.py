from __future__ import annotations

import json
from typing import Any, Dict, Sequence

from sakhi.apps.api.core.llm import call_llm


def compute_fast_identity_momentum(
    episodic_tail: Sequence[Dict[str, Any]] | None,
    soul_state: Dict[str, Any] | None,
    emotion_state: Dict[str, Any] | None,
    rhythm_state: Dict[str, Any] | None,
) -> Dict[str, Any]:
    """
    Deterministic identity momentum frame (<5ms, no LLM).
    """
    # Normalize inputs in case upstream passes serialized JSON strings
    def _ensure_dict(val: Any) -> Dict[str, Any]:
        if isinstance(val, dict):
            return val
        if isinstance(val, str):
            try:
                return json.loads(val)
            except Exception:
                return {}
        return {}

    soul = _ensure_dict(soul_state)
    emotion = _ensure_dict(emotion_state)
    rhythm = _ensure_dict(rhythm_state)
    tail = episodic_tail or []

    shadow = soul.get("shadow") or []
    light = soul.get("light") or []
    values = soul.get("core_values") or []
    friction = soul.get("friction") or soul.get("conflicts") or []
    mood = (emotion.get("dominant") or emotion.get("summary") or "neutral").lower()
    energy = float(rhythm.get("body_energy") or rhythm.get("energy") or 0.5)
    focus = float(rhythm.get("mind_focus") or rhythm.get("focus") or 0.5)

    # simple positive/negative mood mapping
    positive = {"joy", "calm", "optimistic", "positive", "uplifted"}
    negative = {"sad", "tired", "stressed", "anxious", "angry", "negative"}
    if mood in positive:
        mood_score = 1.0
    elif mood in negative:
        mood_score = -1.0
    else:
        mood_score = 0.0

    momentum_score = max(0.0, min(1.0, (len(light) + len(values) + 1) / (len(shadow) + len(friction) + 3)))
    emotional_drag = max(0.0, min(1.0, (len(shadow) + len(friction)) * 0.1 + (0.5 - mood_score * 0.5)))
    shadow_interference = max(0.0, min(1.0, len(shadow) * 0.1))

    # direction based on trend in episodic tail (counts of “growth” vs “stuck” words)
    growth_tokens = ("progress", "growth", "practice", "forward", "built")
    stuck_tokens = ("stuck", "blocked", "tired", "overwhelmed")
    growth_hits = 0
    stuck_hits = 0
    for ep in tail[-5:]:
        text = str(ep.get("text") or "").lower()
        if any(t in text for t in growth_tokens):
            growth_hits += 1
        if any(t in text for t in stuck_tokens):
            stuck_hits += 1
    if growth_hits > stuck_hits + 1:
        momentum_direction = "forward"
    elif stuck_hits > growth_hits + 1:
        momentum_direction = "regressing"
    else:
        momentum_direction = "stagnant"

    # push/pull: energy+focus vs drag
    forward_force = (energy + focus) / 2
    drag = emotional_drag
    if forward_force - drag > 0.2:
        identity_push_pull = "push"
    elif drag - forward_force > 0.2:
        identity_push_pull = "pull"
    else:
        identity_push_pull = "neutral"

    return {
        "momentum_score": momentum_score,
        "momentum_direction": momentum_direction,
        "emotional_drag": emotional_drag,
        "shadow_interference": shadow_interference,
        "identity_push_pull": identity_push_pull,
    }


async def compute_deep_identity_momentum(
    person_id: str,
    episodic: Sequence[Dict[str, Any]],
    soul_state: Dict[str, Any],
    emotion_state: Dict[str, Any],
    rhythm_state: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Worker-time LLM-powered identity momentum.
    """
    prompt = (
        "You are Sakhi's Identity Momentum engine. Given soul_state, emotion_state, rhythm_state, and episodic signals, "
        "return JSON with keys: identity_arc_summary, growth_phase, stagnation_patterns, identity_transitions, "
        "emerging_self_themes, long_term_projection. Keep concise JSON."
    )
    payload = {
        "person_id": person_id,
        "soul_state": soul_state or {},
        "emotion_state": emotion_state or {},
        "rhythm_state": rhythm_state or {},
        "episodic": episodic or [],
    }
    result = await call_llm(messages=[{"role": "user", "content": f"{prompt}\n\nPAYLOAD:\n{payload}"}])
    if isinstance(result, dict):
        return result
    return {"identity_arc_summary": str(result)}
