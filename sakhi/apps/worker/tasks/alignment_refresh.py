from __future__ import annotations

import logging

from sakhi.apps.engine.alignment import engine as alignment_engine
from sakhi.apps.engine.coherence import engine as coherence_engine
from sakhi.apps.api.core.db import exec as dbexec, q
from sakhi.apps.api.core.person_utils import resolve_person_id

logger = logging.getLogger(__name__)


async def alignment_refresh(person_id: str) -> None:
    try:
        resolved = await resolve_person_id(person_id) or person_id
        alignment_map = await alignment_engine.compute_alignment_map(resolved)
        if alignment_map is None:
            return
        await dbexec(
            """
            INSERT INTO daily_alignment_cache (person_id, alignment_map, updated_at)
            VALUES ($1, $2::jsonb, NOW())
            ON CONFLICT (person_id) DO UPDATE
            SET alignment_map = EXCLUDED.alignment_map,
                updated_at = NOW()
            """,
            resolved,
            alignment_map,
        )
        # sync into personal_model
        try:
            pm = await q("SELECT long_term FROM personal_model WHERE person_id = $1", resolved, one=True)
            long_term = (pm.get("long_term") or {}) if pm else {}
            long_term["alignment_state"] = {"alignment_map": alignment_map, "updated_at": alignment_map.get("updated_at")}
            try:
                coherence_report = await coherence_engine.compute_coherence(resolved)
                long_term["coherence_report"] = coherence_report
            except Exception:
                pass
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
            logger.warning("alignment_refresh personal_model sync failed person=%s err=%s", resolved, exc)
    except Exception as exc:
        logger.warning("alignment_refresh failed person=%s err=%s", person_id, exc)


__all__ = ["alignment_refresh"]
