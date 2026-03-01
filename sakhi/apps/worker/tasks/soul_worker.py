from __future__ import annotations

import asyncio
import datetime as dt
import json
import logging
from typing import List

from sakhi.apps.api.core.db import q, exec as dbexec
from sakhi.apps.brain.engines.soul_engine import update_soul_state
from sakhi.libs.schemas.settings import get_settings

logger = logging.getLogger(__name__)


async def _load_observations(person_id: str) -> List[str]:
    rows = await q(
        """
        SELECT text
        FROM memory_episodic
        WHERE person_id = $1
        ORDER BY updated_at DESC
        LIMIT 50
        """,
        person_id,
    )
    return [row.get("text") or "" for row in rows]


async def run(person_id: str) -> dict:
    settings = get_settings()
    if not settings.enable_identity_workers:
        logger.info("Worker disabled by safety gate: ENABLE_IDENTITY_WORKERS=false")
        return {"person_id": person_id, "updated": False}

    observations = await _load_observations(person_id)
    soul_state = await update_soul_state(person_id, observations, embeddings=None)
    payload = soul_state if isinstance(soul_state, str) else json.dumps(soul_state, ensure_ascii=False)

    await dbexec(
        """
        UPDATE personal_model
        SET soul_state = $2::jsonb,
            updated_at = $3
        WHERE person_id = $1
        """,
        person_id,
        payload,
        dt.datetime.utcnow(),
    )
    return {"person_id": person_id, "updated": True}


def enqueue(person_id: str) -> None:
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(run(person_id))
    except RuntimeError:
        asyncio.run(run(person_id))


__all__ = ["run", "enqueue"]
