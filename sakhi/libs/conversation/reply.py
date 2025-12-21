from __future__ import annotations

from typing import List, Optional

from .policy_loader import policy


def pick_question(info_gaps: List[str]) -> Optional[str]:
    p = policy()
    templates = p.get("question_templates", {})
    for gap in info_gaps:
        key = f"{gap}_missing"
        if key in templates:
            return templates[key]
    return None


def ack_line(sentiment: Optional[float], summary: str = "this") -> str:
    p = policy()
    templates = p.get("ack_templates", {})
    heavy = templates.get("heavy", templates.get("neutral", "Noted."))
    positive = templates.get("positive", templates.get("neutral", "Noted."))
    neutral = templates.get("neutral", "Noted.")

    if sentiment is not None and sentiment < -0.3:
        return heavy.replace("{summary}", summary)
    if sentiment is not None and sentiment > 0.3:
        return positive.replace("{summary}", summary)
    return neutral.replace("{summary}", summary)
