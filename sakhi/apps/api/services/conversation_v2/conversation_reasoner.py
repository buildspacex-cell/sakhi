from __future__ import annotations

import json
from typing import Any, Dict, List

from sakhi.libs.json_utils import json_safe


def build_prompt(
    user_text: str,
    context: Dict[str, Any],
    tone: Dict[str, Any],
    *,
    metadata: Dict[str, Any] | None = None,
) -> str:
    """
    Compose the final LLM prompt using the conversation context, tone guidance, and metadata.
    """

    short_term = context.get("short_term") or {}
    texts: List[str] = []
    if isinstance(short_term.get("texts"), list):
        texts = [str(t) for t in short_term["texts"] if isinstance(t, str)]
    st_block = "\n".join(f"- {line}" for line in texts[-3:]) or "- (no recent short-term memories)"

    themes = ", ".join(t.get("theme") for t in context.get("themes", []) if t.get("theme")) or "none"

    tone_style = tone.get("style", "warm and reflective")
    pace = tone.get("pace", "balanced")
    concise = tone.get("concise", False)
    micro = tone.get("micro", {})
    mirroring = tone.get("mirroring", {})
    ritual = tone.get("ritual", {})
    empathy = tone.get("empathy", {})
    stability = tone.get("stability", {})
    memory_thread = tone.get("memory_thread")
    pacing_rationale = tone.get("pacing_rationale")

    clarity_level = context.get("continuity", {}).get("clarity_level", 0.5)
    last_emotion = context.get("conversation", {}).get("last_emotion", "neutral")
    energy_level = context.get("conversation", {}).get("energy_level", 0.5)

    persona_mode = context.get("persona_mode", "Reflective")

    metadata_payload = metadata or {}
    behavior_profile = metadata_payload.get("behavior_profile") or {}
    behavior_block = json_safe(behavior_profile) if behavior_profile else {}
    enriched_context = {
        "topics": metadata_payload.get("topics"),
        "emotion_hint": metadata_payload.get("emotion"),
        "intents": metadata_payload.get("intents"),
        "plans": metadata_payload.get("plans"),
        "rhythm_trigger": metadata_payload.get("rhythm_triggers"),
        "meta_reflection_trigger": metadata_payload.get("meta_reflection_triggers"),
        "behavior_profile": behavior_profile,
    }
    journaling_ai = context.get("journaling_ai")
    journal_section = ""
    if journaling_ai:
        journal_section = "\nJournaling cues:\n" + json.dumps(json_safe(journaling_ai), ensure_ascii=False) + "\n"

    return f"""
You are Sakhi, an emotionally intelligent clarity companion.
Persona mode: {persona_mode}
Tone style: {tone_style} (pace={pace}, concise={str(concise).lower()}).
Tone blueprint:
 - Micro-tone: {micro.get("focus", "gentle presence")} (temperature={micro.get("temperature", 0.4)})
 - Mirroring approach: {mirroring.get("strategy", "mirror emotion before guiding forward")}
 - Ritual phase: {ritual.get("phase", "daily")} (intent: {ritual.get("intent", "nurture calm transitions")})
 - Empathy focus: {empathy.get("focus", "validate and soften edges")} (mood anchor: {empathy.get("mood", "neutral")})
 - Persona stability: score {stability.get("score", 0.8)}, guidance: {stability.get("guidance", "stay consistent")}
 - Memory thread to honor: {memory_thread or "maintain continuity with their latest reflection"}
 - Rhythm pacing note: {pacing_rationale or "default pacing"}

User clarity level: {clarity_level}
Emotion state: {last_emotion}
Energy level: {energy_level}

Active themes: {themes}

Recent short-term thoughts:
{st_block}

Additional context:
{json.dumps(json_safe(enriched_context), ensure_ascii=False)}
Behavior cues:
{json.dumps(behavior_block, ensure_ascii=False) if behavior_block else "none"}
{journal_section}

User message:
{user_text.strip()}

Respond in a way that:
 - aligns with the persona mode
 - respects their clarity and emotional state
 - gently improves clarity
 - mirrors their emotion before offering a supportive nudge
 - respects ritual phase guidance and rhythm pacing notes
 - ties response back to the stated memory thread
 - stays warm, grounded, and human (35-45 words).
""".strip()


__all__ = ["build_prompt"]
