"""Daily alignment state refresh → personal_model.alignment_state + daily_alignment_cache."""

from __future__ import annotations

import json
import logging
from typing import Any, Dict

from sakhi.apps.api.core.db import exec as dbexec
from sakhi.apps.api.core.person_utils import resolve_person_id
from sakhi.apps.engine.alignment.engine import compute_alignment_map

logger = logging.getLogger(__name__)


def _derive_alignment_state(alignment_map: Dict[str, Any]) -> Dict[str, Any]:
    """Derive consumer-facing scores from raw alignment map.

    Consumers expect:
    - alignment_score (moment_model: < 0.4 → adds "fatigue" risk)
    - tension_score (deliberation_scaffold: >= 0.6 → "values vs priority" domain)
    - conflict_zones (deliberation_scaffold: tension labels)
    """
    recommended = alignment_map.get("recommended_actions") or []
    avoid = alignment_map.get("avoid_actions") or []
    safeguards = alignment_map.get("emotional_safeguards") or []
    total = max(1, len(recommended) + len(avoid))

    alignment_score = round(len(recommended) / total, 3)
    tension_score = round(len(avoid) / total + (0.1 * len(safeguards)), 3)
    tension_score = min(1.0, tension_score)

    conflict_zones = [a.get("title", "") for a in avoid[:5] if a.get("title")]
    if safeguards:
        conflict_zones.extend(safeguards[:3])

    return {
        "alignment_score": alignment_score,
        "tension_score": tension_score,
        "conflict_zones": conflict_zones,
        "action_suggestions": [
            a.get("title", "") for a in recommended[:5] if a.get("title")
        ],
        "energy_profile": alignment_map.get("energy_profile"),
        "focus_profile": alignment_map.get("focus_profile"),
        "self_care_suggestions": alignment_map.get("self_care_suggestions") or [],
        "alignment_map": alignment_map,
    }


async def run_alignment_refresh(person_id: str) -> Dict[str, Any]:
    """
    Compute values-to-goals alignment and persist to personal_model.

    Writes to:
    - daily_alignment_cache (read by coherence engine for alignment dimension)
    - personal_model.alignment_state (read by context loader every turn)
    """
    try:
        resolved = await resolve_person_id(person_id) or person_id
        alignment_map = await compute_alignment_map(resolved)
        if alignment_map is None:
            return {"person_id": resolved, "updated": False, "reason": "no_data"}

        map_json = json.dumps(alignment_map, ensure_ascii=False)

        # Write raw map to daily_alignment_cache (coherence engine reads this)
        await dbexec(
            """INSERT INTO daily_alignment_cache (person_id, alignment_map, updated_at)
               VALUES ($1, $2::jsonb, NOW())
               ON CONFLICT (person_id) DO UPDATE
               SET alignment_map = EXCLUDED.alignment_map, updated_at = NOW()""",
            resolved,
            map_json,
        )

        # Derive consumer-facing alignment state
        state = _derive_alignment_state(alignment_map)
        state_json = json.dumps(state, ensure_ascii=False)

        # Write to personal_model column (read by context loader every turn)
        await dbexec(
            """UPDATE personal_model
               SET alignment_state = $2::jsonb, updated_at = NOW()
               WHERE person_id = $1""",
            resolved,
            state_json,
        )
        logger.info(
            "[alignment_refresh] updated person=%s score=%.2f tension=%.2f",
            resolved,
            state["alignment_score"],
            state["tension_score"],
        )
        return {
            "person_id": resolved,
            "updated": True,
            "alignment_score": state["alignment_score"],
        }
    except Exception as exc:
        logger.error(
            "[alignment_refresh] failed person=%s err=%s",
            person_id,
            exc,
            exc_info=True,
        )
        return {"person_id": person_id, "updated": False, "error": str(exc)}


__all__ = ["run_alignment_refresh"]
