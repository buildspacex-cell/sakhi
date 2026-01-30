from __future__ import annotations

import logging

from sakhi.apps.api.core.db import exec as dbexec
from sakhi.apps.api.core.person_utils import resolve_person_id
from sakhi.apps.engine.identity_drift import engine as identity_engine
from sakhi.libs.schemas.settings import get_settings

logger = logging.getLogger(__name__)


async def identity_drift_refresh(person_id: str) -> None:
    try:
        settings = get_settings()
        if not settings.enable_identity_workers:
            logger.info("Worker disabled by safety gate: ENABLE_IDENTITY_WORKERS=false")
            return

        resolved = await resolve_person_id(person_id) or person_id
        state = await identity_engine.compute_identity_state(resolved)
        await dbexec(
            """
            INSERT INTO identity_drift_cache (person_id, identity_state, updated_at)
            VALUES ($1, $2::jsonb, NOW())
            ON CONFLICT (person_id) DO UPDATE
            SET identity_state = EXCLUDED.identity_state,
                updated_at = NOW()
            """,
            resolved,
            state,
        )
        await dbexec(
            """
            UPDATE personal_model
            SET identity_state = $2::jsonb, updated_at = NOW()
            WHERE person_id = $1
            """,
            resolved,
            state,
        )
    except Exception as exc:
        logger.warning("identity_drift_refresh failed person=%s err=%s", person_id, exc)


__all__ = ["identity_drift_refresh"]
