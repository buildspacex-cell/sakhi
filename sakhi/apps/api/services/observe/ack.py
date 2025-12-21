from __future__ import annotations

import random
from dataclasses import dataclass


ACK_MESSAGES = [
    "Got it. I've logged this for you.",
    "Captured. Want me to plan around it later?",
    "Thanks for sharing. I'll keep it in mind.",
    "Noted. Let me know if you want help turning this into a plan.",
]


@dataclass(slots=True)
class AckResponse:
    reply: str
    status: str = "queued"


def build_acknowledgement(text: str) -> AckResponse:
    """Return a lightweight acknowledgement for /memory/observe."""

    message = random.choice(ACK_MESSAGES)

    if "?" in text:
        message = "Captured. Want me to help plan something around this?"
    elif "thanks" in text.lower():
        message = "Anytime. Logging it so we can revisit when needed."

    return AckResponse(reply=message)


__all__ = ["AckResponse", "build_acknowledgement"]
