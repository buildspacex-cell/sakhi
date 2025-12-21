from __future__ import annotations

import logging

from sakhi.apps.engine.narrative import engine as narrative_engine
from sakhi.apps.api.core.db import exec as dbexec
from sakhi.apps.api.core.person_utils import resolve_person_id

logger = logging.getLogger(__name__)


async def narrative_arc_refresh(person_id: str) -> None:
    try:
        resolved = await resolve_person_id(person_id) or person_id
        arcs = await narrative_engine.compute_narrative_arcs(resolved)
        await dbexec(
            """
            UPDATE personal_model
            SET narrative_arcs = $2::jsonb, updated_at = NOW()
            WHERE person_id = $1
            """,
            resolved,
            arcs,
        )
    except Exception as exc:
        logger.warning("narrative_arc_refresh failed person=%s err=%s", person_id, exc)


__all__ = ["narrative_arc_refresh"]
