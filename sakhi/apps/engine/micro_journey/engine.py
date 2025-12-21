from __future__ import annotations

import datetime
from typing import Any, Dict, List

from sakhi.apps.api.core.db import exec as dbexec
from sakhi.apps.api.core.person_utils import resolve_person_id
from sakhi.apps.engine.mini_flow.engine import generate_mini_flow
from sakhi.apps.engine.mini_flow.adjuster import determine_rhythm_slot
from sakhi.apps.engine.micro_journey.sequencer import apply_adaptive_sequencing
from sakhi.apps.engine.micro_journey.pacing import apply_pacing


def select_flow_count(now_dt: datetime.datetime) -> int:
    slot = determine_rhythm_slot(now_dt)
    if slot in {"morning", "midday"}:
        return 3
    if slot in {"afternoon", "evening"}:
        return 2
    return 1


async def generate_micro_journey(person_id: str) -> Dict[str, Any]:
    now = datetime.datetime.utcnow()
    rhythm_slot = determine_rhythm_slot(now)
    flow_count = select_flow_count(now)
    flows: List[Dict[str, Any]] = []
    for _ in range(flow_count):
        flow = await generate_mini_flow(person_id)
        flows.append(flow)

    journey = {
        "person_id": person_id,
        "generated_at": now.isoformat(),
        "rhythm_slot": rhythm_slot,
        "flow_count": flow_count,
        "flows": flows,
        "structure": {
            "total_estimated_minutes": flow_count * 15,
            "order_pattern": "sequential",
            "recommended_pacing": "move flow-to-flow without long delays",
        },
    }
    journey = apply_adaptive_sequencing(journey)
    journey = apply_pacing(journey)
    return journey


async def persist_micro_journey(person_id: str, journey: Dict[str, Any]) -> None:
    """Upsert journey cache and update personal_model."""
    resolved = await resolve_person_id(person_id) or person_id
    try:
        await dbexec(
            """
            INSERT INTO micro_journey_cache (person_id, journey, flow_count, rhythm_slot)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (person_id)
            DO UPDATE SET journey = EXCLUDED.journey,
                          flow_count = EXCLUDED.flow_count,
                          rhythm_slot = EXCLUDED.rhythm_slot,
                          generated_at = now()
            """,
            resolved,
            journey,
            journey.get("flow_count") or 0,
            journey.get("rhythm_slot"),
        )
    except Exception:
        return

    try:
        await dbexec(
            """
            UPDATE personal_model
            SET micro_journey_state = $2
            WHERE person_id = $1
            """,
            resolved,
            {
                "flows": journey.get("flows") or [],
                "flow_count": journey.get("flow_count") or 0,
                "rhythm_slot": journey.get("rhythm_slot"),
                "generated_at": journey.get("generated_at"),
            },
        )
    except Exception:
        return


__all__ = ["select_flow_count", "generate_micro_journey", "persist_micro_journey"]
