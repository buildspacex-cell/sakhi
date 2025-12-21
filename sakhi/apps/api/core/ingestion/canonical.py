from __future__ import annotations

import datetime as dt
from typing import Any, Dict, Optional

from sakhi.apps.api.services.memory.canonical_ingest import process_observation


async def canonical_ingest(
    *,
    person_id: str,
    entry_id: Optional[str],
    text: str,
    layer: str,
    tags: Optional[list[str]] = None,
    triage: Optional[Dict[str, Any]] = None,
    ts: Optional[dt.datetime] = None,
) -> Dict[str, Any]:
    """
    Wrapper around the canonical ingestion engine so routes can call a stable interface.
    """

    metadata = {"tags": tags or []}
    return await process_observation(
        person_id=person_id,
        entry_id=entry_id,
        text=text,
        layer=layer,
        ts=ts,
        raw_extraction=triage,
        metadata=metadata,
    )


__all__ = ["canonical_ingest"]
