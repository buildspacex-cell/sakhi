from __future__ import annotations

import logging
from datetime import datetime, timezone

try:
    from sakhi.libs.schemas.db import get_async_pool
except (ImportError, ModuleNotFoundError):  # pragma: no cover - optional dependency
    get_async_pool = None  # type: ignore[assignment]

LOGGER = logging.getLogger(__name__)

TEMPLATES = {
    "gentle": "I kept thinking of your note on {theme}. Anything open since?",
    "warm": "A little while has passed. How has your rhythm been?",
    "deep": "Silence can be part of the path. Start where we left, or fresh?",
}


async def last_contact(user_id: str):
    if get_async_pool is None:
        LOGGER.debug("jobs_presence.last_contact skipped – async db unavailable.")
        return None

    pool = await get_async_pool()
    async with pool.acquire() as conn:
        return await conn.fetchval(
            "SELECT max(created_at) FROM journal_entries WHERE user_id=$1",
            user_id,
        )


import datetime


async def outreach(person_id: str):
    """
    Placeholder outreach handler.

    Called by scheduler to simulate Sakhi's gentle presence check-ins.
    Currently logs activity but does not write to DB.
    """
    ts = datetime.datetime.utcnow().isoformat()
    print(f"[presence.outreach] (stub) Would send outreach for person {person_id} at {ts}")
    return {"person_id": person_id, "ts": ts, "status": "stub-ok"}
