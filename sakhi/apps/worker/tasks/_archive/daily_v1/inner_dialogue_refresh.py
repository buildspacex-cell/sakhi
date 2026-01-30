from __future__ import annotations

import logging

from sakhi.apps.engine.inner_dialogue import engine as inner_engine
from sakhi.apps.api.core.db import exec as dbexec
from sakhi.apps.api.core.person_utils import resolve_person_id

logger = logging.getLogger(__name__)


async def inner_dialogue_refresh(person_id: str, last_message: str = "", context=None) -> None:
    try:
        resolved = await resolve_person_id(person_id) or person_id
        dialog = await inner_engine.compute_inner_dialogue(resolved, last_message, context or {})
        await dbexec(
            """
            INSERT INTO inner_dialogue_cache (person_id, dialogue, updated_at)
            VALUES ($1, $2::jsonb, NOW())
            ON CONFLICT (person_id) DO UPDATE
            SET dialogue = EXCLUDED.dialogue,
                updated_at = NOW()
            """,
            resolved,
            dialog,
        )
        await dbexec(
            """
            UPDATE personal_model
            SET inner_dialogue_state = $2::jsonb, updated_at = NOW()
            WHERE person_id = $1
            """,
            resolved,
            dialog,
        )
    except Exception as exc:
        logger.warning("inner_dialogue_refresh failed person=%s err=%s", person_id, exc)


__all__ = ["inner_dialogue_refresh"]
