from __future__ import annotations

import logging
from typing import Any, Dict, List

LOGGER = logging.getLogger(__name__)


async def store_planned_items(*, person_id: str, plans: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Placeholder persistence hook. In this lightweight version we simply log.
    """

    if plans:
        LOGGER.debug("[IntentPlans] person=%s plans=%s", person_id, plans)
    return plans


__all__ = ["store_planned_items"]
