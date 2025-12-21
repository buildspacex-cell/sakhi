from __future__ import annotations

import json
from typing import Any, Dict, Sequence

from sakhi.apps.api.core.llm import call_llm


def compute_fast_esr_frame(emotion_state: Dict[str, Any] | None, soul_state: Dict[str, Any] | None, rhythm_state: Dict[str, Any] | None) -> Dict[str, Any]:
    """
    Deterministic tri-layer coherence (no LLM).
    Outputs:
      - coherence_score (0-1)
      - emotion_vs_soul (-1..1)
      - emotion_vs_rhythm (-1..1)
      - soul_vs_rhythm (-1..1)
      - dominant_friction_zone (str)
    """
    emotion = emotion_state or {}
    soul = soul_state or {}
    rhythm = rhythm_state or {}

    if isinstance(emotion, str):
        try:
            emotion = json.loads(emotion)
        except Exception:
            emotion = {}
    if not isinstance(emotion, dict):
        emotion = {}

    if isinstance(soul, str):
        try:
            soul = json.loads(soul)
        except Exception:
            soul = {}
    if not isinstance(soul, dict):
        soul = {}

    if isinstance(rhythm, str):
        try:
            rhythm = json.loads(rhythm)
        except Exception:
            rhythm = {}
    if not isinstance(rhythm, dict):
        rhythm = {}

    # basic signals
    mood = (emotion.get("dominant") or emotion.get("summary") or "neutral").lower()
    values = soul.get("core_values") or []
    shadow = soul.get("shadow") or []
    friction = soul.get("friction") or soul.get("conflicts") or []
    energy = float(rhythm.get("body_energy") or rhythm.get("energy") or 0.5)
    mind_focus = float(rhythm.get("mind_focus") or 0.5)

    # map mood to polarity
    positive = {"joy", "calm", "optimistic", "positive", "uplifted"}
    negative = {"sad", "tired", "stressed", "anxious", "angry", "negative"}
    if mood in positive:
        mood_score = 1.0
    elif mood in negative:
        mood_score = -1.0
    else:
        mood_score = 0.0

    # emotion vs soul: positive if mood aligns with light/values
    soul_light = soul.get("light") or []
    soul_pressure = len(shadow) + len(friction)
    soul_support = len(values) + len(soul_light)
    emotion_vs_soul = max(-1.0, min(1.0, mood_score * 0.6 + (soul_support - soul_pressure) * 0.05))

    # emotion vs rhythm: higher if energy/focus match mood sign
    rhythm_balance = (energy + mind_focus) / 2
    emotion_vs_rhythm = max(-1.0, min(1.0, rhythm_balance * (1 if mood_score >= 0 else -1)))

    # soul vs rhythm: are values/light supported by energy/focus?
    soul_vs_rhythm = max(-1.0, min(1.0, rhythm_balance - (soul_pressure * 0.05)))

    # coherence: blend of above
    coherence_score = max(0.0, min(1.0, (emotion_vs_soul + emotion_vs_rhythm + soul_vs_rhythm + 3) / 6))

    dominant_friction_zone = None
    if friction:
        dominant_friction_zone = str(friction[0])
    elif shadow:
        dominant_friction_zone = str(shadow[0])

    return {
        "coherence_score": coherence_score,
        "emotion_vs_soul": emotion_vs_soul,
        "emotion_vs_rhythm": emotion_vs_rhythm,
        "soul_vs_rhythm": soul_vs_rhythm,
        "dominant_friction_zone": dominant_friction_zone,
    }


async def compute_deep_esr(
    person_id: str,
    episodic: Sequence[Dict[str, Any]],
    emotion_state: Dict[str, Any],
    soul_state: Dict[str, Any],
    rhythm_state: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Worker-time coherence (LLM allowed).
    Outputs include:
      - emotional_arc
      - value_emotion_alignment
      - rhythm_emotion_interactions
      - shadow_emotion_interplay
      - weekly_coherence_map
      - friction_clusters
      - recommended_pacing
    """
    prompt = (
        "You are Sakhi's ESR (Emotion × Soul × Rhythm) analyzer. "
        "Given emotion_state, soul_state, rhythm_state, and episodic snippets, return JSON with keys: "
        "emotional_arc, value_emotion_alignment, rhythm_emotion_interactions, shadow_emotion_interplay, "
        "weekly_coherence_map, friction_clusters, recommended_pacing. "
        "Keep it concise and deterministic JSON."
    )
    payload = {
        "person_id": person_id,
        "emotion_state": emotion_state or {},
        "soul_state": soul_state or {},
        "rhythm_state": rhythm_state or {},
        "episodic": episodic or [],
    }
    result = await call_llm(messages=[{"role": "user", "content": f"{prompt}\n\nPAYLOAD:\n{payload}"}])
    if isinstance(result, dict):
        return result
    return {"weekly_coherence_map": str(result)}
