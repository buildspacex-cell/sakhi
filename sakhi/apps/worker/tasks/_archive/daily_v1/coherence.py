from __future__ import annotations

import logging

from sakhi.apps.api.core.db import exec as dbexec
from sakhi.apps.api.core.person_utils import resolve_person_id
from sakhi.apps.engine.coherence import compute_coherence
from sakhi.libs.schemas.settings import get_settings

logger = logging.getLogger(__name__)


async def run_coherence(person_id: str) -> None:
    try:
        settings = get_settings()
        if not settings.enable_identity_workers:
            logger.info("Worker disabled by safety gate: ENABLE_IDENTITY_WORKERS=false")
            return

        resolved = await resolve_person_id(person_id) or person_id
        state = await compute_coherence(resolved)
        await dbexec(
            """
            INSERT INTO coherence_cache (person_id, coherence_state, updated_at)
            VALUES ($1, $2::jsonb, NOW())
            ON CONFLICT (person_id) DO UPDATE
            SET coherence_state = EXCLUDED.coherence_state,
                updated_at = NOW()
            """,
            resolved,
            state,
        )
        await dbexec(
            """
            UPDATE personal_model
            SET coherence_state = $2::jsonb, updated_at = NOW()
            WHERE person_id = $1
            """,
            resolved,
            state,
        )
    except Exception as exc:
        logger.warning("run_coherence failed person=%s err=%s", person_id, exc)


__all__ = ["run_coherence"]
