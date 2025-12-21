from __future__ import annotations

import datetime as dt
import logging

from sakhi.apps.api.core.db import q, exec as dbexec

logger = logging.getLogger(__name__)


async def intent_evolution_decay(person_id: str) -> None:
    """Daily decay on intent strengths."""
    try:
        rows = await q(
            """
            SELECT intent_name, strength
            FROM intent_evolution
            WHERE person_id = $1
            """,
            person_id,
        )
    except Exception as exc:
        logger.warning("intent_evolution_decay load failed person=%s err=%s", person_id, exc)
        return

    for row in rows or []:
        strength = max(0.0, float(row.get("strength") or 0) - 0.02)
        trend = "down" if strength < (row.get("strength") or 0) else "stable"
        try:
            await dbexec(
                """
                UPDATE intent_evolution
                SET strength = $3, trend = $4, last_seen = $5
                WHERE person_id = $1 AND intent_name = $2
                """,
                person_id,
                row.get("intent_name"),
                strength,
                trend,
                dt.datetime.utcnow(),
            )
        except Exception as exc:
            logger.warning("intent_evolution_decay update failed intent=%s err=%s", row.get("intent_name"), exc)


__all__ = ["intent_evolution_decay"]
