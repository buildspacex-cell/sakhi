"""
Friction Framework API Routes

This module implements the user-facing API for the Friction Framework MVP,
which translates Ayurvedic concepts into modern wellness terminology.

Terminology Mapping:
- Doshas → Operating Systems (Adaptive/Performance/Conservation)
- Gunas → Operating Modes (Clarity/Activation/Recovery)
- Dosha Imbalance → Friction States (Chaos/Intensity/Stagnation)
- Prakruti → Baseline (constitutional type)
- Vikriti → Current State (deviation from baseline)

Endpoints:
- POST /onboarding/assessment - Submit quiz, compute Operating System
- GET /profile/operating-system/{person_id} - Get stored OS
- GET /state/current/{person_id} - Get current state vs baseline
- GET /state/friction-state/{person_id} - Get just friction state
- GET /recommendations/now/{person_id} - Get contextual recommendations
- GET /state/weekly/{person_id} - Get weekly summary
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Request

from pydantic import BaseModel, Field

from sakhi.apps.api.core.db import q, exec
from sakhi.libs.llm_router import LLMRouter

LOGGER = logging.getLogger(__name__)

router = APIRouter(tags=["friction-framework"])


# =============================================================================
# PYDANTIC MODELS
# =============================================================================

class AssessmentResponse(BaseModel):
    question_id: str
    answer: str


class AssessmentRequest(BaseModel):
    person_id: str
    responses: List[AssessmentResponse]


class DoshaBaseline(BaseModel):
    vata: float
    pitta: float
    kapha: float


class OperatingSystemResult(BaseModel):
    operating_system: str
    primary: str
    secondary: Optional[str]
    dosha_baseline: DoshaBaseline
    stored: bool


class OperatingSystemProfile(BaseModel):
    operating_system: str
    primary: str
    secondary: Optional[str]
    dosha_baseline: DoshaBaseline
    description: str
    strengths: List[str]
    vulnerabilities: List[str]
    traits: List[str]


class GunaScores(BaseModel):
    sattva: float
    rajas: float
    tamas: float


class OperatingModeDetail(BaseModel):
    mode: str
    guna_dominant: str
    guna_scores: GunaScores
    description: str


class FrictionStateDetail(BaseModel):
    state: Optional[str]
    dosha_elevated: Optional[str]
    severity: str
    description: str


class BaselineDriftDetail(BaseModel):
    percentage: float
    direction: str
    primary_contributor: Optional[str]
    description: str


class CurrentDoshaState(BaseModel):
    vata: float
    pitta: float
    kapha: float


class CurrentStateResponse(BaseModel):
    timestamp: str
    operating_mode: OperatingModeDetail
    friction_state: FrictionStateDetail
    baseline_drift: BaselineDriftDetail
    current_dosha: CurrentDoshaState


class FrictionStateResponse(BaseModel):
    friction_state: Optional[str]
    friction_color: str
    dosha_elevated: Optional[str]
    severity: str
    since: Optional[str]


class RecommendationItem(BaseModel):
    action: str
    why: str
    category: str
    icon: str


class PatternInsight(BaseModel):
    pattern: str
    suggestion: str


class RecommendationsResponse(BaseModel):
    timestamp: str
    friction_state: Optional[str]
    recommendations: List[RecommendationItem]
    pattern_insight: Optional[PatternInsight]


class DayData(BaseModel):
    date: str
    has_entry: bool
    dominant_mode: Optional[str]


class DominantFriction(BaseModel):
    state: Optional[str]
    days_count: int
    description: str


class WeeklyStateResponse(BaseModel):
    week_start: str
    coherence_score: float
    coherence_trend: str
    days: List[DayData]
    dominant_friction: DominantFriction
    weekly_insight: str


# Full onboarding request with all questionnaire data
class FullOnboardingRequest(BaseModel):
    person_id: str
    responses: Dict[str, Any]  # Flexible dict to handle all question types
    completed_at: str


class FullOnboardingResult(BaseModel):
    operating_system: str
    primary: str
    secondary: Optional[str]
    dosha_baseline: DoshaBaseline
    life_context: Dict[str, Any]
    decision_profile: Dict[str, Any]
    stored: bool


# =============================================================================
# OPERATING SYSTEM DEFINITIONS
# =============================================================================

# Maps dosha combinations to Operating System types
OS_TYPE_DEFINITIONS: Dict[str, Dict[str, Any]] = {
    "Adaptive": {
        "primary": "Adaptive",
        "secondary": None,
        "description": "You're naturally creative and adaptable. Your mind moves quickly, you embrace change, and you thrive with variety. You need grounding practices to balance your variable energy.",
        "strengths": [
            "Quick thinking and innovation",
            "Highly adaptable to change",
            "Creative problem-solving",
            "Enthusiastic and energetic"
        ],
        "vulnerabilities": [
            "Prone to scattered energy",
            "Difficulty with routine",
            "Variable sleep patterns",
            "Can become anxious under stress"
        ],
        "traits": ["Quick thinking", "Creative", "Adaptable", "Variable energy"]
    },
    "Performance": {
        "primary": "Performance",
        "secondary": None,
        "description": "You're naturally driven and focused. You pursue goals with intensity, have strong execution capacity, and thrive on challenge. You need cooling practices to avoid burnout.",
        "strengths": [
            "Strong focus and determination",
            "Excellent execution capacity",
            "Natural leadership",
            "Sharp analytical mind"
        ],
        "vulnerabilities": [
            "Risk of burnout from intensity",
            "Can become irritable under pressure",
            "Perfectionist tendencies",
            "Difficulty delegating"
        ],
        "traits": ["Driven", "Focused", "Intense", "Goal-oriented"]
    },
    "Conservation": {
        "primary": "Conservation",
        "secondary": None,
        "description": "You're naturally steady and grounded. You prefer stability, build lasting relationships, and have great endurance. You need stimulation practices to maintain momentum.",
        "strengths": [
            "Exceptional endurance",
            "Calm under pressure",
            "Reliable and consistent",
            "Strong memory and retention"
        ],
        "vulnerabilities": [
            "Prone to stagnation",
            "Resistance to change",
            "Can become lethargic",
            "Difficulty letting go"
        ],
        "traits": ["Steady", "Grounded", "Reliable", "Enduring"]
    },
    "Adaptive-Performance": {
        "primary": "Adaptive",
        "secondary": "Performance",
        "description": "You blend creativity with execution. Your mind moves fast, you pursue goals intensely, but you need variety and can burn out without recovery.",
        "strengths": [
            "Quick thinking and innovation",
            "Strong focus when engaged",
            "Adaptable to change",
            "Natural problem solver"
        ],
        "vulnerabilities": [
            "Prone to scattered energy",
            "Risk of burnout from intensity",
            "Difficulty with routine",
            "Can push past limits"
        ],
        "traits": ["Quick thinking", "Innovative", "Driven", "Variable energy"]
    },
    "Performance-Conservation": {
        "primary": "Performance",
        "secondary": "Conservation",
        "description": "You combine drive with endurance. You pursue goals with determination and have the stamina to see them through. You need balance between intensity and rest.",
        "strengths": [
            "Strong focus and determination",
            "Excellent stamina",
            "Reliable execution",
            "Calm under pressure"
        ],
        "vulnerabilities": [
            "Can become rigid",
            "Risk of overwork",
            "Difficulty with change",
            "Stubbornness under stress"
        ],
        "traits": ["Determined", "Enduring", "Reliable", "Intense"]
    },
    "Adaptive-Conservation": {
        "primary": "Adaptive",
        "secondary": "Conservation",
        "description": "You blend creativity with stability. You have innovative ideas and the patience to develop them. You need stimulation to avoid stagnation while honoring your need for grounding.",
        "strengths": [
            "Creative yet grounded",
            "Patient innovation",
            "Adaptable but stable",
            "Thoughtful decision-making"
        ],
        "vulnerabilities": [
            "Indecisiveness",
            "Prone to both scatter and stagnation",
            "Variable energy with slow recovery",
            "Can become stuck in analysis"
        ],
        "traits": ["Creative", "Patient", "Adaptable", "Grounded"]
    },
    "Balanced": {
        "primary": "Balanced",
        "secondary": None,
        "description": "You have a rare balanced constitution. You can adapt to different modes as needed but should be mindful of environmental and seasonal influences.",
        "strengths": [
            "Versatile and adaptable",
            "Naturally balanced",
            "Can thrive in varied situations",
            "Good self-regulation"
        ],
        "vulnerabilities": [
            "Sensitive to environmental changes",
            "May lack a strong default mode",
            "Can be influenced by others' energy",
            "Needs conscious balance maintenance"
        ],
        "traits": ["Versatile", "Balanced", "Adaptable", "Centered"]
    }
}

# Maps friction states to colors and recommendations
FRICTION_STATE_CONFIG: Dict[str, Dict[str, Any]] = {
    "Chaos Friction": {
        "color": "#e8c547",
        "dosha": "vata",
        "recommendations": [
            {
                "action": "Close 2-3 open loops before anything new",
                "why": "Reduces mental scatter immediately",
                "category": "immediate",
                "icon": "clock"
            },
            {
                "action": "5 minutes of slow, deep breathing",
                "why": "Activates your recovery system",
                "category": "immediate",
                "icon": "breath"
            },
            {
                "action": "Warm drink, no caffeine",
                "why": "Grounding without more stimulation",
                "category": "immediate",
                "icon": "drink"
            }
        ],
        "pattern_insight": {
            "pattern": "Sleep debt tends to amplify your scattered energy",
            "suggestion": "Tonight, aim for bed 30 min earlier"
        }
    },
    "Intensity Friction": {
        "color": "#e85747",
        "dosha": "pitta",
        "recommendations": [
            {
                "action": "Take a 10-minute cooling break",
                "why": "Reduces mental heat and irritability",
                "category": "immediate",
                "icon": "pause"
            },
            {
                "action": "Delegate or defer one task",
                "why": "Release the pressure of doing everything",
                "category": "immediate",
                "icon": "delegate"
            },
            {
                "action": "Cool water or herbal tea",
                "why": "Physical cooling calms mental intensity",
                "category": "immediate",
                "icon": "drink"
            }
        ],
        "pattern_insight": {
            "pattern": "Perfectionism amplifies your intensity",
            "suggestion": "Ask: Is 80% good enough for this task?"
        }
    },
    "Stagnation Friction": {
        "color": "#4787e8",
        "dosha": "kapha",
        "recommendations": [
            {
                "action": "5-minute brisk walk or stretch",
                "why": "Movement breaks mental stagnation",
                "category": "immediate",
                "icon": "movement"
            },
            {
                "action": "Start one small task, any task",
                "why": "Action creates momentum",
                "category": "immediate",
                "icon": "start"
            },
            {
                "action": "Warm, light food (avoid heavy meals)",
                "why": "Light food increases energy, heavy food adds stagnation",
                "category": "immediate",
                "icon": "food"
            }
        ],
        "pattern_insight": {
            "pattern": "Lack of variety contributes to your stagnation",
            "suggestion": "Try one new or different activity today"
        }
    }
}

# Operating mode definitions
OPERATING_MODES: Dict[str, Dict[str, Any]] = {
    "Clarity": {
        "guna": "sattva",
        "description": "You're in your optimal state — clear, balanced, and focused"
    },
    "Activation": {
        "guna": "rajas",
        "description": "Running high — energy scattered across many things"
    },
    "Recovery": {
        "guna": "tamas",
        "description": "Your body is asking for rest and restoration"
    }
}


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def _compute_dosha_from_responses(responses: List[AssessmentResponse]) -> Dict[str, float]:
    """
    Compute dosha scores from assessment responses.

    Question mapping:
    - q1_challenge: How they approach challenges (Vata=quick, Pitta=analyze, Kapha=steady)
    - q2_energy: Energy patterns (Vata=variable, Pitta=intense, Kapha=steady)
    - q3_stress: Stress response (Vata=anxious, Pitta=irritable, Kapha=withdraw)
    - q4_environment: Work preference (Vata=dynamic, Pitta=challenging, Kapha=calm)
    - q5_sleep: Sleep patterns (Vata=light, Pitta=moderate, Kapha=deep)
    """
    scores = {"vata": 0.0, "pitta": 0.0, "kapha": 0.0}

    answer_weights = {
        # Q1: Challenge approach
        "jump_in_quickly": {"vata": 1.0, "pitta": 0.3, "kapha": 0.0},
        "analyze_thoroughly": {"vata": 0.2, "pitta": 1.0, "kapha": 0.3},
        "take_time_steady": {"vata": 0.0, "pitta": 0.2, "kapha": 1.0},
        # Q2: Energy patterns
        "variable_bursts": {"vata": 1.0, "pitta": 0.2, "kapha": 0.0},
        "intense_focused": {"vata": 0.2, "pitta": 1.0, "kapha": 0.2},
        "steady_consistent": {"vata": 0.0, "pitta": 0.2, "kapha": 1.0},
        # Q3: Stress response
        "scattered_anxious": {"vata": 1.0, "pitta": 0.1, "kapha": 0.0},
        "irritable_critical": {"vata": 0.1, "pitta": 1.0, "kapha": 0.1},
        "withdraw_heavy": {"vata": 0.0, "pitta": 0.1, "kapha": 1.0},
        # Q4: Work environment
        "dynamic_varied": {"vata": 1.0, "pitta": 0.3, "kapha": 0.0},
        "challenging_competitive": {"vata": 0.2, "pitta": 1.0, "kapha": 0.1},
        "calm_predictable": {"vata": 0.0, "pitta": 0.1, "kapha": 1.0},
        # Q5: Sleep patterns
        "light_irregular": {"vata": 1.0, "pitta": 0.2, "kapha": 0.0},
        "moderate_restless": {"vata": 0.3, "pitta": 1.0, "kapha": 0.2},
        "deep_heavy": {"vata": 0.0, "pitta": 0.2, "kapha": 1.0},
    }

    for response in responses:
        weights = answer_weights.get(response.answer, {})
        for dosha, weight in weights.items():
            scores[dosha] += weight

    # Normalize to sum to 1.0
    total = sum(scores.values())
    if total > 0:
        scores = {k: round(v / total, 2) for k, v in scores.items()}
    else:
        scores = {"vata": 0.33, "pitta": 0.33, "kapha": 0.34}

    return scores


def _determine_os_type(dosha_baseline: Dict[str, float]) -> str:
    """
    Determine Operating System type from dosha baseline.

    Rules:
    - If one dosha > 0.5: Pure type (Adaptive/Performance/Conservation)
    - If two doshas each > 0.3 and combined > 0.7: Dual type
    - Otherwise: Balanced
    """
    vata = dosha_baseline.get("vata", 0.33)
    pitta = dosha_baseline.get("pitta", 0.33)
    kapha = dosha_baseline.get("kapha", 0.34)

    # Check for pure dominant type
    if vata >= 0.5:
        return "Adaptive"
    if pitta >= 0.5:
        return "Performance"
    if kapha >= 0.5:
        return "Conservation"

    # Check for dual types
    sorted_doshas = sorted(
        [("vata", vata), ("pitta", pitta), ("kapha", kapha)],
        key=lambda x: x[1],
        reverse=True
    )

    first, second = sorted_doshas[0], sorted_doshas[1]

    if first[1] >= 0.35 and second[1] >= 0.30:
        # Map dosha names to OS names
        dosha_to_os = {"vata": "Adaptive", "pitta": "Performance", "kapha": "Conservation"}
        os1 = dosha_to_os[first[0]]
        os2 = dosha_to_os[second[0]]
        # Use canonical ordering: Adaptive > Performance > Conservation
        canonical_order = ["Adaptive", "Performance", "Conservation"]
        if canonical_order.index(os1) > canonical_order.index(os2):
            os1, os2 = os2, os1
        return f"{os1}-{os2}"

    return "Balanced"


def _classify_friction_state(
    current_dosha: Dict[str, float],
    baseline_dosha: Dict[str, float],
    threshold: float = 0.25
) -> Optional[str]:
    """
    Classify friction state based on dosha deviation from baseline.

    Returns: "Chaos Friction", "Intensity Friction", "Stagnation Friction", or None
    """
    vata_drift = current_dosha.get("vata", 0.33) - baseline_dosha.get("vata", 0.33)
    pitta_drift = current_dosha.get("pitta", 0.33) - baseline_dosha.get("pitta", 0.33)
    kapha_drift = current_dosha.get("kapha", 0.34) - baseline_dosha.get("kapha", 0.34)

    # Find the largest positive drift
    drifts = [
        ("vata", vata_drift, "Chaos Friction"),
        ("pitta", pitta_drift, "Intensity Friction"),
        ("kapha", kapha_drift, "Stagnation Friction")
    ]

    max_drift = max(drifts, key=lambda x: x[1])

    if max_drift[1] >= threshold:
        return max_drift[2]

    return None


def _determine_operating_mode(guna_scores: Dict[str, float]) -> str:
    """
    Determine operating mode from guna scores.

    Returns: "Clarity", "Activation", or "Recovery"
    """
    sattva = guna_scores.get("sattva", 0.33)
    rajas = guna_scores.get("rajas", 0.33)
    tamas = guna_scores.get("tamas", 0.34)

    if sattva >= rajas and sattva >= tamas:
        return "Clarity"
    if rajas >= sattva and rajas >= tamas:
        return "Activation"
    return "Recovery"


def _calculate_baseline_drift(
    current_dosha: Dict[str, float],
    baseline_dosha: Dict[str, float]
) -> Dict[str, Any]:
    """Calculate drift from baseline as percentage."""
    vata_drift = current_dosha.get("vata", 0.33) - baseline_dosha.get("vata", 0.33)
    pitta_drift = current_dosha.get("pitta", 0.33) - baseline_dosha.get("pitta", 0.33)
    kapha_drift = current_dosha.get("kapha", 0.34) - baseline_dosha.get("kapha", 0.34)

    # Total drift as percentage
    total_drift = abs(vata_drift) + abs(pitta_drift) + abs(kapha_drift)
    drift_percentage = round(total_drift * 100, 0)

    # Determine direction and primary contributor
    drifts = [
        ("vata", vata_drift),
        ("pitta", pitta_drift),
        ("kapha", kapha_drift)
    ]
    max_drift = max(drifts, key=lambda x: abs(x[1]))

    direction = "elevated" if max_drift[1] > 0 else "depleted" if max_drift[1] < 0 else "stable"

    return {
        "percentage": drift_percentage,
        "direction": direction,
        "primary_contributor": max_drift[0] if abs(max_drift[1]) > 0.1 else None
    }


def _compute_dosha_from_full_onboarding(responses: Dict[str, Any]) -> Dict[str, float]:
    """
    Compute dosha scores from the full onboarding questionnaire.

    Uses multiple signals:
    - Rhythm & Energy questions (clarity_window, pacing, current_energy)
    - Body Signals questions (first_stress_signal, body_request, fastest_recovery)
    - Decision Making questions (decision_driver, energy_vs_outcome, flexibility)

    This is more nuanced than the simple 5-question assessment.
    """
    scores = {"vata": 0.0, "pitta": 0.0, "kapha": 0.0}

    # Comprehensive answer weights based on Ayurvedic principles
    answer_weights = {
        # Screen 2: Rhythm & Energy
        "clarity_window": {
            "morning": {"vata": 0.2, "pitta": 0.5, "kapha": 0.8},  # Kapha/Pitta peak morning
            "afternoon": {"vata": 0.3, "pitta": 0.8, "kapha": 0.3},  # Pitta peak midday
            "evening": {"vata": 0.8, "pitta": 0.3, "kapha": 0.2},  # Vata peak evening
            "varies": {"vata": 1.0, "pitta": 0.2, "kapha": 0.1},  # Variable = Vata
        },
        "pacing_under_demand": {
            "push_harder": {"vata": 0.3, "pitta": 1.0, "kapha": 0.1},
            "slow_down": {"vata": 0.1, "pitta": 0.2, "kapha": 1.0},
            "oscillate": {"vata": 1.0, "pitta": 0.3, "kapha": 0.2},
        },
        "current_energy": {
            "steady": {"vata": 0.1, "pitta": 0.4, "kapha": 1.0},
            "waves": {"vata": 0.8, "pitta": 0.4, "kapha": 0.2},
            "drained": {"vata": 0.3, "pitta": 0.2, "kapha": 0.8},  # Kapha imbalance
            "wired_tired": {"vata": 1.0, "pitta": 0.5, "kapha": 0.1},  # Vata imbalance
        },

        # Screen 3: Body Signals
        "first_stress_signal": {
            "sleep_trouble": {"vata": 1.0, "pitta": 0.3, "kapha": 0.1},
            "irritability": {"vata": 0.2, "pitta": 1.0, "kapha": 0.1},
            "low_energy": {"vata": 0.1, "pitta": 0.2, "kapha": 1.0},
            "depends": {"vata": 0.5, "pitta": 0.5, "kapha": 0.5},
        },
        "body_request": {
            "quiet_space": {"vata": 0.8, "pitta": 0.3, "kapha": 0.4},
            "physical_release": {"vata": 0.3, "pitta": 0.8, "kapha": 0.3},
            "rest_food": {"vata": 0.2, "pitta": 0.2, "kapha": 0.9},
            "unsure": {"vata": 0.6, "pitta": 0.3, "kapha": 0.3},
        },
        "fastest_recovery": {
            "calm_time": {"vata": 0.7, "pitta": 0.4, "kapha": 0.5},
            "movement": {"vata": 0.4, "pitta": 0.8, "kapha": 0.3},
            "sleep_food": {"vata": 0.2, "pitta": 0.2, "kapha": 1.0},
            "varies": {"vata": 0.8, "pitta": 0.3, "kapha": 0.2},
        },

        # Screen 5: Food (lighter weight)
        "appetite_pattern": {
            "light_variable": {"vata": 1.0, "pitta": 0.2, "kapha": 0.1},
            "strong_regular": {"vata": 0.1, "pitta": 1.0, "kapha": 0.3},
            "slow_inconsistent": {"vata": 0.3, "pitta": 0.1, "kapha": 0.8},
        },

        # Screen 6: Decision Making
        "decision_driver": {
            "protect_energy": {"vata": 0.6, "pitta": 0.2, "kapha": 0.7},
            "people_relationships": {"vata": 0.3, "pitta": 0.3, "kapha": 0.6},
            "reduce_stress": {"vata": 0.8, "pitta": 0.2, "kapha": 0.4},
            "make_progress": {"vata": 0.3, "pitta": 1.0, "kapha": 0.2},
            "depends": {"vata": 0.6, "pitta": 0.4, "kapha": 0.4},
        },
        "risk_behavior": {
            "safer": {"vata": 0.5, "pitta": 0.1, "kapha": 0.9},
            "calculated_risk": {"vata": 0.3, "pitta": 0.9, "kapha": 0.2},
            "balance": {"vata": 0.4, "pitta": 0.5, "kapha": 0.5},
        },
        "time_horizon": {
            "weeks": {"vata": 0.9, "pitta": 0.4, "kapha": 0.2},
            "year_two": {"vata": 0.3, "pitta": 0.8, "kapha": 0.4},
            "long_term": {"vata": 0.2, "pitta": 0.5, "kapha": 0.8},
        },
        "energy_vs_outcome": {
            "preserve_energy": {"vata": 0.5, "pitta": 0.1, "kapha": 0.8},
            "push_through": {"vata": 0.3, "pitta": 1.0, "kapha": 0.2},
            "case_by_case": {"vata": 0.7, "pitta": 0.4, "kapha": 0.3},
        },
        "flexibility_under_load": {
            "simplify": {"vata": 0.7, "pitta": 0.2, "kapha": 0.6},
            "reorganize": {"vata": 0.3, "pitta": 0.9, "kapha": 0.3},
            "pause_reassess": {"vata": 0.5, "pitta": 0.3, "kapha": 0.7},
        },
    }

    # Weight multipliers for different question categories
    question_weights = {
        # Core constitutional questions (high weight)
        "clarity_window": 1.2,
        "pacing_under_demand": 1.3,
        "current_energy": 1.0,  # Current state, not constitution
        "first_stress_signal": 1.4,  # Strong constitutional signal
        "body_request": 1.3,
        "fastest_recovery": 1.2,
        # Food (moderate weight)
        "appetite_pattern": 0.8,
        # Decision making (moderate weight - behavior can be learned)
        "decision_driver": 0.7,
        "risk_behavior": 0.6,
        "time_horizon": 0.5,
        "energy_vs_outcome": 0.8,
        "flexibility_under_load": 0.7,
    }

    for question_id, weights_map in answer_weights.items():
        answer = responses.get(question_id)
        if answer and answer in weights_map:
            weights = weights_map[answer]
            multiplier = question_weights.get(question_id, 1.0)
            for dosha, weight in weights.items():
                scores[dosha] += weight * multiplier

    # Normalize to sum to 1.0
    total = sum(scores.values())
    if total > 0:
        scores = {k: round(v / total, 2) for k, v in scores.items()}
    else:
        scores = {"vata": 0.33, "pitta": 0.33, "kapha": 0.34}

    return scores


def _extract_life_context(responses: Dict[str, Any]) -> Dict[str, Any]:
    """Extract life context from onboarding responses."""
    return {
        "age_range": responses.get("age_range"),
        "location": responses.get("location"),
        "active_roles": responses.get("active_roles", []),
        "life_phase": responses.get("life_phase"),
        "responsibility_load": responses.get("responsibility_load"),
        "allergies": responses.get("allergies"),
        "foods_avoided": responses.get("foods_avoided"),
    }


def _extract_decision_profile(responses: Dict[str, Any]) -> Dict[str, Any]:
    """Extract decision-making profile from onboarding responses."""
    return {
        "primary_driver": responses.get("decision_driver"),
        "risk_tendency": responses.get("risk_behavior"),
        "time_horizon": responses.get("time_horizon"),
        "energy_tradeoff": responses.get("energy_vs_outcome"),
        "flexibility_style": responses.get("flexibility_under_load"),
    }


async def _analyze_expanded_text_with_llm(
    router: LLMRouter,
    responses: Dict[str, Any]
) -> Optional[Dict[str, float]]:
    """
    Analyze expanded free text responses using LLM to extract additional dosha signals.

    The LLM reads the user's narrative descriptions and identifies:
    - Vata signals (variability, anxiety, creativity, movement)
    - Pitta signals (intensity, drive, irritability, focus)
    - Kapha signals (steadiness, lethargy, stability, attachment)

    Returns adjustment weights to apply to the structured computation.
    """
    # Collect all expanded text fields
    expanded_fields = {
        "clarity_window_expanded": "When do you feel most clear and why",
        "pacing_under_demand_expanded": "How you handle demanding days",
        "current_energy_expanded": "What's contributing to your current energy",
        "first_stress_signal_expanded": "How stress shows up for you",
        "body_request_expanded": "What your body typically asks for",
        "fastest_recovery_expanded": "Specific activities that help you recharge",
        "active_roles_expanded": "What you're juggling in life",
        "life_phase_expanded": "What's shaping your current life phase",
        "responsibility_load_expanded": "Who or what you're carrying",
        "appetite_pattern_expanded": "Your eating patterns",
        "decision_driver_expanded": "A recent example of how you make decisions",
        "risk_behavior_expanded": "What influences your approach to risk",
        "time_horizon_expanded": "The bigger picture you're working toward",
        "energy_vs_outcome_expanded": "How you navigate the tired-but-important tension",
        "flexibility_under_load_expanded": "What you do when things feel too heavy",
    }

    # Gather responses that have expanded text
    expanded_texts = []
    for field_id, description in expanded_fields.items():
        value = responses.get(field_id)
        if value and isinstance(value, str) and value.strip():
            expanded_texts.append(f"- {description}: \"{value.strip()}\"")

    if not expanded_texts:
        return None  # No expanded text to analyze

    system_prompt = """You are an expert in Ayurvedic constitution analysis. Your task is to analyze free-text responses and identify signals of the three doshas:

VATA (Adaptive/Air) signals:
- Variable, changeable, inconsistent patterns
- Anxiety, worry, overthinking, scattered energy
- Creativity, quick thinking, enthusiasm
- Difficulty with routine, irregular patterns
- Cold, dry, light sensations
- Movement, change, flexibility

PITTA (Performance/Fire) signals:
- Intensity, drive, ambition
- Irritability, criticism, perfectionism
- Sharp focus, analytical thinking
- Heat, inflammation, burning out
- Competition, achievement, goals
- Strong opinions, leadership

KAPHA (Conservation/Earth) signals:
- Steadiness, consistency, reliability
- Lethargy, heaviness, slow movement
- Attachment, comfort-seeking, resistance to change
- Nurturing, loyalty, patience
- Accumulation, holding on
- Calm under pressure, endurance

Analyze the text and return a JSON object with adjustment weights for each dosha.
The weights should be between -0.15 and +0.15, representing how much to adjust the baseline computation.
Positive = more of that dosha detected, Negative = less of that dosha detected.

IMPORTANT: Be conservative. Only give significant adjustments when the text clearly indicates dosha patterns.
Most responses should result in small adjustments (-0.05 to +0.05).

Response format:
{
  "vata_adjustment": <float>,
  "pitta_adjustment": <float>,
  "kapha_adjustment": <float>,
  "confidence": <float 0-1>,
  "signals_detected": ["brief list of key signals found"]
}"""

    user_prompt = f"""Analyze these free-text responses from an onboarding questionnaire:

{chr(10).join(expanded_texts)}

Based on these responses, what dosha adjustment weights would you recommend?"""

    try:
        from sakhi.libs.schemas import get_settings
        settings = get_settings()

        result = await router.chat(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            model=settings.model_tool or "gpt-4o-mini",
            response_format={"type": "json_object"}
        )

        result_text = result.text or "{}"
        parsed = json.loads(result_text)

        # Validate and clamp adjustments
        adjustments = {
            "vata": max(-0.15, min(0.15, float(parsed.get("vata_adjustment", 0)))),
            "pitta": max(-0.15, min(0.15, float(parsed.get("pitta_adjustment", 0)))),
            "kapha": max(-0.15, min(0.15, float(parsed.get("kapha_adjustment", 0)))),
        }

        confidence = float(parsed.get("confidence", 0.5))
        signals = parsed.get("signals_detected", [])

        LOGGER.info(f"LLM text analysis: adjustments={adjustments}, confidence={confidence}, signals={signals[:3]}")

        # Scale adjustments by confidence
        return {k: v * confidence for k, v in adjustments.items()}

    except Exception as e:
        LOGGER.warning(f"LLM expanded text analysis failed: {e}")
        return None


def _compute_dosha_with_text_analysis(
    structured_scores: Dict[str, float],
    text_adjustments: Optional[Dict[str, float]]
) -> Dict[str, float]:
    """
    Combine structured dosha scores with LLM text analysis adjustments.

    The text analysis provides fine-tuning based on the user's narrative,
    while the structured scores form the foundation.
    """
    if not text_adjustments:
        return structured_scores

    # Apply adjustments
    adjusted = {
        "vata": structured_scores["vata"] + text_adjustments.get("vata", 0),
        "pitta": structured_scores["pitta"] + text_adjustments.get("pitta", 0),
        "kapha": structured_scores["kapha"] + text_adjustments.get("kapha", 0),
    }

    # Ensure non-negative
    adjusted = {k: max(0, v) for k, v in adjusted.items()}

    # Re-normalize to sum to 1.0
    total = sum(adjusted.values())
    if total > 0:
        adjusted = {k: round(v / total, 2) for k, v in adjusted.items()}
    else:
        adjusted = {"vata": 0.33, "pitta": 0.33, "kapha": 0.34}

    return adjusted


# =============================================================================
# API ENDPOINTS
# =============================================================================

@router.post("/onboarding/assessment", response_model=OperatingSystemResult)
async def submit_assessment(request: AssessmentRequest):
    """
    Submit onboarding assessment quiz and compute Operating System.

    This endpoint:
    1. Takes quiz responses
    2. Computes dosha baseline (prakruti)
    3. Determines Operating System type
    4. Stores in personal_model.operating_system
    5. Returns the computed result
    """
    person_id = request.person_id

    # Compute dosha scores from responses
    dosha_baseline = _compute_dosha_from_responses(request.responses)

    # Determine OS type
    os_type = _determine_os_type(dosha_baseline)
    os_def = OS_TYPE_DEFINITIONS.get(os_type, OS_TYPE_DEFINITIONS["Balanced"])

    # Build operating system data
    operating_system_data = {
        "type": os_type,
        "primary": os_def["primary"],
        "secondary": os_def.get("secondary"),
        "dosha_baseline": dosha_baseline,
        "assessment_responses": [r.model_dump() for r in request.responses],
        "computed_at": datetime.now(timezone.utc).isoformat()
    }

    # Store in database
    try:
        # Ensure person exists in persons table (FK constraint for personal_model)
        await exec(
            """
            INSERT INTO persons (id)
            VALUES ($1)
            ON CONFLICT (id) DO NOTHING
            """,
            person_id
        )

        # Ensure base user/profile rows exist (FK constraints)
        email_row = await q(
            "SELECT email FROM auth_users WHERE id = $1 OR supabase_user_id = $1",
            person_id,
            one=True,
        )
        email = email_row["email"] if isinstance(email_row, dict) and email_row.get("email") else f"{person_id}@placeholder.sakhi"
        LOGGER.info("onboarding v1 upserting users: person_id=%s email=%s", person_id, email)

        await exec(
            """
            INSERT INTO public.users (id, email)
            VALUES ($1, $2)
            ON CONFLICT (id) DO UPDATE SET email = COALESCE(public.users.email, EXCLUDED.email)
            """,
            person_id,
            email
        )

        user_check = await q(
            "SELECT id, email FROM public.users WHERE id = $1",
            person_id,
            one=True,
        )
        LOGGER.info(
            "onboarding v1 users check: person_id=%s exists=%s email=%s",
            person_id,
            bool(user_check),
            user_check.get("email") if user_check else None,
        )

        await exec(
            """
            INSERT INTO profiles (user_id)
            VALUES ($1)
            ON CONFLICT (user_id) DO NOTHING
            """,
            person_id
        )

        # Check if personal_model record exists
        existing = await q(
            "SELECT person_id FROM personal_model WHERE person_id = $1",
            person_id,
            one=True
        )

        if existing:
            # Update existing record
            await exec(
                """
                UPDATE personal_model
                SET operating_system = $2, updated_at = NOW()
                WHERE person_id = $1
                """,
                person_id,
                json.dumps(operating_system_data)
            )
        else:
            # Insert new record
            # Note: personal_model requires 'data' and 'longitudinal_state' (NOT NULL)
            initial_data = {"initialized_from": "assessment"}
            initial_longitudinal = {"layers": {}}
            await exec(
                """
                INSERT INTO personal_model (person_id, data, longitudinal_state, operating_system, updated_at)
                VALUES ($1, $2, $3, $4, NOW())
                """,
                person_id,
                json.dumps(initial_data),
                json.dumps(initial_longitudinal),
                json.dumps(operating_system_data)
            )

        stored = True
    except Exception as e:
        LOGGER.error(f"Failed to store operating system: {e}")
        stored = False

    return OperatingSystemResult(
        operating_system=os_type,
        primary=os_def["primary"],
        secondary=os_def.get("secondary"),
        dosha_baseline=DoshaBaseline(**dosha_baseline),
        stored=stored
    )


@router.post("/onboarding/complete", response_model=FullOnboardingResult)
async def complete_full_onboarding(request: FullOnboardingRequest, req: Request):
    """
    Complete the full onboarding questionnaire (19 questions).

    This endpoint:
    1. Takes all onboarding responses (basics, rhythm, body signals, life context, decisions)
    2. Computes dosha baseline using comprehensive analysis
    3. Analyzes expanded text responses with LLM for additional signals
    4. Determines Operating System type
    5. Extracts life context and decision profile
    6. Stores everything in personal_model
    7. Returns the computed result

    Internal guardrail: These answers describe current tendencies, not identity.
    They are soft constraints and must be overridden by observed behavior over time.
    """
    person_id = request.person_id
    responses = request.responses

    # Compute dosha scores from structured questionnaire answers
    structured_scores = _compute_dosha_from_full_onboarding(responses)

    # Try to enhance with LLM analysis of expanded text fields
    llm_router: LLMRouter | None = getattr(req.app.state, "llm_router", None)
    text_adjustments = None

    if llm_router:
        try:
            text_adjustments = await _analyze_expanded_text_with_llm(llm_router, responses)
            if text_adjustments:
                LOGGER.info(f"Applying LLM text adjustments for {person_id}: {text_adjustments}")
        except Exception as e:
            LOGGER.warning(f"LLM text analysis failed, using structured scores only: {e}")

    # Combine structured scores with text analysis
    dosha_baseline = _compute_dosha_with_text_analysis(structured_scores, text_adjustments)

    # Determine OS type
    os_type = _determine_os_type(dosha_baseline)
    os_def = OS_TYPE_DEFINITIONS.get(os_type, OS_TYPE_DEFINITIONS["Balanced"])

    # Extract life context and decision profile
    life_context = _extract_life_context(responses)
    decision_profile = _extract_decision_profile(responses)

    # Build comprehensive operating system data
    operating_system_data = {
        "type": os_type,
        "primary": os_def["primary"],
        "secondary": os_def.get("secondary"),
        "dosha_baseline": dosha_baseline,
        "computed_at": request.completed_at or datetime.now(timezone.utc).isoformat(),
        # Store all raw responses for potential recomputation
        "onboarding_responses": responses,
        # Guardrail metadata
        "source": "full_onboarding",
        "is_soft_constraint": True,
        "override_by_observation": True,
    }

    # Build full personal model data
    personal_model_data = {
        "operating_system": operating_system_data,
        "life_context": life_context,
        "decision_profile": decision_profile,
        "onboarding_completed_at": request.completed_at,
    }

    # Store in database
    try:
        # Ensure person exists in persons table (FK constraint for personal_model)
        await exec(
            """
            INSERT INTO persons (id)
            VALUES ($1)
            ON CONFLICT (id) DO NOTHING
            """,
            person_id
        )

        # Ensure base user/profile rows exist (FK constraint)
        email_row = await q(
            "SELECT email FROM auth_users WHERE id = $1 OR supabase_user_id = $1",
            person_id,
            one=True,
        )
        email = email_row["email"] if isinstance(email_row, dict) and email_row.get("email") else f"{person_id}@placeholder.sakhi"
        LOGGER.info("onboarding full upserting users: person_id=%s email=%s", person_id, email)

        await exec(
            """
            INSERT INTO public.users (id, email)
            VALUES ($1, $2)
            ON CONFLICT (id) DO UPDATE SET email = COALESCE(public.users.email, EXCLUDED.email)
            """,
            person_id,
            email
        )

        user_check = await q(
            "SELECT id, email FROM public.users WHERE id = $1",
            person_id,
            one=True,
        )
        LOGGER.info(
            "onboarding full users check: person_id=%s exists=%s email=%s",
            person_id,
            bool(user_check),
            user_check.get("email") if user_check else None,
        )

        await exec(
            """
            INSERT INTO profiles (user_id)
            VALUES ($1)
            ON CONFLICT (user_id) DO NOTHING
            """,
            person_id
        )

        existing = await q(
            "SELECT person_id FROM personal_model WHERE person_id = $1",
            person_id,
            one=True
        )

        if existing:
            # Update existing record
            await exec(
                """
                UPDATE personal_model
                SET
                    operating_system = $2,
                    life_context = $3,
                    decision_profile = $4,
                    updated_at = NOW()
                WHERE person_id = $1
                """,
                person_id,
                json.dumps(operating_system_data),
                json.dumps(life_context),
                json.dumps(decision_profile)
            )
        else:
            # Insert new record
            # Note: personal_model requires 'data' and 'longitudinal_state' (NOT NULL)
            initial_data = {"initialized_from": "onboarding"}
            initial_longitudinal = {"layers": {}}
            await exec(
                """
                INSERT INTO personal_model (
                    person_id,
                    data,
                    longitudinal_state,
                    operating_system,
                    life_context,
                    decision_profile,
                    updated_at
                )
                VALUES ($1, $2, $3, $4, $5, $6, NOW())
                """,
                person_id,
                json.dumps(initial_data),
                json.dumps(initial_longitudinal),
                json.dumps(operating_system_data),
                json.dumps(life_context),
                json.dumps(decision_profile)
            )

        stored = True
        LOGGER.info(f"Full onboarding completed for {person_id}: OS={os_type}")
    except Exception as e:
        LOGGER.error(f"Failed to store onboarding data: {e}")
        stored = False

    return FullOnboardingResult(
        operating_system=os_type,
        primary=os_def["primary"],
        secondary=os_def.get("secondary"),
        dosha_baseline=DoshaBaseline(**dosha_baseline),
        life_context=life_context,
        decision_profile=decision_profile,
        stored=stored
    )


@router.get("/profile/operating-system/{person_id}", response_model=OperatingSystemProfile)
async def get_operating_system(person_id: str):
    """
    Retrieve the user's Operating System profile.

    Returns the stored constitutional type with full descriptions,
    strengths, vulnerabilities, and traits.
    """
    row = await q(
        """
        SELECT operating_system
        FROM personal_model
        WHERE person_id = $1
        """,
        person_id,
        one=True
    )

    if not row or not row.get("operating_system"):
        raise HTTPException(
            status_code=404,
            detail="Operating System not found. Complete onboarding assessment first."
        )

    os_data = row["operating_system"]
    if isinstance(os_data, str):
        os_data = json.loads(os_data)

    os_type = os_data.get("type", "Balanced")
    os_def = OS_TYPE_DEFINITIONS.get(os_type, OS_TYPE_DEFINITIONS["Balanced"])

    dosha_baseline = os_data.get("dosha_baseline", {"vata": 0.33, "pitta": 0.33, "kapha": 0.34})

    return OperatingSystemProfile(
        operating_system=os_type,
        primary=os_def["primary"],
        secondary=os_def.get("secondary"),
        dosha_baseline=DoshaBaseline(**dosha_baseline),
        description=os_def["description"],
        strengths=os_def["strengths"],
        vulnerabilities=os_def["vulnerabilities"],
        traits=os_def["traits"]
    )


@router.get("/state/current/{person_id}", response_model=CurrentStateResponse)
async def get_current_state(person_id: str):
    """
    Get the user's current state compared to their baseline.

    Returns:
    - Operating Mode (from gunas: Clarity/Activation/Recovery)
    - Friction State (from dosha drift: Chaos/Intensity/Stagnation)
    - Baseline Drift (percentage deviation from prakruti)
    - Current dosha vector
    """
    # Get baseline operating system
    os_row = await q(
        """
        SELECT operating_system
        FROM personal_model
        WHERE person_id = $1
        """,
        person_id,
        one=True
    )

    if not os_row or not os_row.get("operating_system"):
        raise HTTPException(
            status_code=404,
            detail="Operating System not found. Complete onboarding assessment first."
        )

    os_data = os_row["operating_system"]
    if isinstance(os_data, str):
        os_data = json.loads(os_data)

    baseline_dosha = os_data.get("dosha_baseline", {"vata": 0.33, "pitta": 0.33, "kapha": 0.34})

    # Get recent entries to compute current state (last 7 days)
    entries = await q(
        """
        SELECT state_vector, guna_vector, created_at
        FROM memory_episodic
        WHERE person_id = $1
          AND created_at > NOW() - INTERVAL '7 days'
        ORDER BY created_at DESC
        LIMIT 50
        """,
        person_id
    )

    # Compute current dosha from recent entries
    if entries:
        current_dosha = {"vata": 0.0, "pitta": 0.0, "kapha": 0.0}
        current_guna = {"sattva": 0.0, "rajas": 0.0, "tamas": 0.0}
        dosha_count = 0
        guna_count = 0

        for entry in entries:
            state_vec = entry.get("state_vector")
            if state_vec:
                if isinstance(state_vec, str):
                    state_vec = json.loads(state_vec)
                dosha = state_vec.get("dosha", {})
                if dosha:
                    current_dosha["vata"] += dosha.get("vata", 0)
                    current_dosha["pitta"] += dosha.get("pitta", 0)
                    current_dosha["kapha"] += dosha.get("kapha", 0)
                    dosha_count += 1

            guna_vec = entry.get("guna_vector")
            if guna_vec:
                if isinstance(guna_vec, str):
                    guna_vec = json.loads(guna_vec)
                current_guna["sattva"] += guna_vec.get("sattva", 0)
                current_guna["rajas"] += guna_vec.get("rajas", 0)
                current_guna["tamas"] += guna_vec.get("tamas", 0)
                guna_count += 1

        if dosha_count > 0:
            current_dosha = {k: round(v / dosha_count, 2) for k, v in current_dosha.items()}
        else:
            current_dosha = dict(baseline_dosha)

        if guna_count > 0:
            current_guna = {k: round(v / guna_count, 2) for k, v in current_guna.items()}
        else:
            current_guna = {"sattva": 0.5, "rajas": 0.3, "tamas": 0.2}
    else:
        # No recent data - assume baseline
        current_dosha = dict(baseline_dosha)
        current_guna = {"sattva": 0.5, "rajas": 0.3, "tamas": 0.2}

    # Determine operating mode
    mode = _determine_operating_mode(current_guna)
    mode_def = OPERATING_MODES.get(mode, OPERATING_MODES["Clarity"])

    # Classify friction state
    friction_state = _classify_friction_state(current_dosha, baseline_dosha)

    # Calculate baseline drift
    drift = _calculate_baseline_drift(current_dosha, baseline_dosha)

    # Build friction state detail
    if friction_state:
        friction_config = FRICTION_STATE_CONFIG.get(friction_state, {})
        friction_detail = FrictionStateDetail(
            state=friction_state,
            dosha_elevated=friction_config.get("dosha"),
            severity="moderate" if drift["percentage"] < 40 else "high",
            description=f"Your {OS_TYPE_DEFINITIONS.get(os_data.get('type', 'Balanced'), {}).get('primary', 'Adaptive')} side is amplified"
        )
    else:
        friction_detail = FrictionStateDetail(
            state=None,
            dosha_elevated=None,
            severity="low",
            description="You're operating close to your natural baseline"
        )

    # Build drift description
    if drift["primary_contributor"]:
        dosha_name = drift["primary_contributor"].title()
        drift_desc = f"{dosha_name} {'elevated' if drift['direction'] == 'elevated' else 'depleted'}"
    else:
        drift_desc = "Stable and balanced"

    return CurrentStateResponse(
        timestamp=datetime.now(timezone.utc).isoformat(),
        operating_mode=OperatingModeDetail(
            mode=mode,
            guna_dominant=mode_def["guna"],
            guna_scores=GunaScores(**current_guna),
            description=mode_def["description"]
        ),
        friction_state=friction_detail,
        baseline_drift=BaselineDriftDetail(
            percentage=drift["percentage"],
            direction=drift["direction"],
            primary_contributor=drift["primary_contributor"],
            description=drift_desc
        ),
        current_dosha=CurrentDoshaState(**current_dosha)
    )


@router.get("/state/friction-state/{person_id}", response_model=FrictionStateResponse)
async def get_friction_state(person_id: str):
    """
    Get just the user's current friction state.

    Simplified endpoint that returns:
    - Friction state name (or None if balanced)
    - Color for UI
    - Elevated dosha
    - Severity
    - When this state began
    """
    try:
        state = await get_current_state(person_id)
        friction = state.friction_state

        color = "#47e887"  # Green for balanced
        if friction.state:
            color = FRICTION_STATE_CONFIG.get(friction.state, {}).get("color", "#47e887")

        return FrictionStateResponse(
            friction_state=friction.state,
            friction_color=color,
            dosha_elevated=friction.dosha_elevated,
            severity=friction.severity,
            since=None  # TODO: Track when friction state began
        )
    except HTTPException:
        raise
    except Exception as e:
        LOGGER.error(f"Error getting friction state: {e}")
        return FrictionStateResponse(
            friction_state=None,
            friction_color="#47e887",
            dosha_elevated=None,
            severity="unknown",
            since=None
        )


async def _generate_llm_recommendations(
    router: LLMRouter,
    person_id: str,
    os_type: str,
    os_primary: str,
    friction_state: Optional[str],
    operating_mode: str,
    drift_percentage: float,
    recent_patterns: List[str],
) -> Dict[str, Any]:
    """
    Generate personalized recommendations using LLM.

    The LLM receives context about the user's:
    - Operating System (constitutional type)
    - Current friction state
    - Operating mode
    - Baseline drift
    - Recent patterns from their entries

    Returns structured recommendations with actions, rationale, and pattern insights.
    """

    # Build context-rich system prompt
    system_prompt = """You are Sakhi, a wise wellness companion grounded in Ayurvedic wisdom but speaking in modern, accessible language.

Your role is to provide personalized, actionable recommendations based on the user's current state.

IMPORTANT CONTEXT:
- "Operating System" = their constitutional type (like Adaptive, Performance, Conservation)
- "Friction State" = what's creating resistance (Chaos = scattered, Intensity = burnout, Stagnation = stuck)
- "Operating Mode" = how they're running (Clarity = balanced, Activation = high energy, Recovery = rest needed)

Your recommendations should:
1. Be immediately actionable (things they can do in the next few minutes to hours)
2. Address the ROOT CAUSE of their friction, not just symptoms
3. Be specific to their Operating System type
4. Feel warm but practical, not preachy

RESPONSE FORMAT (JSON):
{
  "recommendations": [
    {
      "action": "Clear, specific action in imperative form",
      "why": "Brief explanation of why this helps (1 sentence)",
      "category": "immediate|today|this_week",
      "icon": "breath|movement|drink|food|rest|focus|connect|nature|clock|heart"
    }
  ],
  "pattern_insight": {
    "pattern": "What pattern you notice in their state",
    "suggestion": "One specific thing to try"
  },
  "encouragement": "One warm, brief sentence acknowledging their state"
}

Provide exactly 3 recommendations. Be specific, not generic."""

    # Build user context
    friction_context = f"Currently experiencing {friction_state}" if friction_state else "Currently balanced with no major friction"

    pattern_context = ""
    if recent_patterns:
        pattern_context = f"\nRecent patterns observed: {', '.join(recent_patterns[:5])}"

    user_prompt = f"""User Profile:
- Operating System: {os_type} (primary: {os_primary})
- Current Mode: {operating_mode}
- Friction State: {friction_context}
- Baseline Drift: {drift_percentage}% from their natural state
{pattern_context}

Based on this profile, what 3 specific actions would help them right now?"""

    try:
        from sakhi.libs.schemas import get_settings
        settings = get_settings()

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        response = await router.chat(
            messages=messages,
            model=settings.model_tool or "gpt-4o-mini",
            response_format={"type": "json_object"}
        )

        result_text = response.text or "{}"

        # Parse the JSON response
        try:
            result = json.loads(result_text)
            return result
        except json.JSONDecodeError:
            LOGGER.warning(f"Failed to parse LLM response as JSON: {result_text[:200]}")
            return None

    except Exception as e:
        LOGGER.error(f"LLM recommendation generation failed: {e}")
        return None


def _get_fallback_recommendations(friction_state: Optional[str]) -> Dict[str, Any]:
    """Return rule-based recommendations when LLM is unavailable."""

    if friction_state:
        config = FRICTION_STATE_CONFIG.get(friction_state, {})
        return {
            "recommendations": config.get("recommendations", []),
            "pattern_insight": config.get("pattern_insight"),
            "encouragement": f"You're experiencing {friction_state}. These practices can help restore balance."
        }
    else:
        return {
            "recommendations": [
                {
                    "action": "Maintain your current rhythm",
                    "why": "You're in a good flow state",
                    "category": "maintenance",
                    "icon": "check"
                },
                {
                    "action": "Brief gratitude reflection",
                    "why": "Reinforces positive patterns",
                    "category": "maintenance",
                    "icon": "heart"
                },
                {
                    "action": "Plan tomorrow's priorities",
                    "why": "Leverage your clarity for future planning",
                    "category": "maintenance",
                    "icon": "plan"
                }
            ],
            "pattern_insight": {
                "pattern": "Your balanced state supports decision-making",
                "suggestion": "This is a good time for important choices"
            },
            "encouragement": "You're in a balanced state. This is a great foundation."
        }


@router.get("/recommendations/now/{person_id}", response_model=RecommendationsResponse)
async def get_recommendations(person_id: str, request: Request):
    """
    Get context-aware, LLM-powered recommendations for the current state.

    Returns personalized recommendations based on:
    - Current friction state
    - Operating system type
    - Operating mode
    - Baseline drift
    - Pattern insights from history

    Falls back to rule-based recommendations if LLM is unavailable.
    """
    try:
        # Get current state
        state = await get_current_state(person_id)
        friction_state = state.friction_state.state
        operating_mode = state.operating_mode.mode
        drift_percentage = state.baseline_drift.percentage

        # Get operating system info
        os_row = await q(
            """
            SELECT operating_system
            FROM personal_model
            WHERE person_id = $1
            """,
            person_id,
            one=True
        )

        os_type = "Balanced"
        os_primary = "Balanced"
        if os_row and os_row.get("operating_system"):
            os_data = os_row["operating_system"]
            if isinstance(os_data, str):
                os_data = json.loads(os_data)
            os_type = os_data.get("type", "Balanced")
            os_primary = os_data.get("primary", "Balanced")

        # Get recent patterns from entries
        recent_entries = await q(
            """
            SELECT content, soul_shadow, soul_light
            FROM memory_episodic
            WHERE person_id = $1
              AND created_at > NOW() - INTERVAL '7 days'
            ORDER BY created_at DESC
            LIMIT 10
            """,
            person_id
        )

        recent_patterns = []
        for entry in recent_entries:
            shadows = entry.get("soul_shadow") or []
            lights = entry.get("soul_light") or []
            recent_patterns.extend(shadows[:2])
            recent_patterns.extend(lights[:2])

        # Try LLM-powered recommendations first
        llm_router: LLMRouter | None = getattr(request.app.state, "llm_router", None)

        llm_result = None
        if llm_router:
            llm_result = await _generate_llm_recommendations(
                router=llm_router,
                person_id=person_id,
                os_type=os_type,
                os_primary=os_primary,
                friction_state=friction_state,
                operating_mode=operating_mode,
                drift_percentage=drift_percentage,
                recent_patterns=list(set(recent_patterns))[:5]
            )

        # Use LLM result or fall back to rules
        if llm_result and llm_result.get("recommendations"):
            recommendations = [
                RecommendationItem(
                    action=rec.get("action", "Take a moment to breathe"),
                    why=rec.get("why", "Helps restore balance"),
                    category=rec.get("category", "immediate"),
                    icon=rec.get("icon", "breath")
                )
                for rec in llm_result.get("recommendations", [])[:3]
            ]

            pattern_data = llm_result.get("pattern_insight")
            pattern_insight = PatternInsight(
                pattern=pattern_data.get("pattern", ""),
                suggestion=pattern_data.get("suggestion", "")
            ) if pattern_data else None

            source = "llm"
        else:
            # Fallback to rule-based
            fallback = _get_fallback_recommendations(friction_state)
            recommendations = [
                RecommendationItem(**rec)
                for rec in fallback.get("recommendations", [])[:3]
            ]
            pattern_data = fallback.get("pattern_insight")
            pattern_insight = PatternInsight(**pattern_data) if pattern_data else None
            source = "rules"

        LOGGER.info(f"Generated recommendations for {person_id} using {source}")

        return RecommendationsResponse(
            timestamp=datetime.now(timezone.utc).isoformat(),
            friction_state=friction_state,
            recommendations=recommendations,
            pattern_insight=pattern_insight
        )
    except HTTPException:
        raise
    except Exception as e:
        LOGGER.error(f"Error getting recommendations: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate recommendations")


async def _generate_weekly_insight_llm(
    router: LLMRouter,
    os_type: str,
    friction_state: Optional[str],
    coherence_score: float,
    days_with_entries: int,
    dominant_modes: List[str],
) -> Optional[str]:
    """Generate a personalized weekly insight using LLM."""

    system_prompt = """You are Sakhi, a warm wellness companion. Generate a brief, personalized weekly insight.

Keep it:
- 1-2 sentences max
- Warm but practical
- Specific to their patterns
- Forward-looking with hope

Do NOT:
- Be preachy or lecture
- Use clinical language
- Be vague or generic"""

    mode_summary = ""
    if dominant_modes:
        mode_counts = {}
        for m in dominant_modes:
            mode_counts[m] = mode_counts.get(m, 0) + 1
        most_common = max(mode_counts, key=mode_counts.get) if mode_counts else "varied"
        mode_summary = f"Most common mode this week: {most_common}"

    user_prompt = f"""Weekly summary:
- Operating System: {os_type}
- Days reflected: {days_with_entries}/7
- Coherence score: {coherence_score}%
- Current friction: {friction_state or 'None - balanced'}
- {mode_summary}

Write a brief, encouraging weekly insight."""

    try:
        from sakhi.libs.schemas import get_settings
        settings = get_settings()

        response = await router.chat(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            model=settings.model_chat or "gpt-4o-mini"
        )

        return (response.text or "").strip()
    except Exception as e:
        LOGGER.warning(f"Failed to generate weekly insight: {e}")
        return None


@router.get("/state/weekly/{person_id}", response_model=WeeklyStateResponse)
async def get_weekly_state(person_id: str, request: Request):
    """
    Get weekly state summary for the home screen.

    Returns:
    - Coherence score (from soul analytics)
    - Day-by-day data
    - Dominant friction state for the week
    - Weekly insight
    """
    # Calculate week boundaries
    today = datetime.now(timezone.utc).date()
    week_start = today - timedelta(days=today.weekday())

    # Get entries for this week
    entries = await q(
        """
        SELECT
            DATE(created_at) as entry_date,
            state_vector,
            guna_vector
        FROM memory_episodic
        WHERE person_id = $1
          AND created_at >= $2
        ORDER BY created_at
        """,
        person_id,
        datetime.combine(week_start, datetime.min.time())
    )

    # Build day-by-day data
    days = []
    entry_dates = set()
    day_modes: Dict[str, List[str]] = {}

    for entry in entries:
        entry_date = entry.get("entry_date")
        if entry_date:
            date_str = entry_date.isoformat() if hasattr(entry_date, 'isoformat') else str(entry_date)
            entry_dates.add(date_str)

            # Compute mode for this entry
            guna_vec = entry.get("guna_vector")
            if guna_vec:
                if isinstance(guna_vec, str):
                    guna_vec = json.loads(guna_vec)
                mode = _determine_operating_mode(guna_vec)
                if date_str not in day_modes:
                    day_modes[date_str] = []
                day_modes[date_str].append(mode)

    # Generate 7-day grid
    for i in range(7):
        day = week_start + timedelta(days=i)
        day_str = day.isoformat()
        has_entry = day_str in entry_dates

        # Determine dominant mode for the day
        dominant_mode = None
        if day_str in day_modes and day_modes[day_str]:
            mode_counts = {}
            for m in day_modes[day_str]:
                mode_counts[m] = mode_counts.get(m, 0) + 1
            dominant_mode = max(mode_counts, key=mode_counts.get)

        days.append(DayData(
            date=day_str,
            has_entry=has_entry,
            dominant_mode=dominant_mode
        ))

    # Calculate coherence from soul summary
    try:
        soul_summary = await q(
            """
            SELECT soul_shadow, soul_light
            FROM memory_episodic
            WHERE person_id = $1
            ORDER BY updated_at DESC
            LIMIT 50
            """,
            person_id
        )

        shadows = []
        lights = []
        for row in soul_summary:
            shadows.extend(row.get("soul_shadow") or [])
            lights.extend(row.get("soul_light") or [])

        shadow_count = len(set(shadows))
        light_count = len(set(lights))

        if shadow_count + light_count > 0:
            coherence_score = round((light_count / (shadow_count + light_count)) * 100, 0)
        else:
            coherence_score = 50.0
    except Exception:
        coherence_score = 50.0

    # Get dominant friction for week
    try:
        state = await get_current_state(person_id)
        friction_state = state.friction_state.state
        friction_days = len([d for d in days if d.has_entry])
    except Exception:
        friction_state = None
        friction_days = 0

    # Get OS type for insight
    os_row = await q(
        """
        SELECT operating_system
        FROM personal_model
        WHERE person_id = $1
        """,
        person_id,
        one=True
    )
    os_type = "Balanced"
    if os_row and os_row.get("operating_system"):
        os_data = os_row["operating_system"]
        if isinstance(os_data, str):
            os_data = json.loads(os_data)
        os_type = os_data.get("type", "Balanced")

    # Generate weekly insight (try LLM first, fall back to rules)
    llm_router: LLMRouter | None = getattr(request.app.state, "llm_router", None)

    # Collect dominant modes for insight
    all_modes = []
    for d in days:
        if d.dominant_mode:
            all_modes.append(d.dominant_mode)

    insight = None
    if llm_router:
        insight = await _generate_weekly_insight_llm(
            router=llm_router,
            os_type=os_type,
            friction_state=friction_state,
            coherence_score=coherence_score,
            days_with_entries=friction_days,
            dominant_modes=all_modes
        )

    # Fallback to rule-based insight
    if not insight:
        if friction_state:
            insight = f"Your {os_type} system is showing {friction_state}. Consider grounding practices this week."
        elif friction_days > 0:
            insight = f"You've been consistent with {friction_days} reflections this week. Keep the momentum!"
        else:
            insight = "Start your week with a brief reflection to establish your rhythm."

    return WeeklyStateResponse(
        week_start=week_start.isoformat(),
        coherence_score=coherence_score,
        coherence_trend="stable",  # TODO: Compare with previous week
        days=days,
        dominant_friction=DominantFriction(
            state=friction_state,
            days_count=friction_days,
            description=f"{friction_days} of 7 days showing {friction_state or 'balanced state'}"
        ),
        weekly_insight=insight
    )


# =============================================================================
# CONSTITUTION-BASED RECOMMENDATIONS (No DB user required)
# For demo/simulation purposes - takes prakruti directly
# =============================================================================

class ConstitutionRecommendationRequest(BaseModel):
    """Request for constitution-based recommendations."""
    vata: float = Field(ge=0, le=1, description="Vata percentage (0-1)")
    pitta: float = Field(ge=0, le=1, description="Pitta percentage (0-1)")
    kapha: float = Field(ge=0, le=1, description="Kapha percentage (0-1)")
    symptom: str = Field(description="Current symptom or concern")


class RecommendationDetails(BaseModel):
    """Details for a recommendation (what, when, how)."""
    what: str = ""
    when: str = ""
    how: str = ""


class ConstitutionRecommendation(BaseModel):
    """A single constitution-based recommendation."""
    action: str
    details: Optional[RecommendationDetails] = None
    why: str = ""
    category: str = "immediate"


class ConstitutionRecommendationResponse(BaseModel):
    """Response with LLM-generated recommendations."""
    constitution: Dict[str, Any]
    friction_state: str
    recommendations: List[ConstitutionRecommendation]
    pattern_insight: Optional[Dict[str, str]] = None
    source: str = Field(description="'llm' or 'rules'")


@router.post("/recommendations/by-constitution", response_model=ConstitutionRecommendationResponse)
async def get_recommendations_by_constitution(
    request_data: ConstitutionRecommendationRequest,
    request: Request,
):
    """
    Get personalized recommendations based on constitution (prakruti) without requiring a user in DB.

    This endpoint is designed for demo/simulation purposes where we want to show
    how different constitutions get different recommendations for the same symptom.

    The LLM generates personalized advice based on:
    - The user's constitutional type (dominant dosha)
    - Their current symptom
    - Ayurvedic principles for balancing that dosha
    """
    vata = request_data.vata
    pitta = request_data.pitta
    kapha = request_data.kapha
    symptom = request_data.symptom

    # Determine dominant dosha
    doshas = {"vata": vata, "pitta": pitta, "kapha": kapha}
    dominant = max(doshas, key=doshas.get)
    sorted_doshas = sorted(doshas.items(), key=lambda x: x[1], reverse=True)
    secondary = sorted_doshas[1][0]

    # Map dosha to Operating System type
    os_type_map = {
        "vata": "Adaptive",
        "pitta": "Performance",
        "kapha": "Conservation",
    }
    os_type = os_type_map[dominant]

    # Map dosha to friction state when imbalanced
    friction_map = {
        "vata": "Chaos Friction",
        "pitta": "Intensity Friction",
        "kapha": "Stagnation Friction",
    }
    friction_state = friction_map[dominant]

    # Try LLM-based generation
    llm_router: LLMRouter | None = getattr(request.app.state, "llm_router", None)

    if llm_router:
        try:
            llm_result = await _generate_constitution_recommendations_llm(
                router=llm_router,
                os_type=os_type,
                dominant_dosha=dominant,
                secondary_dosha=secondary,
                friction_state=friction_state,
                symptom=symptom,
                prakruti=doshas,
            )

            if llm_result and llm_result.get("recommendations"):
                return ConstitutionRecommendationResponse(
                    constitution={
                        "dominant": dominant,
                        "secondary": secondary,
                        "type": f"{os_type}-{os_type_map[secondary]}",
                        "vata": vata,
                        "pitta": pitta,
                        "kapha": kapha,
                    },
                    friction_state=friction_state,
                    recommendations=llm_result.get("recommendations", []),
                    pattern_insight=llm_result.get("pattern_insight"),
                    source="llm",
                )
        except Exception as e:
            LOGGER.warning(f"LLM generation failed, falling back to rules: {e}")

    # Fallback to rule-based recommendations
    fallback = _get_constitution_fallback_recommendations(dominant, symptom)

    return ConstitutionRecommendationResponse(
        constitution={
            "dominant": dominant,
            "secondary": secondary,
            "type": f"{os_type}-{os_type_map[secondary]}",
            "vata": vata,
            "pitta": pitta,
            "kapha": kapha,
        },
        friction_state=friction_state,
        recommendations=fallback.get("recommendations", []),
        pattern_insight=fallback.get("pattern_insight"),
        source="rules",
    )


async def _generate_constitution_recommendations_llm(
    router: LLMRouter,
    os_type: str,
    dominant_dosha: str,
    secondary_dosha: str,
    friction_state: str,
    symptom: str,
    prakruti: Dict[str, float],
) -> Dict[str, Any]:
    """
    Generate personalized recommendations using LLM based on constitution.

    This is similar to _generate_llm_recommendations but doesn't require
    a user in the database - it works directly from prakruti percentages.
    """

    system_prompt = """You are Sakhi, a wise wellness companion grounded in Ayurvedic wisdom but speaking in modern, accessible language.

Your role is to provide personalized, DETAILED and ACTIONABLE recommendations based on someone's constitutional type (prakruti).

IMPORTANT AYURVEDIC CONTEXT:
- Vata (Adaptive) = Air/Space. When imbalanced: scattered, anxious, cold, dry. Balance with: warmth, grounding, routine, moisture.
- Pitta (Performance) = Fire/Water. When imbalanced: irritable, inflamed, overheated, intense. Balance with: cooling, moderation, play, surrender.
- Kapha (Conservation) = Earth/Water. When imbalanced: sluggish, stuck, heavy, unmotivated. Balance with: stimulation, movement, lightness, novelty.

CRITICAL: The SAME SYMPTOM needs OPPOSITE treatments depending on constitution:
- "Feeling tired" for Pitta = COOL DOWN (they're burnt out from excess fire)
- "Feeling tired" for Kapha = WARM UP and MOVE (they're sluggish from stagnation)
- "Feeling tired" for Vata = GROUND and REST (they're depleted from scattered energy)

RESPONSE FORMAT (JSON) - Keep responses CONCISE:
{
  "recommendations": [
    {
      "action": "Brief action summary (5-10 words)",
      "details": {
        "what": "Specific items (e.g., 'peppermint tea with honey')",
        "when": "Timing (e.g., 'mid-afternoon, 3-4pm')",
        "how": "Method in 1-2 sentences (e.g., 'Steep 5 min, sip slowly away from desk')"
      },
      "why": "1 sentence connecting to their dosha",
      "category": "immediate"
    }
  ],
  "pattern_insight": {
    "pattern": "Brief insight (1 sentence)",
    "suggestion": "One practice (1 sentence)"
  }
}

REQUIRED - Every recommendation MUST include "details" with what/when/how. Keep each field BRIEF (under 20 words).

Provide exactly 3 recommendations. Be SPECIFIC to their constitution."""

    dosha_percentages = f"Vata: {prakruti['vata']*100:.0f}%, Pitta: {prakruti['pitta']*100:.0f}%, Kapha: {prakruti['kapha']*100:.0f}%"

    user_prompt = f"""Constitution Profile:
- Operating System: {os_type} (Primary: {dominant_dosha.title()}, Secondary: {secondary_dosha.title()})
- Dosha Balance: {dosha_percentages}
- Current Symptom: "{symptom}"
- Expected Friction: {friction_state}

Based on this {dominant_dosha.title()}-dominant constitution experiencing "{symptom}", what 3 specific actions would help them right now?

Remember: This is a {dominant_dosha.title()} type, so recommendations should address the ROOT CAUSE for their constitution, not generic advice."""

    try:
        from sakhi.libs.schemas import get_settings
        settings = get_settings()

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        response = await router.chat(
            messages=messages,
            model=settings.model_chat or "gpt-4o-mini",
            response_format={"type": "json_object"},
            max_tokens=1500,  # Ensure complete JSON response
        )

        if response.text:
            LOGGER.debug(f"LLM constitution response (first 500 chars): {response.text[:500]}")
            result = json.loads(response.text)

            # Validate and clean up recommendations array
            # Sometimes LLM returns malformed JSON where pattern_insight leaks into recommendations
            if "recommendations" in result and isinstance(result["recommendations"], list):
                valid_recommendations = []
                for rec in result["recommendations"]:
                    # Only keep entries that are proper dicts with an 'action' key
                    if isinstance(rec, dict) and "action" in rec:
                        # Ensure required fields have defaults
                        rec.setdefault("why", "")
                        rec.setdefault("category", "immediate")
                        # Validate details structure
                        if "details" in rec and isinstance(rec["details"], dict):
                            rec["details"].setdefault("what", "")
                            rec["details"].setdefault("when", "")
                            rec["details"].setdefault("how", "")
                        valid_recommendations.append(rec)
                    else:
                        LOGGER.warning(f"Skipping invalid recommendation entry: {str(rec)[:100]}")

                result["recommendations"] = valid_recommendations

                if not valid_recommendations:
                    LOGGER.warning("No valid recommendations found in LLM response")
                    return {}

                LOGGER.info(f"Validated {len(valid_recommendations)} recommendations from LLM")

            return result
        return {}

    except json.JSONDecodeError as e:
        LOGGER.error(f"LLM constitution recommendation JSON parse failed: {e}")
        return {}
    except Exception as e:
        LOGGER.error(f"LLM constitution recommendation failed: {e}")
        return {}


def _get_constitution_fallback_recommendations(
    dominant_dosha: str,
    symptom: str,
) -> Dict[str, Any]:
    """
    Rule-based fallback recommendations when LLM is unavailable.
    """

    # Symptom-specific recommendations by dosha
    recommendations_by_dosha = {
        "vata": {
            "tired": [
                {"action": "Drink warm ginger tea and wrap yourself in a cozy blanket", "why": "Vata types get depleted and cold when tired. Warmth restores your energy without overstimulating.", "category": "immediate"},
                {"action": "Do 5 minutes of slow, grounding stretches", "why": "Gentle movement brings scattered Vata energy back to center.", "category": "immediate"},
                {"action": "Take a warm bath with sesame oil", "why": "Oil and warmth are the antidotes to Vata depletion.", "category": "today"},
            ],
            "anxious": [
                {"action": "Drink warm milk with nutmeg and honey", "why": "Vata anxiety is airy and cold. Warm, heavy drinks calm the nervous system.", "category": "immediate"},
                {"action": "Do slow yoga poses held for 10+ breaths", "why": "Slow, grounded movement counters Vata's scattered energy.", "category": "immediate"},
                {"action": "Use a weighted blanket or firm pressure massage", "why": "Heaviness grounds Vata's light, airy nature.", "category": "today"},
            ],
            "default": [
                {"action": "Establish a warm, consistent routine", "why": "Vata thrives on regularity - it counters their naturally variable nature.", "category": "immediate"},
                {"action": "Favor warm, cooked foods over raw or cold", "why": "Warm food balances Vata's cold, dry qualities.", "category": "today"},
                {"action": "Go to bed by 10pm in a warm room", "why": "Regular sleep is medicine for Vata.", "category": "today"},
            ],
        },
        "pitta": {
            "tired": [
                {"action": "Take a 10-minute break in shade or cool room", "why": "Pitta fatigue is often burnout from excess fire. Cooling restores balance.", "category": "immediate"},
                {"action": "Drink coconut water or cool mint tea", "why": "Cooling drinks reduce the heat that's depleting you.", "category": "immediate"},
                {"action": "Splash cool water on your face and wrists", "why": "Pitta runs hot - cooling the pulse points rapidly reduces heat.", "category": "immediate"},
            ],
            "anxious": [
                {"action": "Make a short to-do list and tackle ONE task", "why": "Pitta anxiety comes from feeling out of control. Structure restores confidence.", "category": "immediate"},
                {"action": "Take 3 deep breaths, then reward yourself after the task", "why": "Pitta needs quick wins - they're goal-oriented by nature.", "category": "immediate"},
                {"action": "Go for a walk in nature, away from screens", "why": "Nature cools Pitta's intensity and reminds them life isn't all work.", "category": "today"},
            ],
            "default": [
                {"action": "Avoid intense exercise during the heat of the day", "why": "Pitta already runs hot - adding more heat leads to burnout.", "category": "immediate"},
                {"action": "Favor cooling foods: cucumber, coconut, leafy greens", "why": "Cool foods balance Pitta's natural fire.", "category": "today"},
                {"action": "Schedule play time - not everything needs to be productive", "why": "Pitta's intensity needs regular release through play.", "category": "today"},
            ],
        },
        "kapha": {
            "tired": [
                {"action": "Take a brisk 15-minute walk outside", "why": "Kapha fatigue is stagnation - movement activates circulation and lifts heaviness.", "category": "immediate"},
                {"action": "Drink stimulating chai with ginger and black pepper", "why": "Warming spices counter Kapha's cold, heavy nature.", "category": "immediate"},
                {"action": "Do 5 minutes of vigorous breathwork (kapalabhati)", "why": "Energizing breath clears Kapha's mental fog.", "category": "immediate"},
            ],
            "anxious": [
                {"action": "Change your environment - go somewhere new", "why": "Kapha anxiety is heavy and stuck. Fresh perspectives release stagnant worry.", "category": "immediate"},
                {"action": "Call a friend and talk it out", "why": "Connection moves Kapha's stuck energy.", "category": "immediate"},
                {"action": "Do dynamic stretches or dance for 5 minutes", "why": "Movement is the best medicine for Kapha's heavy anxiety.", "category": "immediate"},
            ],
            "default": [
                {"action": "Wake with the sun and avoid daytime naps", "why": "Kapha needs stimulation - sleeping too much increases sluggishness.", "category": "immediate"},
                {"action": "Favor light, spicy, warm foods over heavy, cold ones", "why": "Light food counters Kapha's heavy digestion.", "category": "today"},
                {"action": "Try something new each day to break routine", "why": "Novelty combats Kapha's tendency toward stagnation.", "category": "today"},
            ],
        },
    }

    # Determine symptom category
    symptom_lower = symptom.lower()
    symptom_key = "default"
    if "tired" in symptom_lower or "energy" in symptom_lower or "fatigue" in symptom_lower:
        symptom_key = "tired"
    elif "anxious" in symptom_lower or "scatter" in symptom_lower or "worry" in symptom_lower:
        symptom_key = "anxious"

    recs = recommendations_by_dosha.get(dominant_dosha, {}).get(symptom_key, recommendations_by_dosha[dominant_dosha]["default"])

    # Pattern insight
    pattern_insights = {
        "vata": {
            "pattern": "Vata types often feel depleted when they've been too scattered or skipped routines",
            "suggestion": "Establish anchor points in your day: same wake time, same meal times, same wind-down routine"
        },
        "pitta": {
            "pattern": "Pitta types often burn out from pushing too hard without cooling breaks",
            "suggestion": "Schedule mandatory 'non-productive' time - your body needs it even if your mind disagrees"
        },
        "kapha": {
            "pattern": "Kapha types often feel stuck when they've been too sedentary or comfortable",
            "suggestion": "Introduce small challenges daily - your body thrives on being gently pushed"
        },
    }

    return {
        "recommendations": recs,
        "pattern_insight": pattern_insights.get(dominant_dosha),
    }
