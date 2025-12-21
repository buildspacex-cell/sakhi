from __future__ import annotations

import logging

from sakhi.apps.api.core.db import exec as dbexec
from sakhi.apps.api.core.person_utils import resolve_person_id
from sakhi.apps.engine.forecast import compute_forecast

logger = logging.getLogger(__name__)


async def run_forecast(person_id: str) -> None:
    try:
        resolved = await resolve_person_id(person_id) or person_id
        state = await compute_forecast(resolved)
        await dbexec(
            """
            INSERT INTO forecast_cache (person_id, forecast_state, updated_at)
            VALUES ($1, $2::jsonb, NOW())
            ON CONFLICT (person_id) DO UPDATE
            SET forecast_state = EXCLUDED.forecast_state,
                updated_at = NOW()
            """,
            resolved,
            state,
        )
        await dbexec(
            """
            UPDATE personal_model
            SET forecast_state = $2::jsonb, updated_at = NOW()
            WHERE person_id = $1
            """,
            resolved,
            state,
        )
    except Exception as exc:
        logger.warning("run_forecast failed person=%s err=%s", person_id, exc)


__all__ = ["run_forecast"]
