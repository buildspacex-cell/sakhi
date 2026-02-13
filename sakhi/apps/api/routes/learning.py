"""
Learning Pipeline API Routes
----------------------------
A.7 Learning Pipeline + A.8 Preference Feedback Loop

Endpoints:
- POST /learning/feedback - Log recommendation feedback
- POST /learning/choice - Log user choice
- POST /learning/outcome - Log intervention outcome
- POST /learning/trigger - Trigger learning cycle
- GET  /learning/history - Get learning run history
- GET  /learning/patterns - Get choice patterns
- GET  /learning/adjustments - Get preference adjustments
"""

from __future__ import annotations

from datetime import date, datetime, timezone
import logging
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

router = APIRouter(prefix="/learning", tags=["learning"])
logger = logging.getLogger(__name__)


# =============================================================================
# Request/Response Models
# =============================================================================

class FeedbackRequest(BaseModel):
    """Request to log recommendation feedback."""
    person_id: str
    recommendation_type: str = Field(description="Type: product, food, activity, wellness")
    recommendation_content: Dict[str, Any]
    feedback_type: str = Field(description="thumbs_up, thumbs_down, complaint, praise, follow, dismiss")
    feedback_text: Optional[str] = None
    rating: Optional[float] = Field(default=None, ge=1.0, le=5.0)
    was_followed: bool = False
    was_reordered: bool = False
    recommendation_domain: Optional[str] = None
    conversation_id: Optional[str] = None


class ChoiceRequest(BaseModel):
    """Request to log a user choice."""
    person_id: str
    choice_context: str = Field(description="Context: restaurant, product, activity")
    options_presented: List[Dict[str, Any]]
    chosen_option: Dict[str, Any]
    chosen_index: int
    conversation_id: Optional[str] = None


class OutcomeRequest(BaseModel):
    """Request to log intervention outcome."""
    person_id: str
    intervention_type: str = Field(description="Type: activity, food, rest, social, mindfulness")
    intervention_name: str
    was_effective: bool
    effectiveness_score: float = Field(default=0.5, ge=0.0, le=1.0)
    symptom_addressed: Optional[str] = None
    related_dosha: Optional[str] = None
    notes: Optional[str] = None


class TriggerRequest(BaseModel):
    """Request to trigger learning cycle."""
    person_id: str
    force: bool = False
    lookback_days: int = 14


class SymptomResolutionRequest(BaseModel):
    """Request to update symptom resolution."""
    person_id: str
    symptom_log_id: str
    interventions_tried: List[str]
    what_helped: List[str]
    what_didnt_help: List[str] = Field(default_factory=list)
    resolution_summary: Optional[str] = None


class CompanionCheckInRequest(BaseModel):
    """Request for immediate Ayurvedic companion check-in."""
    person_id: str
    symptom: str = Field(min_length=2, max_length=120)
    energy_level: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    body_cues: List[str] = Field(default_factory=list)
    note: Optional[str] = Field(default=None, max_length=1000)


class CompanionProtocolOption(BaseModel):
    """A short actionable protocol option (2/5/10 minute)."""
    id: str
    title: str
    category: str
    duration_minutes: int
    related_dosha: Optional[str] = None
    expected_effect: str
    safety_note: str
    steps: List[str]


class CompanionFollowUpPlanRequest(BaseModel):
    """Request to convert selected protocol into a tracked follow-up plan."""
    person_id: str
    symptom: str = Field(min_length=2, max_length=120)
    protocol_id: str
    target_days: int = Field(default=7, ge=1, le=30)
    target_per_day: int = Field(default=1, ge=1, le=5)
    checkin_id: Optional[str] = None


class CompanionProtocolCompletionRequest(BaseModel):
    """Request to log completion/outcome of a selected protocol."""
    person_id: str
    symptom: str = Field(min_length=2, max_length=120)
    protocol_id: str
    was_effective: bool = True
    effectiveness_score: float = Field(default=0.7, ge=0.0, le=1.0)
    notes: Optional[str] = None


PROTOCOL_LIBRARY: Dict[str, Dict[int, Dict[str, Any]]] = {
    "vata": {
        2: {
            "id": "vata_grounding_breath_2m",
            "title": "Grounding Breath Reset",
            "category": "breath",
            "expected_effect": "Settles racing thoughts and nervous agitation quickly.",
            "safety_note": "Breathe gently. Stop if you feel dizzy.",
            "steps": [
                "Sit with both feet grounded and one hand on your belly.",
                "Inhale for 4 counts through the nose, exhale for 6 counts.",
                "Repeat for 8 to 10 rounds.",
            ],
        },
        5: {
            "id": "vata_slow_body_scan_5m",
            "title": "Slow Body Scan",
            "category": "mindfulness",
            "expected_effect": "Reduces scattered attention and restores present-moment stability.",
            "safety_note": "If any step feels too intense, keep attention on your breath.",
            "steps": [
                "Close your eyes and scan from forehead to toes.",
                "Name where you feel tension without judging it.",
                "Take 3 long exhales at each tense area.",
            ],
        },
        10: {
            "id": "vata_warm_reset_10m",
            "title": "Warm Nervous System Reset",
            "category": "nourishment",
            "expected_effect": "Creates grounding through warmth, breath, and slower pacing.",
            "safety_note": "Skip any movement that causes pain.",
            "steps": [
                "Sip warm water or herbal tea slowly for 2 to 3 minutes.",
                "Do gentle neck and shoulder rolls for 3 minutes.",
                "Finish with 10 slow breaths and quiet stillness.",
            ],
        },
    },
    "pitta": {
        2: {
            "id": "pitta_cooling_pause_2m",
            "title": "Cooling Pause",
            "category": "breath",
            "expected_effect": "De-escalates intensity and irritability in the moment.",
            "safety_note": "Do not strain the inhale or hold your breath.",
            "steps": [
                "Step away from screen or conversation for 2 minutes.",
                "Inhale through the nose for 4 counts, exhale for 6.",
                "Relax jaw, shoulders, and forehead on each exhale.",
            ],
        },
        5: {
            "id": "pitta_soften_focus_5m",
            "title": "Soften Focus Reset",
            "category": "mindfulness",
            "expected_effect": "Shifts from over-control to steadier, clearer focus.",
            "safety_note": "If frustration rises, slow down and shorten each step.",
            "steps": [
                "Name one pressure you can release right now.",
                "Do 5 rounds of long exhale breathing.",
                "Choose one next action only, not three.",
            ],
        },
        10: {
            "id": "pitta_cool_walk_10m",
            "title": "Cool Walk and Reset",
            "category": "activity",
            "expected_effect": "Moves excess internal heat and mental intensity.",
            "safety_note": "Keep pace easy and avoid direct heat if possible.",
            "steps": [
                "Take a 10 minute easy walk in cooler air if available.",
                "Keep gaze wide instead of fixed.",
                "Return and drink room-temperature water.",
            ],
        },
    },
    "kapha": {
        2: {
            "id": "kapha_activation_breath_2m",
            "title": "Activation Breath",
            "category": "breath",
            "expected_effect": "Quickly lifts heaviness and mental fog.",
            "safety_note": "Keep effort moderate and stop if lightheaded.",
            "steps": [
                "Sit tall and take 20 strong but controlled exhales.",
                "Stand up and shake your arms and legs for 30 seconds.",
                "Take 3 normal breaths and repeat once.",
            ],
        },
        5: {
            "id": "kapha_mobility_boost_5m",
            "title": "Mobility Boost",
            "category": "activity",
            "expected_effect": "Builds momentum when motivation is low.",
            "safety_note": "Use pain-free ranges and scale intensity as needed.",
            "steps": [
                "Do brisk marching in place for 60 seconds.",
                "Add squats or chair-sits for 2 minutes.",
                "Finish with 90 seconds of fast arm swings.",
            ],
        },
        10: {
            "id": "kapha_energy_walk_10m",
            "title": "Energy Walk",
            "category": "activity",
            "expected_effect": "Reduces stagnation and increases alertness.",
            "safety_note": "Choose stable ground and a sustainable pace.",
            "steps": [
                "Walk briskly for 8 to 10 minutes.",
                "Breathe through your nose and keep posture upright.",
                "End with 1 minute of deep breathing.",
            ],
        },
    },
    "fallback": {
        2: {
            "id": "general_breath_reset_2m",
            "title": "2-Minute Breath Reset",
            "category": "breath",
            "expected_effect": "Provides immediate nervous system regulation.",
            "safety_note": "Breathe naturally and avoid force.",
            "steps": [
                "Inhale for 4, exhale for 6 for 2 minutes.",
                "Soften shoulders and jaw on each exhale.",
            ],
        },
        5: {
            "id": "general_state_reset_5m",
            "title": "5-Minute State Reset",
            "category": "mindfulness",
            "expected_effect": "Improves clarity and emotional steadiness.",
            "safety_note": "Pause if emotions intensify; return to simple breathing.",
            "steps": [
                "Name what you feel in one sentence.",
                "Take 10 slow breaths.",
                "Choose one concrete next step.",
            ],
        },
        10: {
            "id": "general_walk_reset_10m",
            "title": "10-Minute Walk Reset",
            "category": "activity",
            "expected_effect": "Resets body and mind through gentle movement.",
            "safety_note": "Walk at a safe pace for your body.",
            "steps": [
                "Take a short walk with steady breathing.",
                "Reduce phone use and keep attention outward.",
                "Return and hydrate.",
            ],
        },
    },
}


def _build_companion_protocols(dosha: Optional[str]) -> List[CompanionProtocolOption]:
    library = PROTOCOL_LIBRARY.get((dosha or "").lower(), PROTOCOL_LIBRARY["fallback"])
    options: List[CompanionProtocolOption] = []
    for minutes in (2, 5, 10):
        item = library.get(minutes)
        if not item:
            continue
        options.append(CompanionProtocolOption(
            id=item["id"],
            title=item["title"],
            category=item["category"],
            duration_minutes=minutes,
            related_dosha=dosha,
            expected_effect=item["expected_effect"],
            safety_note=item["safety_note"],
            steps=item["steps"],
        ))
    return options


def _find_protocol(protocol_id: str) -> Optional[CompanionProtocolOption]:
    for dosha_key in PROTOCOL_LIBRARY:
        entries = PROTOCOL_LIBRARY[dosha_key]
        for minutes in (2, 5, 10):
            item = entries.get(minutes)
            if not item or item["id"] != protocol_id:
                continue
            related = None if dosha_key == "fallback" else dosha_key
            return CompanionProtocolOption(
                id=item["id"],
                title=item["title"],
                category=item["category"],
                duration_minutes=minutes,
                related_dosha=related,
                expected_effect=item["expected_effect"],
                safety_note=item["safety_note"],
                steps=item["steps"],
            )
    return None


def _protocol_category_to_intervention_type(category: str) -> str:
    mapping = {
        "breath": "mindfulness",
        "mindfulness": "mindfulness",
        "activity": "activity",
        "nourishment": "food",
    }
    return mapping.get(category, "activity")


def _infer_urgency(symptom: str, energy_level: Optional[float], confidence: float) -> str:
    symptom_lower = symptom.lower()
    high_risk_markers = ("panic", "overwhelmed", "burnout", "insomnia", "dizziness")
    if any(marker in symptom_lower for marker in high_risk_markers):
        return "high"
    if energy_level is not None and energy_level <= 0.2:
        return "high"
    if confidence < 0.35:
        return "normal_with_uncertainty"
    return "normal"


# =============================================================================
# Feedback Endpoints (A.8.2)
# =============================================================================

@router.post("/feedback")
async def log_feedback(request: FeedbackRequest) -> Dict[str, Any]:
    """
    Log feedback on a recommendation.

    Supports both explicit feedback (thumbs up/down) and implicit
    signals (was_followed, was_reordered).
    """
    from sakhi.apps.api.services.learning.feedback import (
        log_recommendation_feedback, FeedbackType
    )

    try:
        feedback_type = FeedbackType(request.feedback_type)
    except ValueError:
        raise HTTPException(400, f"Invalid feedback_type: {request.feedback_type}")

    feedback_id = await log_recommendation_feedback(
        person_id=request.person_id,
        recommendation_type=request.recommendation_type,
        recommendation_content=request.recommendation_content,
        feedback_type=feedback_type,
        feedback_text=request.feedback_text,
        rating=request.rating,
        was_followed=request.was_followed,
        was_reordered=request.was_reordered,
        recommendation_domain=request.recommendation_domain,
        conversation_id=request.conversation_id,
    )

    if not feedback_id:
        raise HTTPException(500, "Failed to log feedback")

    return {
        "success": True,
        "feedback_id": feedback_id,
        "message": "Feedback logged and preferences updated",
    }


@router.post("/feedback/extract")
async def extract_feedback_from_text(
    person_id: str,
    text: str,
    recent_recommendation: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Extract feedback from conversational text.

    Analyzes text for feedback signals like "too spicy", "loved it", etc.
    """
    from sakhi.apps.api.services.learning.feedback import extract_feedback_from_text

    feedback = await extract_feedback_from_text(
        person_id=person_id,
        text=text,
        recent_recommendation=recent_recommendation,
    )

    if not feedback:
        return {"found": False, "feedback": None}

    return {
        "found": True,
        "feedback": feedback.model_dump(),
    }


@router.get("/feedback/summary")
async def get_feedback_summary(
    person_id: str,
    domain: Optional[str] = None,
    days: int = Query(default=30, le=365),
) -> Dict[str, Any]:
    """Get summary of feedback patterns for a user."""
    from sakhi.apps.api.services.learning.feedback import get_feedback_summary

    return await get_feedback_summary(person_id, domain, days)


# =============================================================================
# Choice Endpoints (A.8.1)
# =============================================================================

@router.post("/choice")
async def log_choice(request: ChoiceRequest) -> Dict[str, Any]:
    """
    Log a user's choice between options.

    When presenting multiple options and user picks one,
    this logs the choice for preference learning.
    """
    from sakhi.apps.api.services.learning.choices import log_user_choice

    choice_id = await log_user_choice(
        person_id=request.person_id,
        choice_context=request.choice_context,
        options_presented=request.options_presented,
        chosen_option=request.chosen_option,
        chosen_index=request.chosen_index,
        conversation_id=request.conversation_id,
    )

    if not choice_id:
        raise HTTPException(500, "Failed to log choice")

    return {
        "success": True,
        "choice_id": choice_id,
        "message": "Choice logged and preferences updated",
    }


@router.get("/choice/patterns")
async def get_choice_patterns(
    person_id: str,
    context: Optional[str] = None,
    days: int = Query(default=30, le=365),
) -> Dict[str, Any]:
    """
    Analyze choice patterns for a user.

    Returns insights like "tends to choose higher spice levels"
    or "often picks first option".
    """
    from sakhi.apps.api.services.learning.choices import get_choice_patterns

    return await get_choice_patterns(
        person_id=person_id,
        context=context,
        lookback_days=days,
    )


# =============================================================================
# Outcome Endpoints (A.7.3)
# =============================================================================

@router.post("/outcome")
async def log_outcome(request: OutcomeRequest) -> Dict[str, Any]:
    """
    Log the outcome of an intervention.

    Track whether suggestions (walk, meditation, warm meal) actually helped.
    """
    from sakhi.apps.api.services.learning.outcomes import log_intervention_outcome

    outcome_id = await log_intervention_outcome(
        person_id=request.person_id,
        intervention_type=request.intervention_type,
        intervention_name=request.intervention_name,
        was_effective=request.was_effective,
        effectiveness_score=request.effectiveness_score,
        symptom_addressed=request.symptom_addressed,
        related_dosha=request.related_dosha,
        notes=request.notes,
    )

    if not outcome_id:
        raise HTTPException(500, "Failed to log outcome")

    return {
        "success": True,
        "outcome_id": outcome_id,
    }


@router.get("/outcome/effective")
async def get_effective_interventions(
    person_id: str,
    symptom: Optional[str] = None,
    dosha: Optional[str] = None,
    min_effectiveness: float = Query(default=0.5, ge=0.0, le=1.0),
    limit: int = Query(default=10, le=50),
) -> Dict[str, Any]:
    """
    Get interventions that have worked for this user.

    Used for "last time, X helped" responses.
    """
    from sakhi.apps.api.services.learning.outcomes import get_effective_interventions

    interventions = await get_effective_interventions(
        person_id=person_id,
        symptom=symptom,
        dosha=dosha,
        min_effectiveness=min_effectiveness,
        limit=limit,
    )

    return {
        "interventions": interventions,
        "count": len(interventions),
    }


@router.post("/outcome/resolution")
async def update_symptom_resolution(request: SymptomResolutionRequest) -> Dict[str, Any]:
    """
    Update a symptom log entry with resolution information.

    Called when user reports feeling better to track what helped.
    """
    from sakhi.apps.api.services.learning.outcomes import update_symptom_resolution

    success = await update_symptom_resolution(
        person_id=request.person_id,
        symptom_log_id=request.symptom_log_id,
        interventions_tried=request.interventions_tried,
        what_helped=request.what_helped,
        what_didnt_help=request.what_didnt_help,
        resolution_summary=request.resolution_summary,
    )

    if not success:
        raise HTTPException(500, "Failed to update symptom resolution")

    return {"success": True}


# =============================================================================
# Learning Trigger Endpoints (A.7.5)
# =============================================================================

@router.post("/trigger")
async def trigger_learning(request: TriggerRequest) -> Dict[str, Any]:
    """
    Trigger a learning cycle for a user.

    This runs:
    1. Pattern detection from recent behaviors/symptoms
    2. Preference updates from feedback
    3. Records the learning run
    """
    from sakhi.apps.api.services.learning.trigger import (
        should_trigger_learning, run_learning_cycle
    )

    # Check if we should run
    if not request.force:
        should_run, reason = await should_trigger_learning(request.person_id)
        if not should_run:
            return {
                "triggered": False,
                "reason": reason,
                "message": f"Learning not triggered: {reason}",
            }

    # Run the cycle
    result = await run_learning_cycle(
        person_id=request.person_id,
        trigger_reason="manual" if request.force else "threshold",
        lookback_days=request.lookback_days,
    )

    return {
        "triggered": True,
        "run_id": result.run_id,
        "status": result.status,
        "behaviors_processed": result.behaviors_processed,
        "symptoms_processed": result.symptoms_processed,
        "patterns_detected": result.patterns_detected,
        "patterns_strengthened": result.patterns_strengthened,
        "preferences_updated": result.preferences_updated,
        "duration_ms": result.duration_ms,
        "error": result.error,
    }


@router.get("/trigger/check")
async def check_learning_trigger(person_id: str) -> Dict[str, Any]:
    """Check if learning should be triggered for a user."""
    from sakhi.apps.api.services.learning.trigger import should_trigger_learning

    should_run, reason = await should_trigger_learning(person_id)

    return {
        "should_trigger": should_run,
        "reason": reason,
    }


@router.get("/history")
async def get_learning_history(
    person_id: str,
    limit: int = Query(default=10, le=50),
) -> Dict[str, Any]:
    """Get learning run history for a user."""
    from sakhi.apps.api.services.learning.trigger import get_learning_history

    history = await get_learning_history(person_id, limit)

    return {
        "history": history,
        "count": len(history),
    }


# =============================================================================
# Preference Adjustment Endpoints (A.8.3)
# =============================================================================

@router.get("/adjustments")
async def get_preference_adjustments(
    person_id: str,
    domain: Optional[str] = None,
    days: int = Query(default=30, le=365),
    limit: int = Query(default=50, le=200),
) -> Dict[str, Any]:
    """
    Get history of preference adjustments.

    Shows how preferences have changed over time from feedback.
    """
    from sakhi.apps.api.services.learning.preference_updater import get_adjustment_history

    adjustments = await get_adjustment_history(
        person_id=person_id,
        domain=domain,
        days=days,
        limit=limit,
    )

    return {
        "adjustments": adjustments,
        "count": len(adjustments),
    }


@router.post("/decay")
async def apply_preference_decay(person_id: str, days_threshold: int = 90) -> Dict[str, Any]:
    """
    Apply decay to stale preferences.

    Preferences that haven't been reinforced gradually decay toward neutral.
    """
    from sakhi.apps.api.services.learning.preference_updater import decay_stale_preferences

    result = await decay_stale_preferences(person_id, days_threshold)

    return {
        "success": True,
        "decays_applied": result.get("decays_applied", 0),
    }


# =============================================================================
# Intervention Plan Endpoints (A.4.1)
# =============================================================================

class CreatePlanRequest(BaseModel):
    """Request to create an intervention plan."""
    person_id: str
    intervention_type: str = Field(default="activity", description="activity, food, mindfulness, sleep, social")
    intervention_name: str = Field(description="Name of the intervention (e.g., 'morning walk')")
    description: Optional[str] = None
    schedule_type: str = Field(default="daily", description="daily, alternate_days, weekly, specific_days")
    schedule_days: Optional[List[int]] = Field(default=None, description="For specific_days: 0=Mon, 6=Sun")
    target_per_day: int = Field(default=1, ge=1)
    duration_days: int = Field(default=14, ge=1, le=90)
    target_symptom: Optional[str] = None
    target_dosha: Optional[str] = None
    baseline_severity: Optional[float] = Field(default=None, ge=0, le=1)
    recommendation_id: Optional[str] = None
    conversation_id: Optional[str] = None


class CheckInRequest(BaseModel):
    """Request to record a check-in."""
    plan_id: str
    completed: bool = True
    completed_count: int = 1
    notes: Optional[str] = None
    mood_before: Optional[float] = Field(default=None, ge=0, le=1)
    mood_after: Optional[float] = Field(default=None, ge=0, le=1)


@router.post("/plan")
async def create_plan(request: CreatePlanRequest) -> Dict[str, Any]:
    """
    Create an intervention plan from a recommendation.

    Called when user opts in to track a recommended routine.
    Example: "Walk 20 min every other day for 2 weeks"
    """
    from sakhi.apps.api.services.learning.intervention_plans import (
        create_intervention_plan,
        CreatePlanRequest as PlanRequest,
    )

    plan = await create_intervention_plan(PlanRequest(
        person_id=request.person_id,
        intervention_type=request.intervention_type,
        intervention_name=request.intervention_name,
        description=request.description,
        schedule_type=request.schedule_type,
        schedule_days=request.schedule_days,
        target_per_day=request.target_per_day,
        duration_days=request.duration_days,
        target_symptom=request.target_symptom,
        target_dosha=request.target_dosha,
        baseline_severity=request.baseline_severity,
        recommendation_id=request.recommendation_id,
        conversation_id=request.conversation_id,
    ))

    return {
        "success": True,
        "plan_id": plan.id,
        "intervention_name": plan.intervention_name,
        "schedule_type": plan.schedule_type.value,
        "duration_days": plan.duration_days,
        "total_scheduled": plan.total_scheduled,
        "start_date": plan.start_date.isoformat(),
        "end_date": plan.end_date.isoformat() if plan.end_date else None,
    }


@router.post("/plan/checkin")
async def record_checkin(request: CheckInRequest) -> Dict[str, Any]:
    """
    Record a check-in for an intervention.

    Called when user reports they did (or skipped) the intervention.
    """
    from sakhi.apps.api.services.learning.intervention_plans import record_checkin as do_checkin

    checkin = await do_checkin(
        plan_id=request.plan_id,
        completed=request.completed,
        completed_count=request.completed_count,
        notes=request.notes,
        mood_before=request.mood_before,
        mood_after=request.mood_after,
    )

    if not checkin:
        raise HTTPException(500, "Failed to record check-in")

    return {
        "success": True,
        "checkin_id": checkin.id,
        "status": checkin.status.value,
        "completed_count": checkin.completed_count,
    }


@router.get("/plan/today")
async def get_today_plans(person_id: str) -> Dict[str, Any]:
    """
    Get interventions that need check-in today.

    Used to show "Did you do X today?" prompts.
    """
    from sakhi.apps.api.services.learning.intervention_plans import get_today_checkins

    checkins = await get_today_checkins(person_id)

    return {
        "date": str(date.today()),
        "checkins": checkins,
        "count": len(checkins),
        "pending": sum(1 for c in checkins if c.get("needs_checkin")),
    }


@router.get("/plan/{plan_id}/progress")
async def get_plan_progress(plan_id: str) -> Dict[str, Any]:
    """
    Get detailed progress for an intervention plan.

    Shows adherence rate, streaks, symptom improvement.
    """
    from sakhi.apps.api.services.learning.intervention_plans import get_plan_progress as get_progress

    progress = await get_progress(plan_id)

    if not progress:
        raise HTTPException(404, "Plan not found")

    return progress.model_dump()


@router.get("/plan/active")
async def get_active_plans(person_id: str) -> Dict[str, Any]:
    """Get all active intervention plans for a user."""
    from sakhi.apps.api.services.learning.intervention_plans import get_active_plans as get_plans

    plans = await get_plans(person_id)

    return {
        "plans": [p.model_dump() for p in plans],
        "count": len(plans),
    }


@router.post("/plan/{plan_id}/pause")
async def pause_plan(plan_id: str) -> Dict[str, Any]:
    """Pause an active intervention plan."""
    from sakhi.apps.api.services.learning.intervention_plans import pause_plan as do_pause

    await do_pause(plan_id)
    return {"success": True, "status": "paused"}


@router.post("/plan/{plan_id}/resume")
async def resume_plan(plan_id: str) -> Dict[str, Any]:
    """Resume a paused intervention plan."""
    from sakhi.apps.api.services.learning.intervention_plans import resume_plan as do_resume

    await do_resume(plan_id)
    return {"success": True, "status": "active"}


@router.post("/plan/{plan_id}/complete")
async def complete_plan(plan_id: str) -> Dict[str, Any]:
    """Mark an intervention plan as completed."""
    from sakhi.apps.api.services.learning.intervention_plans import (
        complete_plan as do_complete,
        correlate_plan_outcomes,
    )

    await do_complete(plan_id)

    # Correlate outcomes
    correlation = await correlate_plan_outcomes(plan_id)

    return {
        "success": True,
        "status": "completed",
        "outcome": correlation,
    }


@router.post("/plan/{plan_id}/abandon")
async def abandon_plan(plan_id: str, reason: Optional[str] = None) -> Dict[str, Any]:
    """Abandon an intervention plan."""
    from sakhi.apps.api.services.learning.intervention_plans import abandon_plan as do_abandon

    await do_abandon(plan_id, reason)
    return {"success": True, "status": "abandoned"}


# =============================================================================
# Companion Endpoints (Stage 1)
# =============================================================================

@router.post("/companion/checkin")
async def companion_checkin(request: CompanionCheckInRequest) -> Dict[str, Any]:
    """
    Fast companion check-in flow:
    1) Capture symptom + state signals
    2) Explain likely causes
    3) Offer 2/5/10 minute protocol options
    """
    from sakhi.apps.api.services.ayurveda.causal_reasoning import (
        explain_symptom,
        map_symptom_to_dosha,
    )
    from sakhi.apps.api.core.telemetry import log_trace_event

    symptom = request.symptom.strip()
    checkin_id = str(uuid4())

    await log_trace_event(
        "funnel.checkin_started",
        {
            "person_id": request.person_id,
            "symptom": symptom,
            "energy_level": request.energy_level,
            "body_cues_count": len(request.body_cues),
        },
    )

    explanation = await explain_symptom(
        person_id=request.person_id,
        symptom=symptom,
        context={
            "energy_level": request.energy_level,
            "body_cues": request.body_cues,
            "note": request.note,
        },
    )

    dosha_hint = map_symptom_to_dosha(symptom)
    top_confidence = (
        float(explanation.primary_causes[0].confidence)
        if explanation.primary_causes
        else 0.35
    )
    top_confidence = max(0.0, min(1.0, top_confidence))

    protocols = _build_companion_protocols(dosha_hint)
    evidence = [
        {
            "factor_type": c.factor_type,
            "description": c.description,
            "confidence": round(float(c.confidence), 2),
            "evidence": c.evidence,
        }
        for c in explanation.primary_causes[:3]
    ]

    await log_trace_event(
        "funnel.insight_shown",
        {
            "person_id": request.person_id,
            "checkin_id": checkin_id,
            "symptom": symptom,
            "dosha_hint": dosha_hint,
            "confidence": round(top_confidence, 2),
            "protocol_count": len(protocols),
        },
    )

    return {
        "checkin_id": checkin_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "symptom": symptom,
        "dosha_hint": dosha_hint,
        "urgency": _infer_urgency(symptom, request.energy_level, top_confidence),
        "confidence": round(top_confidence, 2),
        "uncertainty": round(1.0 - top_confidence, 2),
        "dosha_context": explanation.dosha_context,
        "explanation": explanation.explanation_text,
        "evidence": evidence,
        "protocols": [p.model_dump() for p in protocols],
    }


@router.post("/companion/followup/plan")
async def companion_create_followup_plan(
    request: CompanionFollowUpPlanRequest,
) -> Dict[str, Any]:
    """
    Convert a selected short protocol into a tracked daily plan.
    """
    from sakhi.apps.api.services.learning.intervention_plans import (
        CreatePlanRequest as PlanRequest,
        create_intervention_plan,
    )
    from sakhi.apps.api.core.telemetry import log_trace_event

    protocol = _find_protocol(request.protocol_id)
    if not protocol:
        raise HTTPException(status_code=400, detail=f"Unknown protocol_id: {request.protocol_id}")

    plan = await create_intervention_plan(PlanRequest(
        person_id=request.person_id,
        intervention_type=_protocol_category_to_intervention_type(protocol.category),
        intervention_name=protocol.title,
        description=(
            f"{protocol.expected_effect} "
            f"(Symptom: {request.symptom.strip()}; Duration: {protocol.duration_minutes}m)"
        ),
        schedule_type="daily",
        target_per_day=request.target_per_day,
        duration_days=request.target_days,
        target_symptom=request.symptom.strip(),
        target_dosha=protocol.related_dosha,
        recommendation_id=request.checkin_id,
    ))

    await log_trace_event(
        "funnel.protocol_selected",
        {
            "person_id": request.person_id,
            "protocol_id": protocol.id,
            "target_days": request.target_days,
            "target_per_day": request.target_per_day,
            "checkin_id": request.checkin_id,
        },
    )
    await log_trace_event(
        "funnel.followup_submitted",
        {
            "person_id": request.person_id,
            "plan_id": plan.id,
            "protocol_id": protocol.id,
            "target_symptom": request.symptom.strip(),
        },
    )

    return {
        "success": True,
        "plan_id": plan.id,
        "protocol_id": protocol.id,
        "intervention_name": plan.intervention_name,
        "schedule_type": plan.schedule_type.value,
        "duration_days": plan.duration_days,
        "total_scheduled": plan.total_scheduled,
        "start_date": plan.start_date.isoformat(),
        "end_date": plan.end_date.isoformat() if plan.end_date else None,
    }


@router.post("/companion/protocol/complete")
async def companion_complete_protocol(
    request: CompanionProtocolCompletionRequest,
) -> Dict[str, Any]:
    """
    Record whether a selected protocol helped.
    """
    from sakhi.apps.api.services.learning.outcomes import log_intervention_outcome
    from sakhi.apps.api.core.telemetry import log_trace_event

    protocol = _find_protocol(request.protocol_id)
    if not protocol:
        raise HTTPException(status_code=400, detail=f"Unknown protocol_id: {request.protocol_id}")

    outcome_id = await log_intervention_outcome(
        person_id=request.person_id,
        intervention_type=_protocol_category_to_intervention_type(protocol.category),
        intervention_name=protocol.title,
        was_effective=request.was_effective,
        effectiveness_score=request.effectiveness_score,
        symptom_addressed=request.symptom.strip(),
        related_dosha=protocol.related_dosha,
        notes=request.notes,
    )

    if not outcome_id:
        raise HTTPException(status_code=500, detail="Failed to log protocol outcome")

    await log_trace_event(
        "funnel.protocol_completed",
        {
            "person_id": request.person_id,
            "protocol_id": protocol.id,
            "was_effective": request.was_effective,
            "effectiveness_score": request.effectiveness_score,
            "symptom": request.symptom.strip(),
        },
    )
    if request.was_effective:
        await log_trace_event(
            "funnel.benefit_reported",
            {
                "person_id": request.person_id,
                "protocol_id": protocol.id,
                "effectiveness_score": request.effectiveness_score,
                "symptom": request.symptom.strip(),
            },
        )

    return {
        "success": True,
        "outcome_id": outcome_id,
        "protocol_id": protocol.id,
    }


# =============================================================================
# Nudge Endpoints (A.4.1)
# =============================================================================

@router.get("/nudges")
async def get_nudges(person_id: str) -> Dict[str, Any]:
    """
    Get all nudges for today.

    Returns reminders, encouragements, and check-in prompts.
    """
    from sakhi.apps.api.services.learning.nudges import generate_daily_nudges, save_nudge

    nudges = await generate_daily_nudges(person_id)

    # Save and return
    saved = []
    for nudge in nudges:
        nudge_id = await save_nudge(nudge)
        saved.append({
            "id": nudge_id,
            "type": nudge.nudge_type.value,
            "message": nudge.message,
            "plan_id": nudge.plan_id,
            "action_options": nudge.action_options,
        })

    return {
        "nudges": saved,
        "count": len(saved),
    }


@router.get("/nudges/unread")
async def get_unread_nudges(
    person_id: str,
    limit: int = Query(default=10, le=50),
) -> Dict[str, Any]:
    """Get unread nudges for a user."""
    from sakhi.apps.api.services.learning.nudges import get_unread_nudges as get_unread

    nudges = await get_unread(person_id, limit)

    return {
        "nudges": [n.model_dump() for n in nudges],
        "count": len(nudges),
    }


@router.post("/nudges/{nudge_id}/read")
async def mark_nudge_read(nudge_id: str) -> Dict[str, Any]:
    """Mark a nudge as read."""
    from sakhi.apps.api.services.learning.nudges import mark_nudge_read as do_read

    await do_read(nudge_id)
    return {"success": True}


@router.post("/nudges/{nudge_id}/acted")
async def mark_nudge_acted(nudge_id: str) -> Dict[str, Any]:
    """Mark a nudge as acted upon."""
    from sakhi.apps.api.services.learning.nudges import mark_nudge_acted as do_act

    await do_act(nudge_id)
    return {"success": True}


@router.get("/checkin/prompt")
async def get_checkin_prompt(person_id: str) -> Dict[str, Any]:
    """
    Get a check-in prompt for the chat UI.

    Returns a structured prompt with action buttons.
    """
    from sakhi.apps.api.services.learning.nudges import get_checkin_prompt as get_prompt

    prompt = await get_prompt(person_id)

    if not prompt:
        return {"has_prompt": False}

    return {
        "has_prompt": True,
        "prompt": prompt,
    }


# =============================================================================
# Background Jobs
# =============================================================================

@router.post("/jobs/mark-missed")
async def run_mark_missed_job() -> Dict[str, Any]:
    """
    Mark pending check-ins from past days as missed.

    Should be run daily as a background job.
    """
    from sakhi.apps.api.services.learning.intervention_plans import mark_missed_checkins

    count = await mark_missed_checkins()

    return {
        "success": True,
        "missed_marked": count,
    }
