from __future__ import annotations

from typing import Dict, List


def explain_anchors(anchors: Dict[str, float]) -> List[str]:
    lines: List[str] = []
    intent = anchors.get("intent_fit", 0.0)
    resources = anchors.get("resource_reality", 0.0)
    coherence = anchors.get("coherence", 0.0)
    risk = anchors.get("risk_drag", 0.0)

    if intent > 0.7:
        lines.append("High intent fit — this aligns with what the user truly wants.")
    elif intent < 0.4:
        lines.append("Low intent fit — seems tangential to current goals.")

    if resources > 0.7:
        lines.append("Resources look good — time, energy, and money allow this.")
    elif resources < 0.4:
        lines.append("Resources are constrained — execution may be stressful.")

    if coherence > 0.7:
        lines.append("Emotionally coherent with current values.")

    if risk > 0.6:
        lines.append("Potential friction or over-commitment risk.")

    return lines
