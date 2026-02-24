"""
Governance Demo Seeder
----------------------
Seeds governance constraints, objectives, and events for the simulation demo.

Provides:
- 4 constraints (3 universal + 1 overcommitment)
- 2 objective versions (stop-overcommitting v1 & v2)
- 5 events for contradiction detection & overcommitment history
- Idempotent: deletes and re-inserts on each call

Constraint semantics:
    The evaluator checks: `if NOT check(op, actual, expected) → violation`.
    Constraints define REQUIREMENTS (what must be true). Use `lt` to mean
    "must be below X" (fires when above), `neq` to mean "must not equal X"
    (fires when equal).
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime, timedelta
from typing import Any, Dict, Optional
from uuid import uuid4

from sakhi.apps.api.core.db import exec as dbexec, q as dbquery

# Real demo user UUID — governance tables require UUID for person_id
# (user_seeder.DEMO_USER_ID is "demo-user-sakhi-001" which is not a UUID)
DEMO_USER_ID = "6b5b2fbc-9efb-4ba4-be0a-9ec527e23f90"

LOGGER = logging.getLogger(__name__)

# Constraint IDs (stable for idempotent seeding)
CONSTRAINT_NO_WORK_AFTER_10PM = "sim-c-no-work-after-10pm"
CONSTRAINT_PROTECT_FOCUS = "sim-c-protect-focus-time"
CONSTRAINT_DRIFT_SAFETY = "sim-c-drift-safety"
CONSTRAINT_STOP_OVERCOMMITTING = "sim-c-stop-overcommitting"

# Event IDs (stable for idempotent seeding)
EVENT_REJECTED_WALK = "sim-evt-rejected-walk"
EVENT_COMMITTED_MOVING = "sim-evt-committed-moving"
EVENT_OVERCOMMITTED_7D = "sim-evt-overcommitted-7d"
EVENT_OVERCOMMITTED_5D = "sim-evt-overcommitted-5d"
EVENT_OVERCOMMITTED_3D = "sim-evt-overcommitted-3d"


async def seed_governance_demo_data(person_id: Optional[str] = None) -> Dict[str, Any]:
    """Seed governance constraints, objectives, and events for the simulation demo.

    Constraints (universal — same for all profiles):
        1. no_work_after_10pm | HARD(3) | proposed_hour must be < 22
        2. protect_focus_time | MEDIUM(2) | proposed_action must not be reschedule_focus
        3. drift_safety | SOFT(1) | drift_percentage must be < 40
        4. stop_overcommitting | MEDIUM(2) | proposed_action must not be accept_commitment

    Objectives:
        1. stop-overcommitting v1 (2 weeks ago) — initial recognition
        2. stop-overcommitting v2 (3 days ago) — strengthened after pattern

    Events (for contradiction detection + overcommitment history):
        1. "suggest_exercise" → "rejected" | yesterday
        2. "email_reply" → "committed" | 3 weeks ago
        3-5. "accept_commitment" → "committed" | 7d, 5d, 3d ago (rising drift)

    The 3-profile differentiation comes from the frontend sending
    different action_context per profile, NOT from different DB rows.
    """
    person_id = person_id or DEMO_USER_ID
    LOGGER.info("[demo] Seeding governance data for person_id=%s", person_id)

    # 1. Clear existing simulation-specific data (idempotent)
    #    Delete by ID prefix globally — event IDs are fixed constants, so a
    #    previous persona run may have left rows under a different person_id.
    await dbexec(
        "DELETE FROM governance_constraints WHERE id LIKE 'sim-%'",
    )
    await dbexec(
        "DELETE FROM governance_events WHERE id LIKE 'sim-%'",
    )
    await dbexec(
        "DELETE FROM governance_objectives WHERE objective_id LIKE 'sim-%'",
    )

    # 2. Seed constraints
    #    Semantics: check(op, actual, expected) must return True for constraint to PASS.
    #    Violation fires when check returns False.
    #    - lt 22 → "hour must be < 22" → fires when hour >= 22
    #    - neq "X" → "action must not be X" → fires when action IS X
    #    - lt 40 → "drift must be < 40" → fires when drift >= 40
    constraints = [
        {
            "id": CONSTRAINT_NO_WORK_AFTER_10PM,
            "constraint_type": "time_boundary",
            "field": "proposed_hour",
            "operator": "lt",
            "value": json.dumps(22),
            "description": "No work-related suggestions after 10 PM — respecting your sleep boundary",
            "source": "user_preference",
            "priority": 3,  # HARD
        },
        {
            "id": CONSTRAINT_PROTECT_FOCUS,
            "constraint_type": "commitment",
            "field": "proposed_action",
            "operator": "neq",
            "value": json.dumps("reschedule_focus"),
            "description": "Protecting your focus blocks — you set this as a priority",
            "source": "user_preference",
            "priority": 2,  # MEDIUM
        },
        {
            "id": CONSTRAINT_DRIFT_SAFETY,
            "constraint_type": "drift_threshold",
            "field": "drift_percentage",
            "operator": "lt",
            "value": json.dumps(40),
            "description": "Safety gate — block proactive suggestions when drift exceeds 40%",
            "source": "system",
            "priority": 1,  # SOFT
        },
        {
            "id": CONSTRAINT_STOP_OVERCOMMITTING,
            "constraint_type": "value_alignment",
            "field": "proposed_action",
            "operator": "neq",
            "value": json.dumps("accept_commitment"),
            "description": "Stop overcommitting — you set a goal to reduce new obligations",
            "source": "objective:sim-stop-overcommitting:v2",
            "priority": 2,  # MEDIUM
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

    # 3. Seed objectives (stop-overcommitting v1 and v2)
    now = datetime.now(UTC)

    # v1: initial recognition (2 weeks ago)
    await dbexec(
        """INSERT INTO governance_objectives
           (objective_id, version, person_id, ts, title, description, data, source, reason)
           VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
        """,
        "sim-stop-overcommitting", 1, person_id,
        now - timedelta(weeks=2),
        "Stop overcommitting",
        "Recognized pattern: saying yes to everything, then burning out",
        json.dumps({"trigger": "evening_commitments", "pattern": "overcommitment"}),
        "crystallization",
        "Sakhi detected overcommitment pattern across 4 episodes",
    )

    # v2: strengthened (3 days ago)
    await dbexec(
        """INSERT INTO governance_objectives
           (objective_id, version, person_id, ts, title, description, data, source, reason, parent_version)
           VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
        """,
        "sim-stop-overcommitting", 2, person_id,
        now - timedelta(days=3),
        "Stop overcommitting v2",
        "Strengthened: 3 overcommitments in 7 days. Evening commitments are the trigger.",
        json.dumps({"trigger": "evening_commitments", "max_new_per_week": 2, "drift_trend": "+6%"}),
        "feedback",
        "User acknowledged: 'I keep doing this' — upgraded from awareness to active guard",
        1,
    )

    # 4. Seed events for contradiction detection + overcommitment history

    # Event 1: "suggest_exercise" rejected yesterday (existing)
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

    # Event 2: "email_reply" committed 3 weeks ago (existing)
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

    # Events 3-5: Overcommitment history (rising drift over 7 days)
    await dbexec(
        """INSERT INTO governance_events
           (id, ts, person_id, event_type, action, actor, data, reason)
           VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        """,
        EVENT_OVERCOMMITTED_7D,
        now - timedelta(days=7),
        person_id,
        "committed",
        "accept_commitment",
        "user",
        json.dumps({"context": "agreed to weekend workshop", "drift_at_time": 6, "scenario": "simulation"}),
        "User took on new commitment — weekend workshop",
    )

    await dbexec(
        """INSERT INTO governance_events
           (id, ts, person_id, event_type, action, actor, data, reason)
           VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        """,
        EVENT_OVERCOMMITTED_5D,
        now - timedelta(days=5),
        person_id,
        "committed",
        "accept_commitment",
        "user",
        json.dumps({"context": "volunteered for community event", "drift_at_time": 9, "scenario": "simulation"}),
        "User took on new commitment — community event",
    )

    await dbexec(
        """INSERT INTO governance_events
           (id, ts, person_id, event_type, action, actor, data, reason)
           VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        """,
        EVENT_OVERCOMMITTED_3D,
        now - timedelta(days=3),
        person_id,
        "committed",
        "accept_commitment",
        "user",
        json.dumps({"context": "agreed to help neighbor move", "drift_at_time": 12, "scenario": "simulation"}),
        "User took on new commitment — helping neighbor",
    )

    LOGGER.info("[demo] Governance data seeded: 4 constraints, 2 objectives, 5 events")

    return {
        "constraints_seeded": 4,
        "objectives_seeded": 2,
        "events_seeded": 5,
        "person_id": person_id,
    }


async def reset_simulation_data(person_id: Optional[str] = None) -> Dict[str, Any]:
    """Clear all simulation events, objectives, and re-seed."""
    person_id = person_id or DEMO_USER_ID

    # Delete all simulation-tagged events (both sim-prefixed and profile-tagged)
    await dbexec(
        "DELETE FROM governance_events WHERE person_id = $1 AND (id LIKE 'sim-%' OR data::text LIKE '%simulation%')",
        person_id,
    )

    # Delete simulation objectives
    await dbexec(
        "DELETE FROM governance_objectives WHERE person_id = $1 AND objective_id LIKE 'sim-%'",
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


async def get_simulation_intelligence(
    person_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Return real governance intelligence data for the demo UI.

    Queries objectives, commitment events, and constraints from the DB.
    Returns both raw data and pre-formatted intelligence items that the
    frontend can display directly in the "What Sakhi knows" panel.
    """
    person_id = person_id or DEMO_USER_ID
    now = datetime.now(UTC)

    # 1. Objectives (version lineage)
    obj_rows = await dbquery(
        """SELECT objective_id, version, title, description, source, reason,
                  ts, parent_version
           FROM governance_objectives
           WHERE person_id = $1 AND objective_id LIKE 'sim-%'
           ORDER BY version DESC
        """,
        person_id,
    )
    objectives = []
    for row in obj_rows or []:
        objectives.append({
            "objective_id": row["objective_id"],
            "version": row["version"],
            "title": row["title"],
            "description": row.get("description", ""),
            "source": row.get("source", ""),
            "reason": row.get("reason", ""),
            "created_at": row["ts"].isoformat() if row.get("ts") else None,
            "parent_version": row.get("parent_version"),
        })

    # 2. Recent commitment events (overcommitment history)
    evt_rows = await dbquery(
        """SELECT id, ts, action, data, reason
           FROM governance_events
           WHERE person_id = $1
             AND action = 'accept_commitment'
             AND id LIKE 'sim-%'
           ORDER BY ts ASC
        """,
        person_id,
    )
    commitment_events = []
    for row in evt_rows or []:
        data_raw = row.get("data") or "{}"
        data = json.loads(data_raw) if isinstance(data_raw, str) else data_raw
        ts = row["ts"]
        days_ago = (now - ts).days if ts else None
        commitment_events.append({
            "id": row["id"],
            "action": row["action"],
            "context": data.get("context", ""),
            "drift_at_time": data.get("drift_at_time"),
            "days_ago": days_ago,
            "timestamp": ts.isoformat() if ts else None,
        })

    # 3. Drift trend from commitment events
    drift_values = [
        e["drift_at_time"] for e in commitment_events
        if e.get("drift_at_time") is not None
    ]
    drift_trend = None
    if len(drift_values) >= 2:
        delta = drift_values[-1] - drift_values[0]
        first_days = commitment_events[0].get("days_ago") or 0
        last_days = commitment_events[-1].get("days_ago") or 0
        span = abs(first_days - last_days) or 1
        drift_trend = {
            "values": drift_values,
            "delta": delta,
            "days": span,
            "direction": "rising" if delta > 0 else "falling" if delta < 0 else "stable",
        }

    # 4. Active constraints
    c_rows = await dbquery(
        """SELECT id, description, priority, source
           FROM governance_constraints
           WHERE person_id = $1 AND active = true AND id LIKE 'sim-%'
           ORDER BY priority DESC
        """,
        person_id,
    )
    constraints = []
    for row in c_rows or []:
        constraints.append({
            "id": row["id"],
            "description": row.get("description", ""),
            "priority": row.get("priority", 1),
            "source": row.get("source", ""),
        })

    # 5. Pre-formatted intelligence items
    intelligence_items: list[Dict[str, str]] = []

    # Objective — latest version
    if objectives:
        latest = objectives[0]  # sorted DESC by version
        ts_str = ""
        if latest.get("created_at"):
            created = datetime.fromisoformat(latest["created_at"])
            age_days = (now - created).days
            ts_str = (
                f" ({age_days} day{'s' if age_days != 1 else ''} ago)"
                if age_days > 0
                else " (today)"
            )
        intelligence_items.append({
            "label": "Objective",
            "value": f"\"{latest['title']}\" — v{latest['version']}{ts_str}",
            "source": "crystallized",
        })

    # Pattern — commitment count
    if commitment_events:
        first_ago = commitment_events[0].get("days_ago") or 0
        last_ago = commitment_events[-1].get("days_ago") or 0
        span_days = abs(first_ago - last_ago) or 1
        count = len(commitment_events)
        intelligence_items.append({
            "label": "Pattern",
            "value": f"{count} new commitment{'s' if count != 1 else ''} in {span_days} days",
            "source": "ledger",
        })

    # Drift trend
    if drift_trend and drift_trend["delta"] != 0:
        sign = "+" if drift_trend["delta"] > 0 else ""
        arrow = "\u2191" if drift_trend["delta"] > 0 else "\u2193"
        intelligence_items.append({
            "label": "Drift trend",
            "value": f"{arrow} {sign}{drift_trend['delta']}% over {drift_trend['days']} days",
            "source": "temporal",
        })

    # Acknowledgment (from objective v2 reason)
    v2_objs = [o for o in objectives if o.get("parent_version") is not None]
    if v2_objs:
        v2 = v2_objs[0]
        ts_str = ""
        if v2.get("created_at"):
            created = datetime.fromisoformat(v2["created_at"])
            age_days = (now - created).days
            ts_str = f" — {age_days} day{'s' if age_days != 1 else ''} ago"
        intelligence_items.append({
            "label": "Acknowledgment",
            "value": f"\"I keep doing this\"{ts_str}",
            "source": "episodic",
        })

    return {
        "objectives": objectives,
        "commitment_events": commitment_events,
        "drift_trend": drift_trend,
        "constraints": constraints,
        "intelligence_items": intelligence_items,
        "person_id": person_id,
    }


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
