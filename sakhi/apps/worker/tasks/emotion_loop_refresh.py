from __future__ import annotations

import logging

from sakhi.apps.engine.emotion_loop import engine as emotion_loop_engine
from sakhi.apps.api.core.db import exec as dbexec, q
from sakhi.apps.api.core.person_utils import resolve_person_id

logger = logging.getLogger(__name__)


async def emotion_loop_refresh(person_id: str) -> None:
    try:
        resolved = await resolve_person_id(person_id) or person_id
        loop_state = await emotion_loop_engine.compute_emotion_loop_for_person(resolved)
        if loop_state:
            # persist to personal_model
            try:
                pm = await q("SELECT long_term FROM personal_model WHERE person_id = $1", resolved, one=True)
                long_term = (pm.get("long_term") or {}) if pm else {}
                long_term["emotion_state"] = loop_state
                await dbexec(
                    """
                    UPDATE personal_model
                    SET long_term = $2::jsonb, updated_at = NOW()
                    WHERE person_id = $1
                    """,
                    resolved,
                    long_term,
                )
            except Exception as exc:
                logger.warning("emotion_loop_refresh personal_model update failed person=%s err=%s", resolved, exc)
    except Exception as exc:
        logger.warning("emotion_loop_refresh failed person=%s err=%s", person_id, exc)


__all__ = ["emotion_loop_refresh"]
