"""Governance service — hydrate kala types from DB and evaluate turns.

This module is the bridge between kala (pure computation) and Sakhi (I/O + persistence).
It loads constraints, objectives, and events from PostgreSQL, feeds them to kala's
GovernanceGate, and returns serializable results for the conversation pipeline.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from kala.constraints.core import Constraint, ConstraintSet
from kala.governance.gate import GovernanceGate
from kala.ledger.core import Event, Ledger
from kala.objectives.core import ObjectiveStore, ObjectiveVersion
from sakhi.libs.kala_adapters.ledger_backend import SakhiLedgerBackend

LOGGER = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Action classification (simple keyword router)
# ---------------------------------------------------------------------------

_ACTION_PATTERNS: dict[str, list[str]] = {
    "suggest_exercise": ["workout", "exercise", "run", "gym", "yoga", "stretch"],
    "suggest_meditation": ["meditat", "mindful", "breath work", "calm down", "grounding"],
    "suggest_productivity": ["productive", "plan my", "schedule", "organize", "prioritize", "to-do"],
    "suggest_diet": ["eat", "food", "meal", "diet", "nutrition", "cook"],
    "suggest_sleep": ["sleep", "rest", "wind down", "bedtime", "nap"],
    "suggest_social": ["call someone", "connect with", "friend", "relationship"],
}


def classify_action_type(user_text: str, friction_state: str = "balanced") -> str:
    """Derive a semantic action label from user text.

    Falls back to ``'proactive_suggestion'`` when friction is high and text is
    open-ended, or ``'conversation_turn'`` otherwise.
    """
    text_lower = (user_text or "").lower()
    for action_type, keywords in _ACTION_PATTERNS.items():
        if any(kw in text_lower for kw in keywords):
            return action_type
    if friction_state in ("chaos", "intensity", "stagnation"):
        return "proactive_suggestion"
    return "conversation_turn"


# ---------------------------------------------------------------------------
# Governance evaluation
# ---------------------------------------------------------------------------


async def evaluate_turn(
    person_id: str,
    action_context: dict[str, Any],
    drift_data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Run kala's GovernanceGate for a single conversation turn.

    Returns a serializable dict with the gate decision, violations,
    and contradiction info.
    """
    constraints = await _load_constraints(person_id)
    objectives = await _load_objectives(person_id)

    # Pre-load recent events into an in-memory ledger for contradiction detection.
    # We use InMemoryBackend because GovernanceGate calls ledger.query() synchronously,
    # but SakhiLedgerBackend.query/append are async and would return unawaited coroutines.
    backend = SakhiLedgerBackend()
    recent = await backend.query(
        entity_id=person_id,
        after=datetime.now(UTC) - timedelta(days=14),
        limit=50,
    )
    ledger = Ledger()  # uses InMemoryBackend by default
    for evt in reversed(recent):  # oldest first
        ledger.append(evt)

    gate = GovernanceGate(
        constraints=constraints,
        ledger=ledger,
        objectives=objectives if objectives else None,
    )

    decision = gate.evaluate(
        action_context=action_context,
        drift_data=drift_data,
    )

    violations_list = []
    for v in (decision.violations or ()):
        violations_list.append({
            "constraint_id": v.constraint.id,
            "field": v.constraint.field,
            "operator": v.constraint.operator,
            "expected": v.constraint.value,
            "description": v.constraint.description,
            "actual": v.actual_value,
            "message": v.message,
        })

    return {
        "action": decision.action,
        "reasons": list(decision.reasons),
        "triggers": list(decision.triggers),
        "is_blocked": decision.is_blocked,
        "is_allowed": decision.is_allowed,
        "requires_confirmation": decision.requires_confirmation,
        "violations": violations_list,
    }


# ---------------------------------------------------------------------------
# Governance guard (decision → prompt directive)
# ---------------------------------------------------------------------------


def build_governance_guard(decision: dict[str, Any]) -> str:
    """Convert a governance decision into a hard LLM prompt directive.

    This is NOT optional context. When present, the prompt builder MUST include it.

    - ``block`` / ``require_reconciliation`` → MANDATORY: "DO NOT suggest X"
    - ``confirm`` / ``require_confirmation`` → ADVISORY: "Ask before suggesting X"
    - ``allow`` → empty string (no modification)
    """
    action = decision.get("action", "allow")
    violations = decision.get("violations", [])

    if action == "allow" and not violations:
        return ""

    if action in ("block", "require_reconciliation"):
        parts = ["GOVERNANCE DIRECTIVE (MANDATORY):"]
        for v in violations:
            parts.append(f"- DO NOT suggest or encourage actions related to: {v['description']}.")
        parts.append(
            "Instead, acknowledge the user's boundary respectfully "
            "and suggest alternatives that work within their constraints."
        )
        if action == "require_reconciliation":
            parts.append(
                "A contradiction with a previous decision or commitment was detected. "
                "Surface this gently and ask the user how they'd like to resolve it."
            )
        return "\n".join(parts)

    if action in ("confirm", "require_confirmation"):
        parts = ["GOVERNANCE ADVISORY:"]
        for v in violations:
            parts.append(
                f"- Before suggesting anything related to: {v['description']}, "
                "explicitly ask the user for confirmation first."
            )
        triggers = decision.get("triggers", [])
        if "drift" in triggers:
            parts.append(
                "- The user's state has drifted significantly from baseline. "
                "Be gentle. Avoid pushing. Ask before suggesting."
            )
        return "\n".join(parts)

    return ""


# ---------------------------------------------------------------------------
# Post-check enforcement
# ---------------------------------------------------------------------------


def enforce_block(reply: str, decision: dict[str, Any]) -> str:
    """If governance blocked but LLM still violated, replace with safe template.

    Simple heuristic keyword scan — not NLP. Sufficient for demo.
    Returns the original reply if clean, or a safe template if violation detected.
    """
    if decision.get("action") != "block":
        return reply

    blocked_keywords: list[str] = []
    for v in decision.get("violations", []):
        desc_lower = (v.get("description", "") or "").lower()
        for word in desc_lower.split():
            if len(word) > 4 and word not in (
                "avoid", "after", "should", "before", "exceed", "state",
                "drift", "which", "their", "about", "could", "would",
            ):
                blocked_keywords.append(word)

    if not blocked_keywords:
        return reply

    reply_lower = reply.lower()
    violation_detected = any(kw in reply_lower for kw in blocked_keywords)

    if not violation_detected:
        return reply

    return (
        "I'm here with you. Given where you are right now, "
        "I want to be thoughtful about what I suggest. "
        "How are you feeling \u2014 would you like to talk, "
        "or would something calming be more helpful?"
    )


# ---------------------------------------------------------------------------
# Event logging
# ---------------------------------------------------------------------------

_EVENT_TYPE_MAP: dict[str, str] = {
    "allow": "committed",
    "confirm": "validated",
    "require_confirmation": "validated",
    "block": "rejected",
    "require_reconciliation": "reconciled",
}


async def log_turn_event(
    person_id: str,
    action: str,
    event_type: str,
    actor: str = "llm",
    data: dict[str, Any] | None = None,
    reason: str = "",
) -> None:
    """Persist a governance event to the ledger."""
    backend = SakhiLedgerBackend()
    event = Event(
        id=f"gov-{uuid4().hex[:12]}",
        timestamp=datetime.now(UTC),
        entity_id=person_id,
        event_type=event_type,
        action=action,
        actor=actor,
        data=data or {},
        reason=reason,
    )
    try:
        await backend.append(event)
    except Exception:
        LOGGER.warning("Failed to log governance event %s", event.id, exc_info=True)


def map_decision_to_event_type(gov_action: str) -> str:
    """Map a governance action to the appropriate ledger event_type."""
    return _EVENT_TYPE_MAP.get(gov_action, "committed")


# ---------------------------------------------------------------------------
# DB hydration helpers
# ---------------------------------------------------------------------------


async def _load_constraints(person_id: str) -> ConstraintSet:
    """Load active constraints for a person from governance_constraints table."""
    from sakhi.apps.api.core.db import get_db

    db = await get_db()
    try:
        rows = await db.fetch(
            "SELECT * FROM governance_constraints WHERE person_id = $1 AND active = true",
            person_id,
        )
    finally:
        await db.close()

    cs = ConstraintSet()
    for row in rows:
        value_raw = row["value"]
        value = json.loads(value_raw) if isinstance(value_raw, str) else value_raw
        meta_raw = row.get("metadata") or "{}"
        meta = json.loads(meta_raw) if isinstance(meta_raw, str) else meta_raw

        cs.add(Constraint(
            id=row["id"],
            constraint_type=row["constraint_type"],
            field=row["field"],
            operator=row["operator"],
            value=value,
            description=row.get("description", ""),
            source=row.get("source", ""),
            priority=row.get("priority", 2),
            active=True,
            metadata=meta,
        ))
    return cs


async def _load_objectives(person_id: str) -> ObjectiveStore | None:
    """Load objectives for a person from governance_objectives table."""
    from sakhi.apps.api.core.db import get_db

    db = await get_db()
    try:
        rows = await db.fetch(
            "SELECT * FROM governance_objectives WHERE person_id = $1 ORDER BY objective_id, version",
            person_id,
        )
    finally:
        await db.close()

    if not rows:
        return None

    store = ObjectiveStore()
    for row in rows:
        data_raw = row.get("data") or "{}"
        data = json.loads(data_raw) if isinstance(data_raw, str) else data_raw
        ts = row["ts"]
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=UTC)

        store.add(ObjectiveVersion(
            objective_id=row["objective_id"],
            version=row["version"],
            timestamp=ts,
            title=row["title"],
            description=row.get("description", ""),
            data=data,
            source=row.get("source", ""),
            reason=row.get("reason", ""),
            parent_version=row.get("parent_version"),
        ))
    return store
