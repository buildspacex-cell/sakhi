"""
Diagnostic Knowledge Base

Contains symptom-specific diagnostic trees with:
- Constitution-specific questions (prioritized by dosha)
- Memory queries to search for
- State signals to check
- Constitution-specific guidance for responses

This is the "Ayurvedic practitioner knowledge" that helps Sakhi
ask targeted questions based on the user's constitution.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from sakhi.apps.api.services.response.knowledge_gap import DiagnosticQuestion
from sakhi.apps.api.services.response.sensing import SenseFrame


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class ConstitutionGuidance:
    """Constitution-specific response guidance."""
    likely_causes: List[str]  # Most likely causes for this constitution
    tone: str  # How to frame the response
    avoid_suggesting: List[str]  # What not to recommend


@dataclass
class DiagnosticPath:
    """Complete diagnostic path for a symptom."""
    symptom: str
    domain: str
    sub_domain: str

    # Questions prioritized by dosha
    dosha_questions: Dict[str, List[DiagnosticQuestion]]  # dosha -> questions

    # Constitution-specific guidance
    constitution_guidance: Dict[str, ConstitutionGuidance]

    # Universal questions (ask regardless of constitution)
    universal_questions: List[DiagnosticQuestion] = field(default_factory=list)


# =============================================================================
# DIAGNOSTIC PATHS
# =============================================================================

# Headaches diagnostic path
HEADACHES_PATH = DiagnosticPath(
    symptom="headaches",
    domain="body",
    sub_domain="head_neurological",
    dosha_questions={
        "vata": [
            DiagnosticQuestion(
                id="pain_quality_vata",
                question="Is the pain more throbbing or pulsing?",
                priority="high",
                dosha_relevance="vata",
                why="Throbbing/pulsing suggests vata aggravation",
            ),
            DiagnosticQuestion(
                id="anxiety_connection",
                question="Does it come on when you're feeling anxious or scattered?",
                priority="high",
                dosha_relevance="vata",
                why="Vata headaches often linked to anxiety and overstimulation",
            ),
            DiagnosticQuestion(
                id="irregular_routine",
                question="Has your routine been irregular lately — meals, sleep?",
                priority="medium",
                dosha_relevance="vata",
                why="Vata is aggravated by irregular routines",
            ),
        ],
        "pitta": [
            DiagnosticQuestion(
                id="pain_quality_pitta",
                question="Is the pain sharp or burning?",
                priority="high",
                dosha_relevance="pitta",
                why="Sharp/burning pain suggests pitta aggravation",
            ),
            DiagnosticQuestion(
                id="heat_trigger",
                question="Does it come on after intense focus or heat exposure?",
                priority="high",
                dosha_relevance="pitta",
                why="Pitta headaches often heat/intensity related",
            ),
            DiagnosticQuestion(
                id="skipped_meals",
                question="Have you been skipping meals or eating late?",
                priority="medium",
                dosha_relevance="pitta",
                why="Pitta is aggravated by skipped meals",
            ),
        ],
        "kapha": [
            DiagnosticQuestion(
                id="pain_quality_kapha",
                question="Is the pain more dull, heavy, or pressure-like?",
                priority="high",
                dosha_relevance="kapha",
                why="Dull/heavy pain suggests kapha/sinus involvement",
            ),
            DiagnosticQuestion(
                id="congestion",
                question="Is there any sinus pressure or congestion with it?",
                priority="high",
                dosha_relevance="kapha",
                why="Kapha headaches often sinus-related",
            ),
            DiagnosticQuestion(
                id="sluggishness",
                question="Have you been feeling heavy or sluggish overall?",
                priority="medium",
                dosha_relevance="kapha",
                why="Kapha headaches often accompany general heaviness",
            ),
        ],
    },
    constitution_guidance={
        "vata": ConstitutionGuidance(
            likely_causes=["anxiety", "irregular_routine", "cold_dry", "overstimulation", "lack_of_grounding"],
            tone="grounding, calming, warm",
            avoid_suggesting=["intense_exercise", "stimulants", "skipping_meals", "cold_foods"],
        ),
        "pitta": ConstitutionGuidance(
            likely_causes=["intensity", "heat", "skipped_meals", "overwork", "frustration"],
            tone="cooling, measured, gentle",
            avoid_suggesting=["pushing_harder", "competition", "spicy_foods", "more_screen_time"],
        ),
        "kapha": ConstitutionGuidance(
            likely_causes=["sinus_congestion", "sluggishness", "oversleep", "heavy_foods", "lack_of_movement"],
            tone="energizing, clear, motivating",
            avoid_suggesting=["more_rest", "heavy_foods", "staying_indoors", "sleeping_more"],
        ),
    },
    universal_questions=[
        DiagnosticQuestion(
            id="timing",
            question="When does it typically happen — morning, afternoon, evening?",
            priority="medium",
            dosha_relevance="universal",
            why="Timing gives clues about triggers",
        ),
    ],
)

# Sleep issues diagnostic path
SLEEP_PATH = DiagnosticPath(
    symptom="sleep",
    domain="body",
    sub_domain="sleep",
    dosha_questions={
        "vata": [
            DiagnosticQuestion(
                id="racing_mind",
                question="Is it hard to fall asleep because your mind won't quiet?",
                priority="high",
                dosha_relevance="vata",
                why="Vata sleep issues often involve racing thoughts",
            ),
            DiagnosticQuestion(
                id="wake_anxiety",
                question="Do you wake up feeling anxious or restless?",
                priority="high",
                dosha_relevance="vata",
                why="Vata causes light, anxious sleep",
            ),
        ],
        "pitta": [
            DiagnosticQuestion(
                id="heat_wake",
                question="Do you wake up feeling hot or sweaty?",
                priority="high",
                dosha_relevance="pitta",
                why="Pitta causes heat-related sleep disturbance",
            ),
            DiagnosticQuestion(
                id="mind_work",
                question="Is your mind still working on problems when you try to sleep?",
                priority="high",
                dosha_relevance="pitta",
                why="Pitta minds stay active solving problems",
            ),
        ],
        "kapha": [
            DiagnosticQuestion(
                id="oversleep",
                question="Are you sleeping a lot but still waking tired?",
                priority="high",
                dosha_relevance="kapha",
                why="Kapha can cause excessive but unrefreshing sleep",
            ),
            DiagnosticQuestion(
                id="hard_wake",
                question="Is it hard to get going in the morning?",
                priority="high",
                dosha_relevance="kapha",
                why="Kapha causes sluggish mornings",
            ),
        ],
    },
    constitution_guidance={
        "vata": ConstitutionGuidance(
            likely_causes=["anxiety", "overstimulation", "irregular_schedule", "cold_environment"],
            tone="calming, grounding, reassuring",
            avoid_suggesting=["late_exercise", "stimulating_content", "irregular_bedtime"],
        ),
        "pitta": ConstitutionGuidance(
            likely_causes=["overwork", "mental_intensity", "late_eating", "unresolved_frustration"],
            tone="cooling, releasing, letting_go",
            avoid_suggesting=["working_late", "intense_discussions", "competitive_activities"],
        ),
        "kapha": ConstitutionGuidance(
            likely_causes=["lack_of_exercise", "heavy_evening_meals", "daytime_napping", "low_motivation"],
            tone="energizing, purposeful, activating",
            avoid_suggesting=["sleeping_more", "heavy_foods", "staying_inactive"],
        ),
    },
    universal_questions=[],
)

# Anxiety diagnostic path
ANXIETY_PATH = DiagnosticPath(
    symptom="anxiety",
    domain="mind",
    sub_domain="anxiety",
    dosha_questions={
        "vata": [
            DiagnosticQuestion(
                id="physical_symptoms",
                question="Do you feel it in your body — racing heart, shallow breath?",
                priority="high",
                dosha_relevance="vata",
                why="Vata anxiety is often felt physically",
            ),
            DiagnosticQuestion(
                id="grounding_help",
                question="Does it feel better when you slow down or go outside?",
                priority="medium",
                dosha_relevance="vata",
                why="Vata is calmed by grounding activities",
            ),
        ],
        "pitta": [
            DiagnosticQuestion(
                id="control_related",
                question="Is the anxiety about things being out of your control?",
                priority="high",
                dosha_relevance="pitta",
                why="Pitta anxiety often stems from control issues",
            ),
            DiagnosticQuestion(
                id="performance_anxiety",
                question="Is it about performance or meeting expectations?",
                priority="medium",
                dosha_relevance="pitta",
                why="Pitta often anxious about achievement",
            ),
        ],
        "kapha": [
            DiagnosticQuestion(
                id="stuck_feeling",
                question="Does it come with feeling stuck or unable to act?",
                priority="high",
                dosha_relevance="kapha",
                why="Kapha anxiety manifests as paralysis",
            ),
            DiagnosticQuestion(
                id="overwhelm_avoidance",
                question="Do you feel overwhelmed by everything that needs to be done?",
                priority="medium",
                dosha_relevance="kapha",
                why="Kapha anxiety leads to avoidance",
            ),
        ],
    },
    constitution_guidance={
        "vata": ConstitutionGuidance(
            likely_causes=["overstimulation", "uncertainty", "irregular_routine", "isolation"],
            tone="warm, steady, grounding",
            avoid_suggesting=["more_research", "analyzing_more", "staying_alone"],
        ),
        "pitta": ConstitutionGuidance(
            likely_causes=["loss_of_control", "high_stakes", "unmet_expectations", "comparison"],
            tone="cooling, accepting, releasing",
            avoid_suggesting=["more_planning", "perfectionism", "pushing_through"],
        ),
        "kapha": ConstitutionGuidance(
            likely_causes=["overwhelm", "stagnation", "avoidance_buildup", "lack_of_structure"],
            tone="energizing, action_oriented, one_step",
            avoid_suggesting=["more_rest", "more_thinking", "waiting_for_clarity"],
        ),
    },
    universal_questions=[],
)

# Energy/fatigue diagnostic path
ENERGY_PATH = DiagnosticPath(
    symptom="energy",
    domain="body",
    sub_domain="energy",
    dosha_questions={
        "vata": [
            DiagnosticQuestion(
                id="scattered_energy",
                question="Does your energy come in bursts then crash?",
                priority="high",
                dosha_relevance="vata",
                why="Vata has erratic energy patterns",
            ),
            DiagnosticQuestion(
                id="depletion_source",
                question="Have you been overextending or skipping self-care?",
                priority="high",
                dosha_relevance="vata",
                why="Vata depletes from irregularity",
            ),
        ],
        "pitta": [
            DiagnosticQuestion(
                id="burnout_pattern",
                question="Have you been pushing hard without breaks?",
                priority="high",
                dosha_relevance="pitta",
                why="Pitta energy depletes from overwork",
            ),
            DiagnosticQuestion(
                id="frustration_drain",
                question="Is there frustration or anger that's draining you?",
                priority="medium",
                dosha_relevance="pitta",
                why="Pitta wastes energy on frustration",
            ),
        ],
        "kapha": [
            DiagnosticQuestion(
                id="movement_lack",
                question="Have you been moving less than usual?",
                priority="high",
                dosha_relevance="kapha",
                why="Kapha energy stagnates without movement",
            ),
            DiagnosticQuestion(
                id="heavy_foods",
                question="Has your eating been heavier or more comfort-focused?",
                priority="medium",
                dosha_relevance="kapha",
                why="Kapha is weighed down by heavy foods",
            ),
        ],
    },
    constitution_guidance={
        "vata": ConstitutionGuidance(
            likely_causes=["irregular_schedule", "overextension", "lack_of_nourishment", "cold"],
            tone="nurturing, grounding, steady",
            avoid_suggesting=["more_activity", "fasting", "cold_foods"],
        ),
        "pitta": ConstitutionGuidance(
            likely_causes=["overwork", "skipped_meals", "emotional_intensity", "heat"],
            tone="cooling, restorative, releasing",
            avoid_suggesting=["pushing_through", "more_intensity", "stimulants"],
        ),
        "kapha": ConstitutionGuidance(
            likely_causes=["inactivity", "oversleep", "heavy_food", "stagnation"],
            tone="energizing, movement_focused, light",
            avoid_suggesting=["more_rest", "heavy_foods", "staying_indoors"],
        ),
    },
    universal_questions=[],
)

# Stress diagnostic path
STRESS_PATH = DiagnosticPath(
    symptom="stress",
    domain="mind",
    sub_domain="stress",
    dosha_questions={
        "vata": [
            DiagnosticQuestion(
                id="overwhelm_type",
                question="Does it feel like too many things at once?",
                priority="high",
                dosha_relevance="vata",
                why="Vata stress is about overwhelm and chaos",
            ),
            DiagnosticQuestion(
                id="ground_missing",
                question="Do you feel ungrounded or scattered?",
                priority="medium",
                dosha_relevance="vata",
                why="Vata needs grounding under stress",
            ),
        ],
        "pitta": [
            DiagnosticQuestion(
                id="deadline_driven",
                question="Is it pressure to perform or deliver?",
                priority="high",
                dosha_relevance="pitta",
                why="Pitta stress is achievement-driven",
            ),
            DiagnosticQuestion(
                id="frustration_building",
                question="Are things not going as planned?",
                priority="medium",
                dosha_relevance="pitta",
                why="Pitta stresses when control is lost",
            ),
        ],
        "kapha": [
            DiagnosticQuestion(
                id="avoidance_building",
                question="Are things piling up that you've been avoiding?",
                priority="high",
                dosha_relevance="kapha",
                why="Kapha stress builds from avoidance",
            ),
            DiagnosticQuestion(
                id="change_stress",
                question="Is there change happening that feels uncomfortable?",
                priority="medium",
                dosha_relevance="kapha",
                why="Kapha resists change",
            ),
        ],
    },
    constitution_guidance={
        "vata": ConstitutionGuidance(
            likely_causes=["overwhelm", "uncertainty", "too_many_inputs", "chaos"],
            tone="calming, simplifying, one_thing",
            avoid_suggesting=["more_planning", "multitasking", "big_changes"],
        ),
        "pitta": ConstitutionGuidance(
            likely_causes=["deadline_pressure", "high_expectations", "blocked_progress", "competition"],
            tone="releasing, perspective, accepting",
            avoid_suggesting=["pushing_harder", "perfectionism", "comparison"],
        ),
        "kapha": ConstitutionGuidance(
            likely_causes=["avoidance_buildup", "resistance_to_change", "stagnation", "overwhelm"],
            tone="activating, small_steps, momentum",
            avoid_suggesting=["more_thinking", "waiting", "adding_comfort"],
        ),
    },
    universal_questions=[],
)


# Work/Career diagnostic path
WORK_PATH = DiagnosticPath(
    symptom="work",
    domain="life",
    sub_domain="work",
    dosha_questions={
        "vata": [
            DiagnosticQuestion(
                id="work_scattered",
                question="Are you feeling pulled in too many directions at work?",
                priority="high",
                dosha_relevance="vata",
                why="Vata struggles with too many inputs",
            ),
            DiagnosticQuestion(
                id="work_routine",
                question="Has your work schedule been irregular lately?",
                priority="medium",
                dosha_relevance="vata",
                why="Vata needs routine to stay grounded",
            ),
        ],
        "pitta": [
            DiagnosticQuestion(
                id="work_recognition",
                question="Is your work being recognized the way you'd like?",
                priority="high",
                dosha_relevance="pitta",
                why="Pitta needs achievement and recognition",
            ),
            DiagnosticQuestion(
                id="work_control",
                question="Do you have enough control over how things are done?",
                priority="medium",
                dosha_relevance="pitta",
                why="Pitta needs control and autonomy",
            ),
        ],
        "kapha": [
            DiagnosticQuestion(
                id="work_stagnation",
                question="Does your work feel like it's in a rut?",
                priority="high",
                dosha_relevance="kapha",
                why="Kapha can stagnate without variety",
            ),
            DiagnosticQuestion(
                id="work_motivation",
                question="Are you finding it hard to get started on things?",
                priority="medium",
                dosha_relevance="kapha",
                why="Kapha needs momentum to stay engaged",
            ),
        ],
    },
    constitution_guidance={
        "vata": ConstitutionGuidance(
            likely_causes=["too_many_projects", "lack_of_structure", "overstimulation"],
            tone="grounding, simplifying, one_thing_at_a_time",
            avoid_suggesting=["multitasking", "taking_more_on", "big_changes"],
        ),
        "pitta": ConstitutionGuidance(
            likely_causes=["lack_of_recognition", "blocked_goals", "inefficiency"],
            tone="strategic, validating, channeling",
            avoid_suggesting=["giving_up", "lowering_standards", "being_passive"],
        ),
        "kapha": ConstitutionGuidance(
            likely_causes=["routine_staleness", "lack_of_challenge", "comfort_zone"],
            tone="energizing, challenging, variety_focused",
            avoid_suggesting=["more_of_same", "waiting", "comfort"],
        ),
    },
    universal_questions=[],
)

# Relationships diagnostic path
RELATIONSHIPS_PATH = DiagnosticPath(
    symptom="relationships",
    domain="life",
    sub_domain="relationships",
    dosha_questions={
        "vata": [
            DiagnosticQuestion(
                id="rel_connection",
                question="Are you feeling connected or a bit isolated lately?",
                priority="high",
                dosha_relevance="vata",
                why="Vata can feel disconnected when overwhelmed",
            ),
            DiagnosticQuestion(
                id="rel_communication",
                question="Is there something you want to say but haven't found the words for?",
                priority="medium",
                dosha_relevance="vata",
                why="Vata can have scattered thoughts about relationships",
            ),
        ],
        "pitta": [
            DiagnosticQuestion(
                id="rel_expectations",
                question="Are expectations being met on both sides?",
                priority="high",
                dosha_relevance="pitta",
                why="Pitta is sensitive to unmet expectations",
            ),
            DiagnosticQuestion(
                id="rel_frustration",
                question="Is there frustration that's building up?",
                priority="medium",
                dosha_relevance="pitta",
                why="Pitta accumulates frustration in relationships",
            ),
        ],
        "kapha": [
            DiagnosticQuestion(
                id="rel_comfort_rut",
                question="Has the relationship settled into too comfortable a pattern?",
                priority="high",
                dosha_relevance="kapha",
                why="Kapha relationships can stagnate",
            ),
            DiagnosticQuestion(
                id="rel_expression",
                question="Are you holding back from expressing what you really feel?",
                priority="medium",
                dosha_relevance="kapha",
                why="Kapha tends to suppress for harmony",
            ),
        ],
    },
    constitution_guidance={
        "vata": ConstitutionGuidance(
            likely_causes=["overstimulation", "lack_of_grounding", "fear_of_commitment"],
            tone="warm, steady, reassuring",
            avoid_suggesting=["withdrawing", "overanalyzing", "rushing"],
        ),
        "pitta": ConstitutionGuidance(
            likely_causes=["unmet_expectations", "control_issues", "competitive_dynamic"],
            tone="cooling, perspective, acceptance",
            avoid_suggesting=["forcing_change", "being_right", "intensity"],
        ),
        "kapha": ConstitutionGuidance(
            likely_causes=["stagnation", "avoiding_difficult_conversations", "excessive_accommodation"],
            tone="activating, honest, growth_oriented",
            avoid_suggesting=["more_waiting", "suppressing", "maintaining_status_quo"],
        ),
    },
    universal_questions=[],
)

# General conversation path - for when no specific symptom/topic is identified
GENERAL_PATH = DiagnosticPath(
    symptom="general",
    domain="general",
    sub_domain="sharing",
    dosha_questions={
        "vata": [
            DiagnosticQuestion(
                id="general_pace",
                question="How's your pace been feeling lately — too fast, too scattered?",
                priority="low",
                dosha_relevance="vata",
                why="Vata benefits from pace awareness",
            ),
        ],
        "pitta": [
            DiagnosticQuestion(
                id="general_intensity",
                question="How's your energy and drive feeling?",
                priority="low",
                dosha_relevance="pitta",
                why="Pitta benefits from intensity awareness",
            ),
        ],
        "kapha": [
            DiagnosticQuestion(
                id="general_movement",
                question="Have you been moving and engaging, or feeling a bit heavy?",
                priority="low",
                dosha_relevance="kapha",
                why="Kapha benefits from movement awareness",
            ),
        ],
    },
    constitution_guidance={
        "vata": ConstitutionGuidance(
            likely_causes=["varied"],
            tone="warm, grounding, steady",
            avoid_suggesting=["rushing", "multitasking"],
        ),
        "pitta": ConstitutionGuidance(
            likely_causes=["varied"],
            tone="measured, strategic, clear",
            avoid_suggesting=["overworking", "perfectionism"],
        ),
        "kapha": ConstitutionGuidance(
            likely_causes=["varied"],
            tone="energizing, light, motivating",
            avoid_suggesting=["stagnation", "over_comfort"],
        ),
    },
    universal_questions=[],
)


# =============================================================================
# PATH REGISTRY
# =============================================================================

DIAGNOSTIC_PATHS: Dict[str, DiagnosticPath] = {
    # Body domain
    "headaches": HEADACHES_PATH,
    "headache": HEADACHES_PATH,
    "head": HEADACHES_PATH,
    "migraine": HEADACHES_PATH,
    "sleep": SLEEP_PATH,
    "insomnia": SLEEP_PATH,
    "tired": SLEEP_PATH,
    "fatigue": ENERGY_PATH,
    "energy": ENERGY_PATH,
    "exhausted": ENERGY_PATH,
    # Mind domain
    "anxiety": ANXIETY_PATH,
    "anxious": ANXIETY_PATH,
    "worried": ANXIETY_PATH,
    "stress": STRESS_PATH,
    "stressed": STRESS_PATH,
    "overwhelmed": STRESS_PATH,
    # Life domain
    "work": WORK_PATH,
    "job": WORK_PATH,
    "career": WORK_PATH,
    "boss": WORK_PATH,
    "colleague": WORK_PATH,
    "relationship": RELATIONSHIPS_PATH,
    "relationships": RELATIONSHIPS_PATH,
    "family": RELATIONSHIPS_PATH,
    "friend": RELATIONSHIPS_PATH,
    "partner": RELATIONSHIPS_PATH,
    "marriage": RELATIONSHIPS_PATH,
    # General domain (fallback)
    "general": GENERAL_PATH,
    "sharing": GENERAL_PATH,
    "greeting": GENERAL_PATH,
}


# =============================================================================
# LOOKUP FUNCTIONS
# =============================================================================

def get_diagnostic_path(symptom: str) -> Optional[DiagnosticPath]:
    """
    Get the diagnostic path for a symptom.

    Args:
        symptom: The symptom keyword (e.g., "headaches", "sleep")

    Returns:
        DiagnosticPath if found, None otherwise
    """
    symptom_lower = symptom.lower().strip()
    return DIAGNOSTIC_PATHS.get(symptom_lower)


def get_diagnostic_questions(
    symptom: str,
    dominant_dosha: str,
    *,
    include_universal: bool = True,
) -> List[DiagnosticQuestion]:
    """
    Get prioritized diagnostic questions for a symptom and constitution.

    Questions are returned in priority order:
    1. High-priority questions for the dominant dosha
    2. Medium-priority questions for the dominant dosha
    3. Universal questions
    4. High-priority questions for other doshas (lower priority)

    Args:
        symptom: The symptom keyword
        dominant_dosha: User's dominant dosha ("vata", "pitta", "kapha", or "balanced")
        include_universal: Whether to include universal questions

    Returns:
        List of DiagnosticQuestion objects, prioritized
    """
    path = get_diagnostic_path(symptom)
    if not path:
        return []

    questions = []

    # For balanced constitution, mix from all doshas
    if dominant_dosha == "balanced":
        # Take first question from each dosha
        for dosha in ["vata", "pitta", "kapha"]:
            dosha_qs = path.dosha_questions.get(dosha, [])
            if dosha_qs:
                questions.append(dosha_qs[0])
    else:
        # Prioritize dominant dosha questions
        dominant_qs = path.dosha_questions.get(dominant_dosha, [])
        questions.extend(dominant_qs)

        # Add a question from other doshas as backup
        for dosha in ["vata", "pitta", "kapha"]:
            if dosha != dominant_dosha:
                other_qs = path.dosha_questions.get(dosha, [])
                if other_qs:
                    # Add first question from other dosha with lower priority
                    backup_q = other_qs[0]
                    backup_q.priority = "low"
                    questions.append(backup_q)

    # Add universal questions
    if include_universal:
        questions.extend(path.universal_questions)

    return questions


def get_constitution_guidance(
    symptom: str,
    dominant_dosha: str,
) -> Optional[ConstitutionGuidance]:
    """
    Get constitution-specific guidance for responding about a symptom.

    Args:
        symptom: The symptom keyword
        dominant_dosha: User's dominant dosha

    Returns:
        ConstitutionGuidance if found, None otherwise
    """
    path = get_diagnostic_path(symptom)
    if not path:
        return None

    # For balanced, use a mix
    if dominant_dosha == "balanced":
        return ConstitutionGuidance(
            likely_causes=["lifestyle_factors", "routine_changes", "stress"],
            tone="balanced, gentle, exploratory",
            avoid_suggesting=["extreme_changes"],
        )

    return path.constitution_guidance.get(dominant_dosha)


def get_symptom_from_sense(sense: SenseFrame) -> str:
    """Extract the best symptom keyword from a SenseFrame."""
    # Try the extracted symptom first
    if sense.symptom and sense.symptom in DIAGNOSTIC_PATHS:
        return sense.symptom

    # Try sub_domain
    if sense.sub_domain and sense.sub_domain in DIAGNOSTIC_PATHS:
        return sense.sub_domain

    # Try keywords
    for kw in sense.keywords:
        if kw in DIAGNOSTIC_PATHS:
            return kw

    # Fallback to domain-based default
    domain_defaults = {
        "body": "energy",
        "mind": "stress",
        "life": "work",
        "general": "general",
    }
    return domain_defaults.get(sense.domain, "general")


# =============================================================================
# SYMPTOM MATCHING + OS-DOSHA INSIGHT TEMPLATES
# =============================================================================
# Foods/practices/avoids come from the knowledge graph (ay_nodes/ay_edges).
# OS insight templates explain WHY a dosha-type symptom makes sense for this
# person's OS type. 12 templates (3 doshas × 4 OS types) — zero jargon.

# Fuzzy match aliases → canonical symptom key
_SYMPTOM_ALIASES = {
    # Congestion
    "congestion": "congestion", "nose block": "congestion", "blocked nose": "congestion",
    "stuffy nose": "congestion", "nasal": "congestion", "sinus": "congestion",
    "runny nose": "congestion", "mucus": "congestion",
    # Headache
    "headache": "headache", "head pain": "headache", "head ache": "headache",
    "throbbing head": "headache",
    # Migraine
    "migraine": "migraine",
    # Fatigue
    "fatigue": "fatigue", "tired": "fatigue", "exhausted": "fatigue",
    "exhaustion": "fatigue", "no energy": "fatigue", "low energy": "fatigue",
    "drained": "fatigue", "lethargic": "fatigue",
    # Insomnia
    "insomnia": "insomnia", "can't sleep": "insomnia", "sleepless": "insomnia",
    "trouble sleeping": "insomnia", "sleep issues": "insomnia",
    "not sleeping": "insomnia", "restless sleep": "insomnia",
    # Acidity
    "acidity": "acidity", "heartburn": "acidity", "acid reflux": "acidity",
    "burning stomach": "acidity", "acid": "acidity",
    # Bloating
    "bloating": "bloating", "bloated": "bloating", "gas": "bloating",
    "gassy": "bloating", "stomach bloat": "bloating",
    # Constipation
    "constipation": "constipation", "constipated": "constipation",
    # Anxiety
    "anxiety": "anxiety", "anxious": "anxiety", "panic": "anxiety",
    "worried": "anxiety", "racing thoughts": "anxiety", "nervous": "anxiety",
    # Stress
    "stress": "stress", "stressed": "stress", "overwhelmed": "stress",
    "burnout": "stress", "overloaded": "stress",
    # Body pain
    "body_pain": "body_pain", "body pain": "body_pain", "aches": "body_pain",
    "pain": "body_pain", "stiff": "body_pain", "stiffness": "body_pain",
    "sore body": "body_pain", "muscle pain": "body_pain",
    # Cold
    "cold": "cold", "common cold": "cold", "flu": "cold",
    "chills": "cold", "sneezing": "cold",
    # Fever
    "fever": "fever", "temperature": "fever", "hot": "fever",
    # Nausea
    "nausea": "nausea", "nauseous": "nausea", "feeling sick": "nausea",
    "queasy": "nausea", "vomiting": "nausea",
    # Sore throat
    "sore_throat": "sore_throat", "sore throat": "sore_throat",
    "throat pain": "sore_throat", "scratchy throat": "sore_throat",
    "throat": "sore_throat",
}

# OS-dosha insight templates: explain WHY this dosha-type symptom makes sense
# for this person's OS type. Uses {symptom} placeholder.
OS_DOSHA_INSIGHT_TEMPLATES = {
    # Kapha symptoms (congestion, sluggishness, heaviness)
    ("kapha", "Conservation"): "You're naturally steady — {symptom} is your system getting too heavy. It needs warmth and movement to clear out.",
    ("kapha", "Adaptive"): "This isn't typical for you — {symptom} means something's slowing your system down. Warming things up will get you moving again.",
    ("kapha", "Performance"): "You've been pushing hard and your body's holding on to things. {symptom} is a sign to lighten up and let warmth do the work.",
    ("kapha", "Balanced"): "Your system's a bit sluggish right now. {symptom} will clear with some warmth and movement.",
    # Pitta symptoms (heat, inflammation, irritation)
    ("pitta", "Performance"): "You push hard — {symptom} is your system saying ease up. The heat needs somewhere to go.",
    ("pitta", "Conservation"): "This is unusual for you — {symptom} means something's heating up internally. Cooling down will help.",
    ("pitta", "Adaptive"): "Your energy's been scattered and it's building pressure. {symptom} is a sign to slow down and cool off.",
    ("pitta", "Balanced"): "Something's running hot in your system. {symptom} will ease with some cooling.",
    # Vata symptoms (anxiety, scattered, dryness, irregularity)
    ("vata", "Adaptive"): "Your quick-moving mind is in overdrive — {symptom} is your system asking for grounding. Something steady and warm will help.",
    ("vata", "Performance"): "You've been putting pressure on yourself and it's creating tension. {symptom} is a sign to ease the grip.",
    ("vata", "Conservation"): "This isn't your natural state — {symptom} means something has shaken your usual steadiness. Warmth and routine will bring it back.",
    ("vata", "Balanced"): "Your system feels unsettled. {symptom} will ease with warmth and a steady routine.",
}


def _normalize_os_type(os_type: str) -> str:
    """Normalize OS type to one of the 4 protocol keys."""
    if not os_type:
        return "Balanced"
    os_lower = os_type.lower()
    if "conservation" in os_lower or "endurance" in os_lower or "steady" in os_lower:
        return "Conservation"
    if "performance" in os_lower or "driven" in os_lower:
        return "Performance"
    if "adaptive" in os_lower or "flow" in os_lower or "quick" in os_lower:
        return "Adaptive"
    return "Balanced"


def match_symptom(symptom: str) -> Optional[str]:
    """Fuzzy match a symptom string to a canonical symptom key."""
    if not symptom:
        return None
    key = symptom.lower().strip()

    # Direct alias match
    canonical = _SYMPTOM_ALIASES.get(key)
    if canonical:
        return canonical

    # Substring match — check if any alias is contained in the symptom text
    for alias, can in _SYMPTOM_ALIASES.items():
        if alias in key:
            return can

    return None


def get_symptom_insight(symptom: str, dosha: str, os_type: str) -> str:
    """Get OS-aware insight explaining WHY this symptom for this person."""
    os_key = _normalize_os_type(os_type)
    template = OS_DOSHA_INSIGHT_TEMPLATES.get((dosha, os_key))
    if not template:
        template = OS_DOSHA_INSIGHT_TEMPLATES.get((dosha, "Balanced"), "")
    symptom_display = symptom.replace("_", " ")
    return template.format(symptom=symptom_display) if template else ""


async def generate_symptom_protocol_via_llm(
    symptom: str, dosha: str, os_type: str, os_insight: str,
) -> Optional[dict]:
    """
    LLM fallback: generate symptom recommendation when knowledge graph is empty.

    Returns same dict format as knowledge-graph path:
    {"insight": str, "best_food": {"what": ..., "why": ...}, ...}
    """
    import json as _json
    from sakhi.apps.api.core.llm import call_llm

    os_key = _normalize_os_type(os_type)
    _OS_QUALITY = {
        "Conservation": "steady and grounded",
        "Adaptive": "quick-moving and creative",
        "Performance": "driven and focused",
        "Balanced": "balanced",
    }
    quality = _OS_QUALITY.get(os_key, "balanced")

    _DOSHA_QUALITY = {
        "kapha": "heaviness and sluggishness",
        "pitta": "heat and intensity",
        "vata": "scattered energy and dryness",
    }
    imbalance = _DOSHA_QUALITY.get(dosha, "imbalance")

    prompt = (
        f"The user is experiencing: {symptom}\n"
        f"Their system type: {os_key} (naturally {quality})\n"
        f"The underlying pattern: {imbalance}\n\n"
        "Give exactly ONE food recommendation and ONE practice "
        "(yoga, breathing, or routine) that would help.\n"
        "Each must have a short reason why it helps THIS person.\n"
        "Also name ONE thing to avoid.\n\n"
        "Rules:\n"
        "- No Sanskrit or Ayurvedic terms (no dosha, pranayama, kapha, etc.)\n"
        "- Use plain everyday English\n"
        "- Connect the reason to their system type\n"
        "- Be specific (not 'eat healthy' — name the actual food/practice)\n\n"
        'Return JSON:\n'
        '{"food": {"what": "the specific food or drink", "why": "reason"}, '
        '"practice": {"what": "the specific practice", "why": "reason"}, '
        '"avoid": "what to skip and why"}'
    )

    try:
        result = await call_llm(prompt, model="openrouter/fast")
        data = _json.loads(result) if isinstance(result, str) else result
        return {
            "insight": os_insight,
            "best_food": data.get("food"),
            "best_practice": data.get("practice"),
            "avoid": data.get("avoid", ""),
        }
    except Exception:
        return None


__all__ = [
    "DiagnosticPath",
    "ConstitutionGuidance",
    "DIAGNOSTIC_PATHS",
    "get_diagnostic_path",
    "get_diagnostic_questions",
    "get_constitution_guidance",
    "get_symptom_from_sense",
    "match_symptom",
    "get_symptom_insight",
    "generate_symptom_protocol_via_llm",
]
