from __future__ import annotations

import logging
from typing import List, Dict, Any

from sakhi.apps.api.core.db import q as dbfetch, exec as dbexec
from sakhi.apps.worker.tasks.rhythm_forecast import run_rhythm_forecast

LOGGER = logging.getLogger(__name__)


async def run_rhythm_scheduler() -> bool:
    """
    Lightweight rhythm-refresh scheduler.
    Looks for personal_model.rhythm_state.refresh_hint == 'weekly' and refreshes forecasts.
    """

    rows: List[Dict[str, Any]] = await dbfetch(
        """
        SELECT person_id
        FROM personal_model
        WHERE rhythm_state->>'refresh_hint' = 'weekly'
        """
    )

    if not rows:
        return False

    for row in rows:
        person_id = row.get("person_id")
        if not person_id:
            continue

        LOGGER.info("[Rhythm Scheduler] Refreshing weekly forecast for %s", person_id)
        try:
            await run_rhythm_forecast(str(person_id))
        except Exception as exc:  # pragma: no cover - defensive logging
            LOGGER.error("[Rhythm Scheduler] Forecast failed for %s: %s", person_id, exc)
            continue

        await dbexec(
            """
            UPDATE personal_model
            SET rhythm_state = rhythm_state - 'refresh_hint',
                updated_at = NOW()
            WHERE person_id = $1
            """,
            person_id,
        )

    return True


__all__ = ["run_rhythm_scheduler"]
