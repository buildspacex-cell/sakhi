from __future__ import annotations

from typing import Dict, List

ANCHORS_ORDER = [
    "intent_fit",
    "commitment_load",
    "resource_reality",
    "coherence",
    "risk_drag",
    "rhythm_timing",
]


def build_prompt(context: Dict, options: List[Dict], impact: Dict[str, float], user_text: str) -> str:
    lines: List[str] = []
    lines.append("You are Sakhi, a clarity companion. Respect hard constraints and person values.")
    lines.append(f'USER SAID: "{user_text}"')
    anchors = " | ".join(f"{key}={impact.get(key, 0.0):.2f}" for key in ANCHORS_ORDER)
    lines.append(f"ANCHORS (0..1): {anchors}")

    aspects = context.get("aspects", {})
    for name, features in aspects.items():
        tops = []
        for key, value in features.items():
            if isinstance(value, dict) and "score" in value:
                tops.append(f"{key}:{value['score']:.2f}")
        if tops:
            lines.append(f"{name.upper()}: {', '.join(tops[:3])}")

    lines.append("OPTIONS:")
    for option in options:
        label = option.get("label", "")
        notes = option.get("notes", [])
        notes_str = " | ".join(notes) if notes else ""
        lines.append(f"- {option['id']}: {label} {notes_str}".strip())

    lines.append("Respond with: (a) Why this fits you (b) Trade-offs (c) Ask to pick A/B/C.")
    return "\n".join(lines)
