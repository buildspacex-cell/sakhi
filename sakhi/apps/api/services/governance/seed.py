"""Default governance constraints and objectives for new users.

Call ``seed_defaults(person_id)`` during onboarding or manually for demo users
to populate the governance_constraints and governance_objectives tables.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime

LOGGER = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Default constraints
# ---------------------------------------------------------------------------

DEFAULT_CONSTRAINTS: list[dict] = [
    {
        "id": "sleep-boundary",
        "constraint_type": "time_boundary",
        "field": "proposed_hour",
        "operator": "lte",
        "value": 22,
        "description": "Avoid stimulating suggestions after 10 PM",
        "source": "objective:sleep-health:v1",
        "priority": 2,  # MEDIUM — confirm, don't block
    },
    {
        "id": "high-drift-gate",
        "constraint_type": "drift_threshold",
        "field": "drift_percentage",
        "operator": "lt",
        "value": 40,
        "description": "Require gentle approach when drift exceeds 40%",
        "source": "system",
        "priority": 3,  # HARD — block proactive suggestions
    },
    {
        "id": "chaos-guard",
        "constraint_type": "value_alignment",
        "field": "friction_state",
        "operator": "neq",
        "value": "chaos",
        "description": "When in chaos, do not add cognitive load with new suggestions",
        "source": "objective:anxiety-management:v1",
        "priority": 2,
    },
]


# ---------------------------------------------------------------------------
# Default objectives
# ---------------------------------------------------------------------------

DEFAULT_OBJECTIVES: list[dict] = [
    {
        "objective_id": "sleep-health",
        "version": 1,
        "title": "Maintain healthy sleep boundaries",
        "description": "Wind down after 10 PM. Avoid stimulating activities late at night.",
        "data": {"wind_down_hour": 22, "wake_target_hour": 7},
        "source": "onboarding",
        "reason": "Initial onboarding default",
    },
    {
        "objective_id": "anxiety-management",
        "version": 1,
        "title": "Reduce anxiety through grounding",
        "description": "When in a chaotic state, focus on grounding rather than adding tasks.",
        "data": {"preferred_techniques": ["breathing", "grounding", "body_scan"]},
        "source": "onboarding",
        "reason": "Initial onboarding default",
    },
]


# ---------------------------------------------------------------------------
# Seeder
# ---------------------------------------------------------------------------


async def seed_defaults(person_id: str) -> dict[str, int]:
    """Insert default constraints and objectives for *person_id*.

    Uses ``ON CONFLICT DO NOTHING`` so it's safe to call repeatedly.
    Returns counts of rows inserted.
    """
    from sakhi.apps.api.core.db import get_db

    db = await get_db()
    constraints_inserted = 0
    objectives_inserted = 0

    try:
        for c in DEFAULT_CONSTRAINTS:
            result = await db.execute(
                """
                INSERT INTO governance_constraints
                    (id, person_id, constraint_type, field, operator, value,
                     description, source, priority, active, metadata)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, true, '{}')
                ON CONFLICT (id, person_id) DO NOTHING
                """,
                c["id"],
                person_id,
                c["constraint_type"],
                c["field"],
                c["operator"],
                json.dumps(c["value"]),
                c["description"],
                c["source"],
                c["priority"],
            )
            if result and "INSERT 0 1" in result:
                constraints_inserted += 1

        now = datetime.now(UTC)
        for o in DEFAULT_OBJECTIVES:
            result = await db.execute(
                """
                INSERT INTO governance_objectives
                    (objective_id, version, person_id, ts, title, description,
                     data, source, reason, parent_version)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, NULL)
                ON CONFLICT (objective_id, version, person_id) DO NOTHING
                """,
                o["objective_id"],
                o["version"],
                person_id,
                now,
                o["title"],
                o["description"],
                json.dumps(o["data"]),
                o["source"],
                o["reason"],
            )
            if result and "INSERT 0 1" in result:
                objectives_inserted += 1
    finally:
        await db.close()

    LOGGER.info(
        "Seeded governance defaults for %s: %d constraints, %d objectives",
        person_id, constraints_inserted, objectives_inserted,
    )
    return {"constraints": constraints_inserted, "objectives": objectives_inserted}
