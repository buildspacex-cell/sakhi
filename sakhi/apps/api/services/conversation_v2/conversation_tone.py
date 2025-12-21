from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List


def _safe_float(value: Any, default: float = 0.5) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _micro_tone(last_emotion: str, clarity: float) -> Dict[str, Any]:
    emotion = (last_emotion or "neutral").lower()
    palette = {
        "neutral": ("grounded calm", 0.4),
        "tired": ("restorative warmth", 0.35),
        "sad": ("soft reassurance", 0.3),
        "anxious": ("steady grounding", 0.32),
        "excited": ("contained enthusiasm", 0.55),
        "angry": ("cool steadying", 0.33),
    }
    label, temperature = palette.get(emotion, ("gentle presence", 0.42))
    return {
        "focus": label,
        "temperature": temperature if clarity < 0.7 else min(0.6, temperature + 0.1),
        "note": "Stay concise while protecting safety" if clarity < 0.4 else "Offer layered nuance",
    }


def _mirroring(last_emotion: str, clarity: float) -> Dict[str, Any]:
    emotion = (last_emotion or "neutral").lower()
    strategy = "Name the feeling, validate it, then extend warmth."
    if clarity < 0.45:
        strategy = "Mirror feeling in short phrasing, then gently co-regulate."
    elif clarity > 0.7:
        strategy = "Mirror emotion briefly and co-create next gentle action."
    return {
        "emotion": emotion,
        "strategy": strategy,
    }


def _persona_style(persona: str) -> str:
    persona_styles = {
        "Reflective": "gentle, reflective, warm",
        "Supportive": "encouraging, empathetic, steady",
        "Action": "clear, direct, structured",
        "Light": "friendly, upbeat, conversational",
        "Companion": "tender, intuitive, heartfelt",
    }
    return persona_styles.get(persona, persona_styles["Reflective"])


def _determine_ritual(rhythm: Dict[str, Any]) -> Dict[str, Any]:
    now = datetime.now(timezone.utc)
    hour = now.hour
    if hour < 6:
        phase = "pre-dawn"
        intent = "protect rest and whisper reassurance"
    elif hour < 12:
        phase = "morning"
        intent = "lift gently with grounding rituals"
    elif hour < 18:
        phase = "afternoon"
        intent = "maintain steady cadence and nudge focus"
    else:
        phase = "evening"
        intent = "wind down, wrap with gratitude cues"

    chronotype = rhythm.get("chronotype")
    if isinstance(chronotype, str):
        intent += f"; honour {chronotype} chronotype tempo"

    return {
        "phase": phase,
        "intent": intent,
    }


def _empathy_block(emotion_state: Dict[str, Any], themes: List[Dict[str, Any]]) -> Dict[str, Any]:
    mood = (emotion_state.get("mood") or "neutral").lower()
    dominant_theme = themes[0]["theme"] if themes else None
    focus = "Name their inner weather and mirror it back."
    if mood in {"sad", "tired"}:
        focus = "Validate heaviness, offer anchoring breath imagery."
    elif mood in {"open", "curious"}:
        focus = "Celebrate openness and point toward gentle experimentation."
    if dominant_theme:
        focus += f" Thread in the '{dominant_theme}' theme for coherence."
    return {
        "mood": mood,
        "focus": focus,
    }


def _memory_thread(short_term: Dict[str, Any], themes: List[Dict[str, Any]]) -> str:
    if isinstance(short_term.get("focus"), str):
        return short_term["focus"]
    if isinstance(short_term.get("summary"), str):
        return short_term["summary"]
    texts = short_term.get("texts")
    if isinstance(texts, list):
        for text in reversed(texts):
            if isinstance(text, str) and text.strip():
                return text.strip()
    for theme in themes:
        name = theme.get("theme")
        if name:
            return f"Stay coherent with theme: {name}"
    return "Keep continuity with their last reflection."


def _apply_behavior_overrides(tone: Dict[str, Any], behavior: Dict[str, Any]) -> None:
    tone_profile = behavior.get("tone_profile")
    pacing = behavior.get("pacing")
    depth = behavior.get("conversation_depth")

    style_map = {
        "soft": "soft, calming, reassuring",
        "warm": "warm, steady, reassuring",
        "focused": "clear, focused, composed",
        "gentle": "gentle, spacious, kind",
        "uplifting": "uplifting, encouraging, forward-leaning",
    }
    if tone_profile in style_map:
        tone["style"] = style_map[tone_profile]

    pace_map = {
        "short": "slow",
        "medium": "balanced",
        "extended": "bright",
    }
    if pacing in pace_map:
        tone["pace"] = pace_map[pacing]

    if depth:
        tone["depth"] = depth
    if behavior.get("guidance_intensity"):
        tone["guidance_intensity"] = behavior["guidance_intensity"]
    if behavior.get("emotional_alignment"):
        tone["emotional_alignment"] = behavior["emotional_alignment"]
    if behavior.get("avoid_modes"):
        tone["avoid_modes"] = behavior["avoid_modes"]
    if behavior.get("reflection_invitations"):
        tone["reflection_invitation"] = behavior["reflection_invitations"]


def decide_tone(context: Dict[str, Any], behavior: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """
    Determine tonal guidance based on clarity, energy, persona mode, rhythm, and memory threads.
    """

    continuity = context.get("continuity") or {}
    conversation = context.get("conversation") or {}
    rhythm = context.get("rhythm") or {}
    short_term = context.get("short_term") or {}
    emotion_state = context.get("emotion") or {}
    themes = context.get("themes") or []

    clarity = _safe_float(continuity.get("clarity_level"), 0.55)
    energy = _safe_float(conversation.get("energy_level"), 0.5)
    rhythm_energy = _safe_float(rhythm.get("body_energy"), energy)
    persona = context.get("persona_mode") or "Reflective"
    last_emotion = conversation.get("last_emotion") or emotion_state.get("mood") or "neutral"

    tone: Dict[str, Any] = {}
    tone["style"] = _persona_style(persona)
    tone["persona_mode"] = persona
    tone["concise"] = clarity > 0.65
    tone["mirroring"] = _mirroring(last_emotion, clarity)
    tone["micro"] = _micro_tone(last_emotion, clarity)
    tone["stability"] = {
        "score": round(min(0.95, 0.6 + clarity * 0.4), 2),
        "guidance": "Hold consistent warmth; avoid persona jumps.",
    }
    tone["ritual"] = _determine_ritual(rhythm)
    tone["empathy"] = _empathy_block(emotion_state, themes)
    tone["memory_thread"] = _memory_thread(short_term, themes)

    combined_energy = (energy + rhythm_energy) / 2
    if combined_energy < 0.4:
        pace = "slow"
    elif combined_energy > 0.75:
        pace = "bright"
    else:
        pace = "balanced"
    tone["pace"] = pace
    tone["pacing_rationale"] = f"Rhythm energy {rhythm_energy:.2f} blended with current conversation energy {energy:.2f}"

    if behavior:
        _apply_behavior_overrides(tone, behavior)
        tone["behavior_profile"] = behavior

    return tone


__all__ = ["decide_tone"]
