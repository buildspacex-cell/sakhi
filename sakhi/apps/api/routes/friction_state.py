"""
Friction State API — Ayurvedic Intelligence Endpoints

Provides access to:
- Operating System (Prakruti / Constitutional Type)
- Current State (Vikriti)
- Drift percentage from baseline
- Friction State classification (Chaos, Intensity, Stagnation, Balanced)
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any, Dict, Optional

from sakhi.apps.api.services.ayurveda.prakruti import (
    compute_prakruti_from_onboarding,
    get_prakruti,
    infer_prakruti_from_history,
)
from sakhi.apps.api.services.ayurveda.vikriti import (
    compute_current_vikriti,
    compute_baseline_drift,
    classify_friction_state,
    get_full_friction_state,
)

router = APIRouter(prefix="/v1/state", tags=["friction-state"])


class OnboardingQuizRequest(BaseModel):
    """Request model for onboarding quiz responses."""
    person_id: str
    responses: Dict[str, str]


class FrictionStateResponse(BaseModel):
    """Response model for friction state."""
    status: str
    operating_system: Optional[str] = None
    current_state: Optional[Dict[str, Any]] = None
    drift_percentage: Optional[float] = None
    friction_state: Optional[str] = None
    friction_name: Optional[str] = None
    description: Optional[str] = None
    severity: Optional[str] = None
    recommendations_focus: Optional[list] = None
    data: Optional[Dict[str, Any]] = None


@router.get("/friction/{person_id}")
async def get_friction_state(person_id: str) -> FrictionStateResponse:
    """
    Get the complete friction state for a person.

    Returns:
    - operating_system: Their constitutional type (e.g., "Adaptive-Performance")
    - current_state: Current Vikriti (dosha balance)
    - drift_percentage: How far from baseline (0-100%)
    - friction_state: "chaos" | "intensity" | "stagnation" | "balanced"
    - friction_name: User-facing name (e.g., "Chaos Friction")
    - description: Explanation of current state
    - severity: "minimal" | "mild" | "moderate" | "significant"
    """
    try:
        full_state = await get_full_friction_state(person_id)

        friction = full_state.get("friction", {})
        drift = full_state.get("drift", {})
        vikriti = full_state.get("current_state", {})

        return FrictionStateResponse(
            status="ok",
            operating_system=full_state.get("operating_system"),
            current_state=vikriti.get("current_dosha"),
            drift_percentage=drift.get("drift_percentage"),
            friction_state=friction.get("state"),
            friction_name=friction.get("name"),
            description=friction.get("description"),
            severity=friction.get("severity"),
            recommendations_focus=friction.get("recommendations_focus"),
            data=full_state,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to compute friction state: {str(exc)}",
        )


@router.get("/operating-system/{person_id}")
async def get_operating_system(person_id: str) -> Dict[str, Any]:
    """
    Get the person's constitutional type (Prakruti).

    If not yet computed from onboarding, attempts to infer from history.
    """
    try:
        prakruti = await get_prakruti(person_id)

        if not prakruti:
            # Try to infer from history
            prakruti = await infer_prakruti_from_history(person_id)

        if not prakruti:
            return {
                "status": "pending",
                "message": "Constitutional type not yet determined. Complete onboarding quiz or continue journaling.",
                "data": None,
            }

        return {
            "status": "ok",
            "type": prakruti.get("type"),
            "primary_dosha": prakruti.get("primary"),
            "dosha_baseline": prakruti.get("dosha_baseline"),
            "source": prakruti.get("source"),
            "data": prakruti,
        }
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve operating system: {str(exc)}",
        )


@router.post("/operating-system/compute")
async def compute_operating_system(request: OnboardingQuizRequest) -> Dict[str, Any]:
    """
    Compute and store constitutional type from onboarding quiz.

    Expected quiz response keys:
    - body_type: "light_thin" | "medium_muscular" | "solid_heavy"
    - energy_pattern: "variable_bursts" | "focused_sustained" | "steady_slow"
    - stress_response: "anxious_scattered" | "irritable_intense" | "withdrawn_sluggish"
    - sleep_pattern: "light_variable" | "moderate_efficient" | "deep_heavy"
    - work_style: "creative_multitask" | "goal_driven" | "methodical_consistent"
    """
    try:
        prakruti = await compute_prakruti_from_onboarding(
            person_id=request.person_id,
            responses=request.responses,
            store=True,
        )

        return {
            "status": "ok",
            "type": prakruti.get("type"),
            "primary_dosha": prakruti.get("primary"),
            "dosha_baseline": prakruti.get("dosha_baseline"),
            "message": f"Your constitutional type is {prakruti.get('type')}",
            "data": prakruti,
        }
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to compute operating system: {str(exc)}",
        )


@router.get("/vikriti/{person_id}")
async def get_vikriti(person_id: str, window_days: int = 7) -> Dict[str, Any]:
    """
    Get the current state (Vikriti) for a person.

    Args:
        person_id: The person's ID
        window_days: Number of days to look back (default 7)
    """
    try:
        vikriti = await compute_current_vikriti(person_id, window_days)

        return {
            "status": "ok",
            "current_dosha": vikriti.get("current_dosha"),
            "confidence": vikriti.get("confidence"),
            "episode_count": vikriti.get("episode_count"),
            "computed_from": vikriti.get("computed_from"),
            "data": vikriti,
        }
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to compute current state: {str(exc)}",
        )


@router.get("/drift/{person_id}")
async def get_drift(person_id: str) -> Dict[str, Any]:
    """
    Get the drift between baseline and current state.
    """
    try:
        prakruti = await get_prakruti(person_id)
        if not prakruti:
            prakruti = {
                "dosha_baseline": {"vata": 0.33, "pitta": 0.33, "kapha": 0.34}
            }

        vikriti = await compute_current_vikriti(person_id)
        drift = compute_baseline_drift(prakruti, vikriti)

        return {
            "status": "ok",
            "drift_percentage": drift.get("drift_percentage"),
            "primary_contributor": drift.get("primary_contributor"),
            "direction": drift.get("direction"),
            "severity": drift.get("severity"),
            "raw_distances": drift.get("raw_distances"),
            "data": drift,
        }
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to compute drift: {str(exc)}",
        )


__all__ = ["router"]
