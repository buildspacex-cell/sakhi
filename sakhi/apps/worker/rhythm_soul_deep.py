from __future__ import annotations

from typing import Any, Dict
import logging
import json

from sakhi.apps.api.core.db import q, exec as dbexec
from sakhi.core.rhythm.rhythm_soul_engine import compute_deep_rhythm_soul

logger = logging.getLogger(__name__)

# Rhythm Soul Deep is a Sensemaking worker.
# It detects alignment and tension between rhythm and soul signals.
# It MUST NOT:
# - generate advice or recommendations
# - form identity or narrative
# - predict future outcomes
# - suggest actions or schedules

async def run_rhythm_soul_deep(person_id: str) -> Dict[str, Any]:
    logger.info("[rhythm_soul] start", extra={"person_id": person_id})

    pm_row = await q("SELECT rhythm_state, soul_state FROM personal_model WHERE person_id = $1", person_id, one=True)
    rhythm_state = (pm_row or {}).get("rhythm_state") or {}
    soul_state = (pm_row or {}).get("soul_state") or {}

    def _normalize(val: Any) -> Dict[str, Any]:
        if isinstance(val, str):
            try:
                return json.loads(val)
            except Exception:
                return {}
        return val if isinstance(val, dict) else {}

    rhythm_state = _normalize(rhythm_state)
    soul_state = _normalize(soul_state)

    if not rhythm_state or not soul_state:
        logger.info("[rhythm_soul] skipped: missing inputs", extra={"person_id": person_id})
        return {}

    try:
        deep = compute_deep_rhythm_soul(person_id, [], rhythm_state, soul_state)
        await dbexec(
            "UPDATE personal_model SET rhythm_soul_state = $2::jsonb, updated_at = NOW() WHERE person_id = $1",
            person_id,
            json.dumps(deep, ensure_ascii=False),
        )
        logger.info(
            "[rhythm_soul] updated",
            extra={
                "person_id": person_id,
                "alignment_level": deep.get("alignment_level"),
                "tension_count": len(deep.get("tension_zones") or []),
                "coherence_count": len(deep.get("coherence_zones") or []),
            },
        )
        return deep
    except Exception as exc:
        logger.error("[rhythm_soul] error", extra={"person_id": person_id, "error": str(exc)})
        return {}
