"""
Demo Routes
-----------
API endpoints for running demos and seeding demo data.

These routes enable:
- Seeding demo data for real working demos
- Running vision loop demos
- Running coordination demos
- Running reflection demos
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Literal, Optional

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

LOGGER = logging.getLogger(__name__)

router = APIRouter(prefix="/demo", tags=["demo"])


# =============================================================================
# Request/Response Models
# =============================================================================

class SeedResponse(BaseModel):
    """Response from seeding operations."""
    status: str
    message: str
    data: Optional[Dict[str, Any]] = None


class DemoRunResponse(BaseModel):
    """Response from running a demo."""
    status: str
    demo_type: str
    steps: Optional[list] = None
    events: Optional[list] = None
    result: Optional[Dict[str, Any]] = None


class SimulationEvalRequest(BaseModel):
    """Request to evaluate a simulation scenario through Kala GovernanceGate."""
    person_id: Optional[str] = None
    scenario_id: str
    profile: str = "adaptive"  # adaptive | performance | conservation
    action_context: Dict[str, Any]


class SimulationAddJournalRequest(BaseModel):
    """Request to append a journal entry to a simulation profile."""
    persona_id: str
    content: str
    time_of_day: Literal["morning", "afternoon", "evening"] = "evening"


class SimulationContinuityEntry(BaseModel):
    """Selected simulation entry to include in a continuity arc."""

    day: int
    timestamp: str
    content: str
    time_of_day: Optional[str] = None
    scalar: Optional[float] = None
    facet: Optional[str] = None
    decision_state: Optional[str] = None
    stance: Optional[str] = None


class SimulationContinuityRequest(BaseModel):
    """Request to compute a continuity arc over selected simulation entries."""

    persona_id: str
    anchor: str
    entries: list[SimulationContinuityEntry]
    max_gap_days: int = 21
    min_len: int = 3


# =============================================================================
# Seeding Endpoints
# =============================================================================

@router.post("/seed/all", response_model=SeedResponse)
async def seed_all_demo_data():
    """
    Seed ALL demo data for a complete working demo.

    This creates:
    - Demo user with profile
    - Demo mom for mesh coordination
    - Demo restaurant for business mesh
    - Sensory preferences
    - Personal patterns
    - Recent behaviors
    - Past episodes

    Call this once before running any demos.
    """
    try:
        from sakhi.apps.api.services.demo import seed_all_demo_data as do_seed

        result = await do_seed()

        return SeedResponse(
            status="success",
            message="All demo data seeded successfully",
            data=result,
        )
    except Exception as e:
        LOGGER.exception("[demo] Failed to seed data: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/seed/preferences", response_model=SeedResponse)
async def seed_preferences(person_id: Optional[str] = None):
    """Seed sensory preferences for a user."""
    try:
        from sakhi.apps.api.services.demo import seed_demo_preferences, DEMO_USER_ID

        await seed_demo_preferences(person_id or DEMO_USER_ID)

        return SeedResponse(
            status="success",
            message="Preferences seeded",
            data={"person_id": person_id or DEMO_USER_ID},
        )
    except Exception as e:
        LOGGER.exception("[demo] Failed to seed preferences: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/seed/patterns", response_model=SeedResponse)
async def seed_patterns(person_id: Optional[str] = None):
    """Seed patterns and behaviors for causal reasoning."""
    try:
        from sakhi.apps.api.services.demo import seed_all_causal_data, DEMO_USER_ID

        await seed_all_causal_data(person_id or DEMO_USER_ID)

        return SeedResponse(
            status="success",
            message="Patterns and behaviors seeded",
            data={"person_id": person_id or DEMO_USER_ID},
        )
    except Exception as e:
        LOGGER.exception("[demo] Failed to seed patterns: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Vision Demo Endpoints
# =============================================================================

@router.post("/run/vision", response_model=DemoRunResponse)
async def run_vision_demo(
    task: str = Query(default="Find a car perfume on Amazon", description="Task for vision demo"),
    mode: str = Query(default="simulated", description="Demo mode: simulated, recorded, or live"),
    person_id: Optional[str] = Query(default=None, description="Person UUID to run demo for"),
):
    """
    Run a vision loop demonstration.

    Modes:
    - simulated: Uses pre-built responses (fast, reliable for demos)
    - recorded: Uses pre-recorded screenshots
    - live: Uses real desktop agent (requires agent connection)
    """
    try:
        from sakhi.apps.api.services.demo import run_vision_demo, DemoMode, DEMO_USER_ID

        mode_enum = DemoMode(mode)
        steps = await run_vision_demo(
            task=task,
            mode=mode_enum,
            person_id=person_id or DEMO_USER_ID,
        )

        return DemoRunResponse(
            status="success",
            demo_type="vision",
            steps=steps,
        )
    except Exception as e:
        LOGGER.exception("[demo] Vision demo failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Coordination Demo Endpoints
# =============================================================================

@router.post("/run/coordination/personal", response_model=DemoRunResponse)
async def run_coordination_personal():
    """
    Run personal mesh coordination demo.

    Shows Your Sakhi coordinating dinner with Mom's Sakhi.
    """
    try:
        from sakhi.apps.api.services.demo import run_coordination_demo, CoordinationScenario

        events = await run_coordination_demo(
            scenario=CoordinationScenario.PERSONAL_DINNER,
        )

        return DemoRunResponse(
            status="success",
            demo_type="coordination_personal",
            events=events,
        )
    except Exception as e:
        LOGGER.exception("[demo] Personal coordination demo failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/run/coordination/business", response_model=DemoRunResponse)
async def run_coordination_business():
    """
    Run business mesh coordination demo.

    Shows Your Sakhi making a reservation with Restaurant Sakhi.
    """
    try:
        from sakhi.apps.api.services.demo import run_coordination_demo, CoordinationScenario

        events = await run_coordination_demo(
            scenario=CoordinationScenario.BUSINESS_RESERVATION,
        )

        return DemoRunResponse(
            status="success",
            demo_type="coordination_business",
            events=events,
        )
    except Exception as e:
        LOGGER.exception("[demo] Business coordination demo failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Reflection Demo Endpoints
# =============================================================================

@router.post("/run/reflection", response_model=DemoRunResponse)
async def run_reflection_demo(
    symptom: str = Query(default="scattered", description="Symptom to explain"),
    person_id: Optional[str] = None,
):
    """
    Run reflective intelligence demo.

    Shows causal reasoning: "Why am I feeling X?"
    """
    try:
        from sakhi.apps.api.services.demo import DEMO_USER_ID
        from sakhi.apps.api.services.ayurveda.causal_reasoning import explain_symptom

        explanation = await explain_symptom(
            person_id=person_id or DEMO_USER_ID,
            symptom=symptom,
        )

        return DemoRunResponse(
            status="success",
            demo_type="reflection",
            result={
                "symptom": explanation.symptom,
                "dosha_context": explanation.dosha_context,
                "primary_causes": [c.dict() for c in explanation.primary_causes],
                "contributing_factors": [c.dict() for c in explanation.contributing_factors],
                "seasonal_influence": explanation.seasonal_influence,
                "personal_pattern_match": explanation.personal_pattern_match,
                "explanation": explanation.explanation_text,
            },
        )
    except Exception as e:
        LOGGER.exception("[demo] Reflection demo failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/run/last-time", response_model=DemoRunResponse)
async def run_last_time_demo(
    symptom: str = Query(default="anxious", description="Symptom to look up"),
    person_id: Optional[str] = None,
):
    """
    Run "Last Time" lookup demo.

    Shows: "Last time I felt this way, what helped?"
    """
    try:
        from sakhi.apps.api.services.demo import DEMO_USER_ID
        from sakhi.apps.api.services.ayurveda.causal_reasoning import lookup_last_time

        result = await lookup_last_time(
            person_id=person_id or DEMO_USER_ID,
            symptom=symptom,
        )

        return DemoRunResponse(
            status="success",
            demo_type="last_time",
            result={
                "symptom": result.current_symptom,
                "found_episodes": [ep.dict() for ep in result.found_episodes],
                "best_interventions": result.best_interventions,
                "average_resolution_time": result.average_resolution_time,
                "summary": result.summary,
            },
        )
    except Exception as e:
        LOGGER.exception("[demo] Last time lookup failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/last-time/{person_id}")
async def get_last_time(
    person_id: str,
    symptom: str = Query(..., description="Symptom to look up"),
):
    """
    Look up similar past episodes for a real user.

    Returns what helped last time they felt this way.
    """
    try:
        from sakhi.apps.api.services.ayurveda.causal_reasoning import lookup_last_time

        result = await lookup_last_time(
            person_id=person_id,
            symptom=symptom,
        )

        return {
            "symptom": result.current_symptom,
            "episodes": [ep.dict() for ep in result.found_episodes],
            "best_interventions": result.best_interventions,
            "average_resolution_time": result.average_resolution_time,
            "summary": result.summary,
        }
    except Exception as e:
        LOGGER.exception("[demo] Last time lookup failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Full Demo Endpoint
# =============================================================================

@router.post("/run/full", response_model=DemoRunResponse)
async def run_full_demo():
    """
    Run all demos in sequence.

    This runs:
    1. Vision demo (car perfume search)
    2. Personal coordination demo (dinner with Mom)
    3. Business coordination demo (restaurant reservation)
    4. Reflection demo (why am I scattered?)
    """
    try:
        from sakhi.apps.api.services.demo import run_full_demo

        result = await run_full_demo(demo_type="all")

        return DemoRunResponse(
            status="success",
            demo_type="full",
            result=result,
        )
    except Exception as e:
        LOGGER.exception("[demo] Full demo failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Status Endpoint
# =============================================================================

@router.get("/status")
async def demo_status():
    """Check demo data status."""
    try:
        from sakhi.apps.api.core.db import q as dbfetch
        from sakhi.apps.api.services.demo import DEMO_USER_ID

        # Check if demo user exists
        user = await dbfetch(
            "SELECT id FROM persons WHERE id = $1",
            DEMO_USER_ID,
            one=True,
        )

        # Check preferences
        prefs = await dbfetch(
            "SELECT person_id FROM sensory_preferences WHERE person_id = $1",
            DEMO_USER_ID,
            one=True,
        )

        # Check patterns
        patterns = await dbfetch(
            "SELECT COUNT(*) as count FROM personal_patterns WHERE person_id = $1",
            DEMO_USER_ID,
            one=True,
        )

        return {
            "status": "ready" if user else "needs_seeding",
            "demo_user_exists": bool(user),
            "preferences_seeded": bool(prefs),
            "patterns_count": patterns["count"] if patterns else 0,
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "hint": "Run POST /demo/seed/all to initialize demo data",
        }


# =============================================================================
# Governance Simulation Endpoints
# =============================================================================


@router.post("/seed/governance", response_model=SeedResponse)
async def seed_governance(request: Request):
    """Seed governance constraints and events for simulation demo.

    Idempotent: deletes existing sim-* data and re-inserts.
    Seeds 3 constraints + 2 base events for contradiction detection.
    """
    try:
        from sakhi.apps.api.services.demo import (
            seed_governance_demo_data,
        )
        from sakhi.apps.api.services.demo.governance_seeder import DEMO_USER_ID

        body = await request.json() if request else {}
        person_id = body.get("person_id") if isinstance(body, dict) else None
        result = await seed_governance_demo_data(person_id or DEMO_USER_ID)

        return SeedResponse(
            status="success",
            message="Governance demo data seeded",
            data=result,
        )
    except Exception as e:
        LOGGER.exception("[demo] Failed to seed governance data: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/simulation/evaluate")
async def evaluate_simulation_scenario(body: SimulationEvalRequest):
    """Run REAL Kala GovernanceGate evaluation with scenario context.

    Returns the full GateDecision from Kala's evaluate_turn().
    Logs proposed + decision events to the governance_events ledger.
    """
    try:
        from sakhi.apps.api.services.demo import DEMO_USER_ID
        from sakhi.apps.api.services.governance.service import (
            evaluate_turn,
            log_turn_event,
            map_decision_to_event_type,
        )

        person_id = body.person_id or DEMO_USER_ID

        # Ensure entity_id is in the action context
        action_context = {**body.action_context, "entity_id": person_id}

        # Log PROPOSED event
        event_id = f"sim-{body.profile}-{body.scenario_id}-{_short_id()}"
        await log_turn_event(
            person_id=person_id,
            action=action_context.get("proposed_action", "conversation_turn"),
            event_type="proposed",
            actor="llm",
            data={**action_context, "profile": body.profile, "scenario": body.scenario_id},
            reason=f"Simulation scenario: {body.scenario_id} (profile: {body.profile})",
        )

        # Run REAL Kala GovernanceGate evaluation
        drift_data = None
        drift_pct = action_context.get("drift_percentage")
        if drift_pct is not None:
            drift_data = {
                "drift_percentage": drift_pct,
                "severity": action_context.get("friction_state", "balanced"),
            }

        decision = await evaluate_turn(
            person_id=person_id,
            action_context=action_context,
            drift_data=drift_data,
        )

        # Log DECISION event
        gov_action = decision.get("action", "allow")
        await log_turn_event(
            person_id=person_id,
            action=action_context.get("proposed_action", "conversation_turn"),
            event_type=map_decision_to_event_type(gov_action),
            actor="governance",
            data={
                **action_context,
                "profile": body.profile,
                "scenario": body.scenario_id,
                "gate_decision": gov_action,
            },
            reason="; ".join(decision.get("reasons", [])) or f"Governance: {gov_action}",
        )

        return {
            "status": "success",
            "scenario_id": body.scenario_id,
            "profile": body.profile,
            **decision,
        }
    except Exception as e:
        LOGGER.exception("[demo] Simulation evaluate failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/simulation/ledger/{person_id}")
async def get_simulation_ledger_endpoint(person_id: str, limit: int = Query(default=50)):
    """Get governance event ledger for demo user."""
    try:
        from sakhi.apps.api.services.demo import get_simulation_ledger

        events = await get_simulation_ledger(person_id, limit)
        return {"status": "success", "events": events, "count": len(events)}
    except Exception as e:
        LOGGER.exception("[demo] Ledger fetch failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/simulation/state/{person_id}")
async def get_simulation_state_endpoint(person_id: str):
    """Get personal model state (OS, drift, constraints) for simulation."""
    try:
        from sakhi.apps.api.services.demo import get_simulation_state

        state = await get_simulation_state(person_id)
        return {"status": "success", **state}
    except Exception as e:
        LOGGER.exception("[demo] State fetch failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/simulation/reset/{person_id}")
async def reset_simulation_endpoint(person_id: str):
    """Clear simulation events and re-seed for a fresh demo."""
    try:
        from sakhi.apps.api.services.demo import reset_simulation_data

        result = await reset_simulation_data(person_id)
        return {"status": "success", **result}
    except Exception as e:
        LOGGER.exception("[demo] Simulation reset failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/simulation/intelligence/{person_id}")
async def get_simulation_intelligence_endpoint(person_id: str):
    """Get real governance intelligence data (objectives, events, drift trend).

    Returns pre-formatted intelligence items for the "What Sakhi knows" panel,
    plus raw objectives, commitment events, and constraints for detailed display.
    """
    try:
        from sakhi.apps.api.services.demo import get_simulation_intelligence

        data = await get_simulation_intelligence(person_id)
        return {"status": "success", **data}
    except Exception as e:
        LOGGER.exception("[demo] Intelligence fetch failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/simulation/add-journal")
async def add_simulation_journal(body: SimulationAddJournalRequest, request: Request):
    """Append a journal to a simulation profile and process it through /v2/turn + daily workers."""
    try:
        from sakhi.apps.api.services.demo.simulation_profile_updater import (
            add_journal_to_simulation_profile,
        )

        result = await add_journal_to_simulation_profile(
            app=request.app,
            persona_id=body.persona_id,
            content=body.content,
            time_of_day=body.time_of_day,
        )
        return {"status": "success", **result}
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        LOGGER.exception("[demo] Simulation add-journal failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/simulation/continuity")
async def build_simulation_continuity(body: SimulationContinuityRequest):
    """Build a continuity arc over selected simulation entries."""
    try:
        from sakhi.apps.api.services.demo.simulation_continuity import (
            build_simulation_continuity_arc,
        )

        result = build_simulation_continuity_arc(
            persona_id=body.persona_id,
            anchor=body.anchor,
            entries=[entry.model_dump() for entry in body.entries],
            max_gap_days=body.max_gap_days,
            min_len=body.min_len,
        )
        return {"status": "success", **result}
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        LOGGER.exception("[demo] Simulation continuity failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


def _short_id() -> str:
    """Generate a short unique ID for simulation events."""
    from uuid import uuid4
    return uuid4().hex[:8]
