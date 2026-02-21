"""
Governance Demo Seeder
----------------------
Seeds governance constraints and events for the simulation demo.

Provides:
- 3 universal constraints (work for all profile types)
- 2 base events for contradiction detection
- Idempotent: deletes and re-inserts on each call
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime, timedelta
from typing import Any, Dict, Optional
from uuid import uuid4

from sakhi.apps.api.core.db import exec as dbexec, q as dbquery
from sakhi.apps.api.services.demo.user_seeder import DEMO_USER_ID

LOGGER = logging.getLogger(__name__)

# Constraint IDs (stable for idempotent seeding)
CONSTRAINT_NO_WORK_AFTER_10PM = "sim-c-no-work-after-10pm"
CONSTRAINT_PROTECT_FOCUS = "sim-c-protect-focus-time"
CONSTRAINT_DRIFT_SAFETY = "sim-c-drift-safety"

# Event IDs (stable for idempotent seeding)
EVENT_REJECTED_WALK = "sim-evt-rejected-walk"
EVENT_COMMITTED_MOVING = "sim-evt-committed-moving"


async def seed_governance_demo_data(person_id: Optional[str] = None) -> Dict[str, Any]:
    """Seed governance constraints and events for the simulation demo.

    Constraints (universal — same for all profiles):
        1. no_work_after_10pm | HARD(3) | time_boundary | proposed_hour >= 22
        2. protect_focus_time | MEDIUM(2) | commitment
        3. drift_safety | SOFT(1) | drift_threshold | drift_percentage >= 40

    Events (for contradiction detection):
        1. "suggest_exercise" → "rejected" | yesterday | "too busy"
        2. "email_reply" → "committed" | 3 weeks ago | "considering moving"

    The 3-profile differentiation comes from the frontend sending
    different action_context per profile, NOT from different DB rows.
    """
    person_id = person_id or DEMO_USER_ID
    LOGGER.info("[demo] Seeding governance data for person_id=%s", person_id)

    # 1. Clear existing simulation-specific data (idempotent)
    await dbexec(
        "DELETE FROM governance_constraints WHERE person_id = $1 AND id LIKE 'sim-%'",
        person_id,
    )
    await dbexec(
        "DELETE FROM governance_events WHERE person_id = $1 AND id LIKE 'sim-%'",
        person_id,
    )

    # 2. Seed constraints
    constraints = [
        {
            "id": CONSTRAINT_NO_WORK_AFTER_10PM,
            "constraint_type": "time_boundary",
            "field": "proposed_hour",
            "operator": "gte",
            "value": json.dumps(22),
            "description": "No work-related suggestions after 10 PM — respecting your sleep boundary",
            "source": "user_preference",
            "priority": 3,  # HARD
        },
        {
            "id": CONSTRAINT_PROTECT_FOCUS,
            "constraint_type": "commitment",
            "field": "proposed_action",
            "operator": "eq",
            "value": json.dumps("reschedule_focus"),
            "description": "Protecting your focus blocks — you set this as a priority",
            "source": "user_preference",
            "priority": 2,  # MEDIUM
        },
        {
            "id": CONSTRAINT_DRIFT_SAFETY,
            "constraint_type": "drift_threshold",
            "field": "drift_percentage",
            "operator": "gte",
            "value": json.dumps(40),
            "description": "Safety gate — block proactive suggestions when drift exceeds 40%",
            "source": "system",
            "priority": 1,  # SOFT
        },
    ]

    for c in constraints:
        await dbexec(
            """INSERT INTO governance_constraints
               (id, person_id, constraint_type, field, operator, value,
                description, source, priority, active, metadata, created_at)
               VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, true, '{}', now())
            """,
            c["id"], person_id, c["constraint_type"], c["field"],
            c["operator"], c["value"], c["description"], c["source"],
            c["priority"],
        )

    # 3. Seed base events for contradiction detection
    now = datetime.now(UTC)

    # Event 1: "suggest_exercise" rejected yesterday (enables Scenario 4)
    await dbexec(
        """INSERT INTO governance_events
           (id, ts, person_id, event_type, action, actor, data, reason)
           VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        """,
        EVENT_REJECTED_WALK,
        now - timedelta(hours=18),
        person_id,
        "rejected",
        "suggest_exercise",
        "user",
        json.dumps({"proposed_action": "suggest_exercise", "scenario": "simulation"}),
        "User said: too busy for a walk right now",
    )

    # Event 2: "email_reply" committed 3 weeks ago (enables Scenario 2)
    await dbexec(
        """INSERT INTO governance_events
           (id, ts, person_id, event_type, action, actor, data, reason)
           VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        """,
        EVENT_COMMITTED_MOVING,
        now - timedelta(weeks=3),
        person_id,
        "committed",
        "email_reply",
        "user",
        json.dumps({"context": "considering moving closer to work", "scenario": "simulation"}),
        "User expressed intent to move closer to work",
    )

    LOGGER.info("[demo] Governance data seeded: 3 constraints, 2 events")

    return {
        "constraints_seeded": 3,
        "events_seeded": 2,
        "person_id": person_id,
    }


async def reset_simulation_data(person_id: Optional[str] = None) -> Dict[str, Any]:
    """Clear all simulation events and re-seed."""
    person_id = person_id or DEMO_USER_ID

    # Delete all simulation-tagged events (both sim-prefixed and profile-tagged)
    await dbexec(
        "DELETE FROM governance_events WHERE person_id = $1 AND (id LIKE 'sim-%' OR data::text LIKE '%simulation%')",
        person_id,
    )

    # Re-seed
    result = await seed_governance_demo_data(person_id)
    result["reset"] = True
    return result


async def get_simulation_ledger(
    person_id: Optional[str] = None, limit: int = 50,
) -> list[Dict[str, Any]]:
    """Get governance event ledger for simulation display."""
    person_id = person_id or DEMO_USER_ID

    rows = await dbquery(
        """SELECT id, ts, person_id, event_type, action, actor, data, reason
           FROM governance_events
           WHERE person_id = $1
           ORDER BY ts ASC
           LIMIT $2
        """,
        person_id, limit,
    )

    events = []
    for row in rows or []:
        data_raw = row.get("data") or "{}"
        data = json.loads(data_raw) if isinstance(data_raw, str) else data_raw
        events.append({
            "id": row["id"],
            "timestamp": row["ts"].isoformat() if row.get("ts") else None,
            "person_id": str(row["person_id"]),
            "event_type": row["event_type"],
            "action": row["action"],
            "actor": row.get("actor", "system"),
            "data": data,
            "reason": row.get("reason", ""),
        })

    return events


async def get_simulation_state(
    person_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Get personal model state for simulation display."""
    person_id = person_id or DEMO_USER_ID

    # Get operating system from personal_model
    pm_row = await dbquery(
        "SELECT operating_system FROM personal_model WHERE person_id = $1",
        person_id,
        one=True,
    )

    os_data = {}
    if pm_row:
        os_raw = pm_row.get("operating_system") or "{}"
        os_data = json.loads(os_raw) if isinstance(os_raw, str) else os_raw

    # Count active constraints
    constraint_row = await dbquery(
        "SELECT COUNT(*) as count FROM governance_constraints WHERE person_id = $1 AND active = true",
        person_id,
        one=True,
    )
    constraint_count = constraint_row["count"] if constraint_row else 0

    # Get active constraints list
    constraint_rows = await dbquery(
        """SELECT id, constraint_type, field, operator, value, description, priority
           FROM governance_constraints
           WHERE person_id = $1 AND active = true
           ORDER BY priority DESC
        """,
        person_id,
    )

    constraints = []
    for row in constraint_rows or []:
        val_raw = row.get("value") or "null"
        val = json.loads(val_raw) if isinstance(val_raw, str) else val_raw
        constraints.append({
            "id": row["id"],
            "type": row["constraint_type"],
            "field": row["field"],
            "operator": row["operator"],
            "value": val,
            "description": row.get("description", ""),
            "priority": row.get("priority", 1),
        })

    return {
        "operating_system": os_data,
        "constraint_count": constraint_count,
        "constraints": constraints,
        "person_id": person_id,
    }
