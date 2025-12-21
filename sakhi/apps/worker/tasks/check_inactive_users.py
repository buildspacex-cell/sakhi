from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List

from sakhi.apps.worker.utils.db import db_find
from sakhi.apps.worker.utils.response_composer import compose_response

LOGGER = logging.getLogger(__name__)


def check_inactive_users() -> None:
    """
    Detect users silent >24h, send gentle reconnection message.
    """
    asyncio.run(_check_inactive_users_async())


async def _check_inactive_users_async() -> None:
    users: List[Dict[str, Any]] = db_find("session_continuity")
    if not users:
        return

    now = datetime.now(timezone.utc)
    for user in users:
        last_ts = user.get("last_interaction_ts")
        person_id = user.get("person_id")
        if not person_id or not last_ts:
            continue
        try:
            last_time = datetime.fromisoformat(str(last_ts))
        except ValueError:
            continue
        if (now - last_time).total_seconds() <= 86400:
            continue

        reply = await compose_response(
            person_id,
            intent="reconnect_prompt",
            context={"last_emotion": user.get("last_emotion")},
        )
        send_message(person_id, reply)


def send_message(person_id: Any, text: str) -> None:
    LOGGER.info("inactive_user.nudge person_id=%s text=%s", person_id, text)


__all__ = ["check_inactive_users"]
