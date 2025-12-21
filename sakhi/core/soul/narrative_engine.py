from __future__ import annotations

from typing import Any, Dict, Sequence


def compute_fast_narrative(short_term: Sequence[Dict[str, Any]] | None, soul_state: Dict[str, Any] | None) -> Dict[str, Any]:
    """
    Purely deterministic, no LLM. Returns quickly for turn-time use.
    Output fields:
      - dominant_theme
      - emotional_trend
      - value_alignment (0-1)
      - shadow_pressure (0-1)
    """
    st = short_term or []
    soul = soul_state or {}

    # dominant theme from identity themes / recent text tags
    themes = soul.get("identity_themes") or []
    dominant_theme = themes[0] if themes else None

    # crude emotional trend from last 3 short-term entries (if they have triage/emotion hint)
    emotions = [entry.get("emotion") or entry.get("triage", {}).get("emotion") for entry in st[-3:]]
    emotion_counts: Dict[str, int] = {}
    for e in emotions:
        if not e:
            continue
        key = str(e)
        emotion_counts[key] = emotion_counts.get(key, 0) + 1
    emotional_trend = max(emotion_counts, key=emotion_counts.get) if emotion_counts else "neutral"

    values = soul.get("core_values") or []
    friction = soul.get("friction") or []
    # naive alignment: more values and fewer friction/conflicts => higher
    value_alignment = min(1.0, max(0.0, (len(values) + 1) / ((len(friction) or 0) + 3)))

    shadow = soul.get("shadow") or []
    light = soul.get("light") or []
    shadow_pressure = min(1.0, (len(shadow) + 1) / (len(light) + len(shadow) + 2))

    return {
        "dominant_theme": dominant_theme,
        "emotional_trend": emotional_trend,
        "value_alignment": value_alignment,
        "shadow_pressure": shadow_pressure,
    }
