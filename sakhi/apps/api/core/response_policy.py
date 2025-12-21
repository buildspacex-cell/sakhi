from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from sakhi.apps.api.core.config_loader import get_policy
from sakhi.apps.api.core.suggestions import recent_suggestions


@dataclass
class PolicyDecision:
    allow: bool
    reason: str
    meta: Dict[str, Any]


def _policy() -> Dict[str, Any]:
    return get_policy("response_policy")


async def should_suggest(
    person_id: str,
    *,
    state_confidence: Optional[float],
    need: Optional[str] = None,
) -> PolicyDecision:
    return PolicyDecision(
        allow=True,
        reason="enabled",
        meta={
            "state_confidence": state_confidence,
            "need": need,
        },
    )
