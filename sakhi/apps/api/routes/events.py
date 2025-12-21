from __future__ import annotations

import asyncio
import json
import logging

import asyncpg
from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from sakhi.apps.api.core.db import get_db

router = APIRouter(prefix="/events", tags=["dev"])
LOGGER = logging.getLogger(__name__)


async def event_stream(person_id: str):
    db = await get_db()
    last_id = 0
    try:
        while True:
            try:
                rows = await db.fetch(
                    """
                    SELECT * FROM system_events
                    WHERE person_id = $1 AND id > $2
                    ORDER BY id ASC
                    """,
                    person_id,
                    last_id,
                )
            except asyncpg.UndefinedTableError:
                LOGGER.warning(
                    "system_events table missing; SSE stream disabled until migrations run."
                )
                yield "event: error\ndata: {\"message\": \"system_events table missing\"}\n\n"
                break
            except Exception as exc:  # pragma: no cover - defensive guard
                LOGGER.warning("event_stream fetch failed: %s", exc)
                await asyncio.sleep(2)
                continue

            for row in rows:
                last_id = row["id"]
                yield f"data: {json.dumps(dict(row), default=str)}\n\n"
            await asyncio.sleep(1)
    finally:
        await db.close()


@router.get("/stream/{person_id}")
async def stream(person_id: str):
    return StreamingResponse(event_stream(person_id), media_type="text/event-stream")


__all__ = ["router"]
