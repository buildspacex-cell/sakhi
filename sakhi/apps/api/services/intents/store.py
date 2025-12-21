from __future__ import annotations

import logging
import uuid
from typing import Any, Dict

LOGGER = logging.getLogger(__name__)


async def store_intent(*, person_id: str, entry_id: str | None, intent: Dict[str, Any]) -> Dict[str, Any]:
    """
    Minimal persistence shim. We don't write to a DB table here;
    instead we enrich the intent payload with IDs so downstream
    code can operate predictably.
    """

    enriched = {
        "id": intent.get("id") or str(uuid.uuid4()),
        "person_id": person_id,
        "entry_id": entry_id,
        **intent,
    }
    LOGGER.debug("[IntentStore] person=%s entry=%s intent=%s", person_id, entry_id, intent)
    return enriched


__all__ = ["store_intent"]
