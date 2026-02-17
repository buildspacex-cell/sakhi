"""Daily coherence state refresh → personal_model.coherence_state."""

from __future__ import annotations

import json
import logging
from typing import Any, Dict

from sakhi.apps.api.core.db import exec as dbexec
from sakhi.apps.api.core.person_utils import resolve_person_id
from sakhi.apps.engine.coherence.engine import compute_coherence
from sakhi.libs.schemas.settings import get_settings

logger = logging.getLogger(__name__)


async def run_coherence_refresh(person_id: str) -> Dict[str, Any]:
    """
    Compute 6-dimension coherence assessment and persist to personal_model.

    Writes to:
    - coherence_cache (fallback for /v1/coherence/report API)
    - personal_model.coherence_state (read by context loader every turn)
    """
    try:
        settings = get_settings()
        if not settings.enable_identity_workers:
            return {"person_id": person_id, "updated": False, "reason": "disabled"}

        resolved = await resolve_person_id(person_id) or person_id
        state = await compute_coherence(resolved)

        state_json = json.dumps(state, ensure_ascii=False)

        # Write to coherence_cache (fallback store for API route)
        await dbexec(
            """INSERT INTO coherence_cache (person_id, coherence_state, updated_at)
               VALUES ($1, $2::jsonb, NOW())
               ON CONFLICT (person_id) DO UPDATE
               SET coherence_state = EXCLUDED.coherence_state, updated_at = NOW()""",
            resolved,
            state_json,
        )
        # Write to personal_model column (read by context loader every turn)
        await dbexec(
            """UPDATE personal_model
               SET coherence_state = $2::jsonb, updated_at = NOW()
               WHERE person_id = $1""",
            resolved,
            state_json,
        )
        logger.info(
            "[coherence_refresh] updated person=%s score=%.2f",
            resolved,
            state.get("coherence_score", 0),
        )
        return {
            "person_id": resolved,
            "updated": True,
            "coherence_score": state.get("coherence_score"),
        }
    except Exception as exc:
        logger.error(
            "[coherence_refresh] failed person=%s err=%s",
            person_id,
            exc,
            exc_info=True,
        )
        return {"person_id": person_id, "updated": False, "error": str(exc)}


__all__ = ["run_coherence_refresh"]
