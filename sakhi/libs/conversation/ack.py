EMOTION_ALIASES = {
    # energy-related
    "energetic": "excited",
    "motivated": "excited",
    "inspired": "excited",
    "focused": "calm",

    # low-energy
    "tired": "tired",
    "drained": "tired",
    "exhausted": "tired",
    "fatigued": "tired",

    # anxiety/stress
    "anxious": "anxious",
    "stressed": "anxious",
    "worried": "anxious",
    "tense": "anxious",
    "overwhelmed": "overwhelmed",

    # uncertainty / doubt
    "uncertain": "uncertain",
    "confused": "uncertain",
    "lost": "uncertain",
    "unsure": "uncertain",

    # calm / centered states
    "peaceful": "calm",
    "relaxed": "calm",
    "grounded": "calm",

    # positive / high affect
    "happy": "positive",
    "grateful": "grateful",
    "joyful": "positive",
    "content": "positive",

    # reflective / neutral introspection
    "thoughtful": "reflective",
    "curious": "reflective",
    "neutral": "neutral",
}

from dataclasses import dataclass
from typing import Callable, Optional


@dataclass
class AckContext:
    sentiment: str = "neutral"  # "heavy" | "neutral" | "positive"
    user_style: Optional[str] = None  # e.g., "concise", "warm"
    allow_llm: bool = True


def _sentiment_to_key(sentiment: str) -> str:
    s = (sentiment or "neutral").lower()
    if s in {"heavy", "negative", "very_negative"}:
        return "heavy"
    if s in {"positive", "very_positive"}:
        return "positive"
    return "neutral"


def compose_ack(
    policy,
    ctx: AckContext,
    llm_rephrase_fn: Optional[Callable[[str, str], str]] = None,
) -> str:
    """
    Picks an ack from policy and (optionally) routes it through a light LLM
    rephrase ONLY when needed (heavy sentiment or user style demands).
    """
    raw_emotion = (ctx.sentiment or "neutral").lower().strip()
    normalized_emotion = EMOTION_ALIASES.get(raw_emotion, raw_emotion)

    key = _sentiment_to_key(normalized_emotion)
    if hasattr(policy, "get_ack_by_emotion"):
        base = policy.get_ack_by_emotion(normalized_emotion, fallback=key)
    elif hasattr(policy, "get_ack"):
        base = policy.get_ack(key)  # from conversation.yaml -> ack_templates
    else:
        data = policy() if callable(policy) else policy
        templates = (data or {}).get("ack_templates", {})
        base = templates.get(key, templates.get("neutral", "Got it."))

    # Decide whether to rephrase
    wants_soft = key == "heavy"
    wants_style = (ctx.user_style in {"warm", "gentle"})

    rephrase_enabled = getattr(policy, "flags", {}).get("ack_llm_rephrase", True)

    if ctx.allow_llm and rephrase_enabled and (wants_soft or wants_style) and llm_rephrase_fn:
        sys_prompt = (
            "Rewrite the acknowledgement to sound natural and supportive. "
            "Keep under 12 words. No questions. No emojis."
        )
        return llm_rephrase_fn(base, sys_prompt)

    return base
