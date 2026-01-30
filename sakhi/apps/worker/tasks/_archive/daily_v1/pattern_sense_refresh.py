from __future__ import annotations

import logging

from sakhi.apps.engine.pattern_sense import engine as pattern_engine
from sakhi.apps.api.core.db import exec as dbexec, q
from sakhi.apps.api.core.person_utils import resolve_person_id

logger = logging.getLogger(__name__)


async def pattern_sense_refresh(person_id: str) -> None:
    try:
        resolved = await resolve_person_id(person_id) or person_id
        patterns = await pattern_engine.compute_patterns(resolved)
        await dbexec(
            """
            INSERT INTO pattern_sense_cache (person_id, patterns, updated_at)
            VALUES ($1, $2::jsonb, NOW())
            ON CONFLICT (person_id) DO UPDATE
            SET patterns = EXCLUDED.patterns, updated_at = NOW()
            """,
            resolved,
            patterns,
        )
        # sync personal_model
        try:
            await dbexec(
                """
                UPDATE personal_model
                SET pattern_sense = $2::jsonb, updated_at = NOW()
                WHERE person_id = $1
                """,
                resolved,
                patterns,
            )
        except Exception as exc:
            logger.warning("pattern_sense_refresh personal_model update failed person=%s err=%s", resolved, exc)
    except Exception as exc:
        logger.warning("pattern_sense_refresh failed person=%s err=%s", person_id, exc)


__all__ = ["pattern_sense_refresh"]
