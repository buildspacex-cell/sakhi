"""
Jargon-Free Translation Layer

Translates all Ayurvedic and yogic concepts into everyday, accessible language.
The science remains—the terminology transforms.

Core Principles:
- "Dosha" → "Energy pattern" or just describe the quality
- "Vata/Pitta/Kapha" → Descriptive qualities (scattered/intense/heavy)
- "Prakruti" → "Your baseline" or "how you're wired"
- "Vikriti" → "Current state" or "where you are now"
- "Gunas" → "Energy modes" (clarity/activation/inertia)
- Friction = the felt sense of imbalance

The user never sees Sanskrit. They see their own experience reflected back.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

# =============================================================================
# OPERATING SYSTEM TRANSLATIONS
# =============================================================================

OPERATING_SYSTEM_DESCRIPTIONS = {
    "Adaptive-Flow": {
        "name": "Quick-moving",
        "short": "creative, loves variety",
        "description": "You're the type who gets excited by new ideas and needs variety to feel alive. Your mind moves fast — that's your superpower. But when things get chaotic, you feel it first.",
        "strengths": ["creativity", "adaptability", "quick thinking", "enthusiasm"],
        "watch_for": ["scattered energy", "anxiety", "irregular routines", "overthinking"],
        "thrives_with": ["routine", "warmth", "grounding activities", "steady rhythm"],
    },
    "Adaptive-Performance": {
        "name": "Driven",
        "short": "focused, gets things done",
        "description": "You're wired to achieve. Sharp, clear, and you know what you want. That intensity is a gift — but it can turn on you when you push too hard.",
        "strengths": ["focus", "determination", "leadership", "clear thinking"],
        "watch_for": ["overwork", "irritability", "perfectionism", "impatience"],
        "thrives_with": ["moderation", "play", "cooling activities", "letting go"],
    },
    "Adaptive-Endurance": {
        "name": "Steady",
        "short": "grounded, reliable",
        "description": "You've got natural stamina — you're the person others lean on. That stability is rare. But sometimes you get stuck, and change feels harder than it should.",
        "strengths": ["stability", "endurance", "patience", "nurturing"],
        "watch_for": ["stagnation", "resistance to change", "low motivation", "attachment"],
        "thrives_with": ["variety", "movement", "lightness", "new challenges"],
    },
    "Balanced": {
        "name": "Balanced",
        "short": "adaptable",
        "description": "You're pretty even across the board — no strong pull in one direction. That's flexible, but it also means you gotta tune in more carefully to what you need.",
        "strengths": ["balance", "flexibility", "adaptability"],
        "watch_for": ["missing subtle imbalances", "generic approaches"],
        "thrives_with": ["seasonal adjustments", "listening to body signals"],
    },
}

# Aliases: onboarding uses these shorter names
OPERATING_SYSTEM_DESCRIPTIONS["Adaptive"] = OPERATING_SYSTEM_DESCRIPTIONS["Adaptive-Flow"]
OPERATING_SYSTEM_DESCRIPTIONS["Performance"] = OPERATING_SYSTEM_DESCRIPTIONS["Adaptive-Performance"]
OPERATING_SYSTEM_DESCRIPTIONS["Conservation"] = OPERATING_SYSTEM_DESCRIPTIONS["Adaptive-Endurance"]

# Dual types
OPERATING_SYSTEM_DESCRIPTIONS["Adaptive-Conservation"] = {
    "name": "Creative-Steady",
    "short": "imaginative with endurance",
    "description": "You blend creativity with stamina. You get excited by new ideas but also have the patience to see things through. Balance quick thinking with steady follow-through.",
    "strengths": ["creative endurance", "adaptability", "patience with novelty"],
    "watch_for": ["scattered energy vs stagnation swings", "difficulty prioritizing"],
    "thrives_with": ["structured creativity", "gentle routine", "movement"],
}
OPERATING_SYSTEM_DESCRIPTIONS["Performance-Conservation"] = {
    "name": "Driven-Steady",
    "short": "focused with endurance",
    "description": "You combine drive with stamina. You pursue goals with determination and have the patience to see them through. Balance intensity with rest.",
    "strengths": ["focused endurance", "leadership", "consistency"],
    "watch_for": ["overwork combined with resistance to change", "stubbornness"],
    "thrives_with": ["variety in routine", "cooling activities", "playfulness"],
}

# Fallback for unknown types
DEFAULT_OPERATING_SYSTEM = {
    "name": "You",
    "short": "unique",
    "description": "Still getting to know your patterns. The more we talk, the better I'll understand what works for you.",
    "strengths": ["unique perspective"],
    "watch_for": ["varies by day"],
    "thrives_with": ["self-awareness", "experimentation"],
}


# =============================================================================
# FRICTION STATE TRANSLATIONS (already jargon-free, enhance)
# =============================================================================

FRICTION_TRANSLATIONS = {
    "chaos": {
        "name": "all over the place",
        "description": "Mind's racing, hard to land on anything. Maybe a bit anxious or just... scattered.",
        "what_helps": "Slow it down. Warmth helps. Something grounding — even just a walk.",
        "quick_reframe": "Your system's in overdrive. It just needs a signal that everything's okay.",
        "body_signal": "racing thoughts, can't settle, cold hands, appetite all over the place",
    },
    "intensity": {
        "name": "running hot",
        "description": "You're pushing hard. Maybe getting irritated more easily, or just feeling like you can't stop.",
        "what_helps": "Cool it down. Less doing, more being. Play, not productivity.",
        "quick_reframe": "That drive is yours — but right now it's turned up a bit too high.",
        "body_signal": "irritable, impatient, overheating, being too hard on yourself",
    },
    "stagnation": {
        "name": "stuck",
        "description": "Everything feels heavy. Motivation's low. Change sounds exhausting.",
        "what_helps": "Move. Anything new. Even small changes help shake things loose.",
        "quick_reframe": "You've gone into conservation mode. Time to get things moving again.",
        "body_signal": "heavy, unmotivated, sleeping too much, avoiding things",
    },
    "balanced": {
        "name": "good",
        "description": "You're in your rhythm. Things are flowing.",
        "what_helps": "Keep doing what you're doing. Small tweaks as seasons change.",
        "quick_reframe": "You're humming along. Nice.",
        "body_signal": "steady energy, sleeping well, thinking clearly",
    },
}


# =============================================================================
# ENERGY MODE TRANSLATIONS (Gunas → Everyday)
# =============================================================================

ENERGY_MODE_TRANSLATIONS = {
    "sattva": {
        "name": "clear",
        "short": "clear-headed",
        "description": "Mind's quiet. Decisions feel easier. You're centered.",
    },
    "rajas": {
        "name": "active",
        "short": "on the go",
        "description": "Lots of energy, wanting to do things. Just watch it doesn't tip into restless.",
    },
    "tamas": {
        "name": "low",
        "short": "turned inward",
        "description": "Energy's down, turned inward. Good for rest, but can get sticky if you stay too long.",
    },
}


# =============================================================================
# RECOMMENDATION TRANSLATIONS
# =============================================================================

FOOD_QUALITY_TRANSLATIONS = {
    # Rasa (taste) → simple effect
    "sweet": "grounding",
    "sour": "good for digestion",
    "salty": "warming",
    "pungent": "heating",
    "bitter": "cooling, cleansing",
    "astringent": "drying",

    # Virya (energy) → simple effect
    "heating": "warming",
    "cooling": "cooling",
    "neutral": "balancing",
}

PRACTICE_TRANSLATIONS = {
    # Practice types → what a friend would call them
    "pranayama": "breathing",
    "asana": "gentle stretching",
    "meditation": "sitting quietly",
    "abhyanga": "self-massage",
    "dinacharya": "morning routine",
    "yoga_nidra": "deep rest",
    "trataka": "candle gazing",
    "japa": "mantra",
    "kriyas": "cleansing",
}


# =============================================================================
# TRANSLATION FUNCTIONS
# =============================================================================

def translate_operating_system(os_type: str) -> Dict[str, Any]:
    """Translate operating system type to user-friendly description."""
    return OPERATING_SYSTEM_DESCRIPTIONS.get(os_type, DEFAULT_OPERATING_SYSTEM)


def translate_friction_state(friction_key: str) -> Dict[str, str]:
    """Translate friction state key to user-friendly description."""
    return FRICTION_TRANSLATIONS.get(friction_key.lower(), FRICTION_TRANSLATIONS["balanced"])


def translate_energy_mode(guna: str) -> Dict[str, str]:
    """Translate guna to energy mode description."""
    return ENERGY_MODE_TRANSLATIONS.get(guna.lower(), {
        "name": "Mixed Mode",
        "short": "variable",
        "description": "Energy is mixed—some clarity, some activation, some conservation.",
    })


def translate_food_quality(rasa: Optional[str], virya: Optional[str]) -> str:
    """Translate food qualities to simple words."""
    parts = []
    if virya:
        effect = FOOD_QUALITY_TRANSLATIONS.get(virya.lower())
        if effect:
            parts.append(effect)
    if rasa and not parts:
        effect = FOOD_QUALITY_TRANSLATIONS.get(rasa.lower())
        if effect:
            parts.append(effect)
    return parts[0] if parts else "good for you"


def translate_practice_name(practice_name: str) -> str:
    """Translate practice name to plain English."""
    # First check if it's a known Sanskrit term
    name_lower = practice_name.lower().replace("_", " ")
    for sanskrit, english in PRACTICE_TRANSLATIONS.items():
        if sanskrit in name_lower:
            return name_lower.replace(sanskrit, english)

    # Otherwise just clean up the name
    return practice_name.replace("_", " ").title()


def translate_constitution(dosha_baseline: Dict[str, float]) -> str:
    """
    Translate dosha percentages to plain, friendly description.

    Never mentions doshas—just describes who they are.
    """
    if not dosha_baseline:
        return "still getting to know you"

    vata = dosha_baseline.get("vata", 0.33)
    pitta = dosha_baseline.get("pitta", 0.33)
    kapha = dosha_baseline.get("kapha", 0.34)

    # Find dominant (>40%) and secondary (>30%) patterns
    dominant = []
    if vata > 0.4:
        dominant.append("quick-moving, creative")
    if pitta > 0.4:
        dominant.append("sharp, driven")
    if kapha > 0.4:
        dominant.append("steady, grounded")

    if not dominant:
        # Check for secondary
        if vata > 0.35:
            dominant.append("a bit quick-moving")
        if pitta > 0.35:
            dominant.append("somewhat driven")
        if kapha > 0.35:
            dominant.append("pretty steady")

    if not dominant:
        return "balanced, no strong pull either way"

    return " and ".join(dominant)


def translate_drift_severity(drift_percentage: float) -> str:
    """Translate drift percentage to casual, friendly language."""
    if drift_percentage < 15:
        return "in your groove"
    elif drift_percentage < 25:
        return "a bit off"
    elif drift_percentage < 40:
        return "noticeably off"
    else:
        return "pretty far from your baseline"


# =============================================================================
# PROMPT BUILDERS (Jargon-Free)
# =============================================================================

@dataclass
class JargonFreeContext:
    """All context translated to everyday language."""

    # Who they are
    operating_system_name: str = ""
    operating_system_description: str = ""
    constitution_description: str = ""  # Never mentions doshas

    # Current state
    friction_state_name: str = ""
    friction_description: str = ""
    friction_quick_reframe: str = ""
    drift_description: str = ""
    energy_mode_name: str = ""
    energy_mode_description: str = ""

    # What helps
    what_helps_now: str = ""
    body_signals_to_watch: str = ""

    # Recommendations (translated from friction state)
    foods_translated: List[Dict[str, str]] = None
    practices_translated: List[Dict[str, str]] = None
    immediate_actions: List[Dict[str, str]] = None

    # Symptom-specific (OS-aware, 1-2 recs — takes priority when present)
    symptom_insight: str = ""
    symptom_best_food: Optional[Dict[str, str]] = None
    symptom_best_practice: Optional[Dict[str, str]] = None
    symptom_avoid: str = ""


def build_jargon_free_context(
    operating_system: str,
    dosha_baseline: Dict[str, float],
    friction_state: str,
    drift_percentage: float,
    energy_mode: str,
    recommendations: Optional[Dict[str, Any]] = None,
    symptom_protocol: Optional[Dict[str, Any]] = None,
) -> JargonFreeContext:
    """
    Build complete jargon-free context from all signals.

    This is the main integration point—takes all the Ayurvedic data
    and returns a context object with no Sanskrit anywhere.
    """
    ctx = JargonFreeContext()

    # Operating system
    os_info = translate_operating_system(operating_system)
    ctx.operating_system_name = os_info["name"]
    ctx.operating_system_description = os_info["description"]

    # Constitution (no dosha names)
    ctx.constitution_description = translate_constitution(dosha_baseline)

    # Friction state
    friction_info = translate_friction_state(friction_state)
    ctx.friction_state_name = friction_info["name"]
    ctx.friction_description = friction_info["description"]
    ctx.friction_quick_reframe = friction_info["quick_reframe"]
    ctx.what_helps_now = friction_info["what_helps"]
    ctx.body_signals_to_watch = friction_info["body_signal"]

    # Drift
    ctx.drift_description = translate_drift_severity(drift_percentage)

    # Energy mode
    mode_info = translate_energy_mode(energy_mode)
    ctx.energy_mode_name = mode_info["name"]
    ctx.energy_mode_description = mode_info["description"]

    # Recommendations
    if recommendations:
        ctx.foods_translated = _translate_foods(recommendations.get("foods_now", []))
        ctx.practices_translated = _translate_practices(recommendations.get("practices_today", []))
        ctx.immediate_actions = _translate_immediate(recommendations.get("immediate_actions", []))
    else:
        ctx.foods_translated = []
        ctx.practices_translated = []
        ctx.immediate_actions = []

    # Symptom-specific protocol (OS-aware, takes priority over friction-based)
    if symptom_protocol:
        ctx.symptom_insight = symptom_protocol.get("insight", "")
        ctx.symptom_best_food = symptom_protocol.get("best_food")
        ctx.symptom_best_practice = symptom_protocol.get("best_practice")
        ctx.symptom_avoid = symptom_protocol.get("avoid", "")

    return ctx


def _translate_foods(foods: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """Translate food recommendations to plain English."""
    translated = []
    for food in foods[:5]:  # Top 5
        name = food.get("name", "").replace("_", " ").title()
        rasa = food.get("rasa")
        virya = food.get("virya")
        effect = translate_food_quality(rasa, virya)

        translated.append({
            "name": name,
            "effect": effect,
            "score": food.get("score", 0.7),
        })
    return translated


def _translate_practices(practices: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """Translate practice recommendations to plain English."""
    translated = []
    for practice in practices[:5]:  # Top 5
        name = translate_practice_name(practice.get("name", ""))
        duration = practice.get("duration_min", 10)
        intensity = practice.get("intensity", "gentle")

        translated.append({
            "name": name,
            "duration": f"{duration} min",
            "intensity": intensity,
            "score": practice.get("score", 0.7),
        })
    return translated


def _translate_immediate(actions: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """Translate immediate actions to plain English."""
    translated = []
    for action in actions[:3]:  # Top 3
        act = action.get("action", "")
        why = action.get("why", "")

        # Clean up any Sanskrit in the action
        for sanskrit, english in PRACTICE_TRANSLATIONS.items():
            act = act.replace(sanskrit, english)

        translated.append({
            "action": act,
            "why": why,
        })
    return translated


# =============================================================================
# KNOWLEDGE GRAPH → PLAIN ENGLISH TRANSLATORS
# =============================================================================

# Dosha-specific "why" for food recommendations (jargon-free)
DOSHA_FOOD_WHY = {
    "kapha": "helps cut through heaviness naturally",
    "pitta": "cools and settles your system from inside",
    "vata": "warms and grounds your system",
}


def translate_graph_food(food: Dict[str, Any], dosha: str) -> Dict[str, str]:
    """Translate a knowledge graph food to plain English recommendation."""
    name = food.get("display_name") or food.get("name", "").replace("_", " ").title()
    for sanskrit, english in PRACTICE_TRANSLATIONS.items():
        name = name.replace(sanskrit, english)
    why = DOSHA_FOOD_WHY.get(dosha, "good for you right now")
    return {"what": name.lower(), "why": why}


def translate_graph_practice(practice: Dict[str, Any]) -> Dict[str, str]:
    """Translate a knowledge graph practice to plain English recommendation."""
    name = translate_practice_name(
        practice.get("display_name") or practice.get("name", "")
    )
    benefits = practice.get("benefits", [])
    why = benefits[0] if benefits else "helps bring your system back to balance"
    return {"what": name.lower(), "why": why}


def translate_graph_avoid(foods: List[Dict[str, Any]]) -> str:
    """Translate aggravating foods to a plain English 'avoid' string."""
    if not foods:
        return ""
    names = []
    for f in foods[:3]:
        name = f.get("display_name") or f.get("name", "").replace("_", " ")
        names.append(name.lower())
    return ", ".join(names) + " — they can make things worse right now"


def build_jargon_free_prompt_section(ctx: JargonFreeContext) -> str:
    """
    Build the user context section for the LLM prompt.

    Keep it simple. Like notes a friend would jot down.
    """
    sections = []

    # Who they are — simple
    sections.append(f"""WHO THEY ARE
───────────────────────────────────────────────────────────────────────────────
Type: {ctx.operating_system_name} — {ctx.constitution_description}
{ctx.operating_system_description}""")

    # Current state — casual
    sections.append(f"""
RIGHT NOW
───────────────────────────────────────────────────────────────────────────────
Feeling: {ctx.friction_state_name} ({ctx.drift_description})
{ctx.friction_description}

{ctx.friction_quick_reframe}

Watch for: {ctx.body_signals_to_watch}
Energy: {ctx.energy_mode_name} — {ctx.energy_mode_description}""")

    # What helps — direct
    sections.append(f"""
WHAT HELPS
───────────────────────────────────────────────────────────────────────────────
{ctx.what_helps_now}""")

    # Quick actions
    if ctx.immediate_actions:
        actions_text = "\n".join(
            f"  → {a['action']} ({a['why']})"
            for a in ctx.immediate_actions
        )
        sections.append(f"""
Quick things that could help:
{actions_text}""")

    if ctx.foods_translated:
        foods_text = ", ".join(f['name'] for f in ctx.foods_translated[:3])
        sections.append(f"Good foods right now: {foods_text}")

    if ctx.practices_translated:
        practices_text = ", ".join(
            f"{p['name']} ({p['duration']})"
            for p in ctx.practices_translated[:3]
        )
        sections.append(f"Try: {practices_text}")

    return "\n".join(sections)


# =============================================================================
# BODY STATE TRANSLATIONS
# =============================================================================

BODY_DOSHA_TRANSLATIONS = {
    "vata": {
        "name": "running on overdrive",
        "signals": {
            "low_hrv": "body's not recovering well",
            "irregular_sleep": "sleep's been all over the place",
            "restless_sleep": "can't settle at night",
            "light_sleep": "not getting deep rest",
            "cold_extremities": "hands/feet are cold",
            "variable_digestion": "digestion's unpredictable",
            "constipation": "things are... stuck",
            "bloating": "feeling bloated",
            "dehydration": "need more water",
            "shallow_breath": "breath's up in your chest",
            "anxiety": "that anxious feeling",
            "restlessness": "can't sit still",
            "craving_grounding_foods": "wanting warm, heavy foods",
        },
        "what_helps": "slow down, stay warm, get grounded",
    },
    "pitta": {
        "name": "running hot",
        "signals": {
            "elevated_heart_rate": "heart's working hard",
            "elevated_temperature": "body temp's up",
            "insufficient_sleep": "not sleeping enough",
            "intense_exercise": "pushing hard in workouts",
            "overheating": "feeling too warm",
            "hyperactive_digestion": "digestion's in overdrive",
            "intense_hunger": "ravenous hunger",
            "irritability": "getting irritated easily",
            "anger": "that fire's up",
            "frustration": "feeling frustrated",
            "craving_cooling_foods": "wanting cold, sweet foods",
        },
        "what_helps": "cool down, ease off, more play less push",
    },
    "kapha": {
        "name": "feeling heavy",
        "signals": {
            "low_heart_rate": "everything's slow",
            "excess_sleep": "sleeping too much",
            "low_activity": "not moving enough",
            "sedentary": "sitting too long",
            "weight_gain": "body's holding on",
            "sluggish_digestion": "digestion's sluggish",
            "low_appetite": "not hungry",
            "lethargy": "energy's just... low",
            "fatigue": "tired all the time",
            "depression": "feeling heavy inside",
            "mental_sluggishness": "brain fog",
            "craving_stimulating_foods": "wanting light, spicy foods",
        },
        "what_helps": "get moving, try something new, shake it up",
    },
}

BODY_NEED_TRANSLATIONS = {
    "grounding": "Your system needs to settle. Warmth, routine, and slow down.",
    "cooling": "Body's running hot. Ease off, cool down, less intensity.",
    "movement": "Time to shake off the heaviness. Move, try new things.",
    "rest": "You're running on empty. Real rest, not just sleep.",
    "nourishment": "Body's asking to be fed well. Warm, nourishing foods.",
    "balance": "You're doing okay. Just maintain what's working.",
}

BODY_RECOMMENDATION_TRANSLATIONS = {
    # Grounding practices
    "warm_oil_massage": "warm oil self-massage before bed",
    "warm_cooked_foods": "warm, cooked meals (less raw/cold)",
    "regular_routine": "same wake time and sleep time",
    "gentle_yoga": "gentle stretching or slow yoga",

    # Cooling practices
    "cooling_breath": "slow, deep breaths (exhale longer)",
    "avoid_overexertion": "ease up on intense workouts",
    "light_meals": "lighter meals, nothing too heavy",
    "moon_bathing": "evening time outside, cooling",

    # Movement practices
    "brisk_walk": "brisk morning walk",
    "dry_brushing": "dry brushing before shower",
    "light_fasting": "skip a meal if not hungry",
    "stimulating_spices": "add some ginger or pepper",

    # Rest practices
    "earlier_bedtime": "lights out earlier",
    "warm_milk": "warm milk or chamomile before bed",
    "reduce_screens": "screens off an hour before bed",
    "restorative_yoga": "legs up the wall, just rest",

    # Nourishment
    "nourishing_foods": "bone broth, stews, warm grains",
    "warm_soups": "homemade soups",
    "adequate_protein": "enough protein with each meal",
    "digestive_tea": "ginger or fennel tea after meals",

    # General
    "balanced_routine": "stick to your rhythm",
    "mindful_eating": "eat slowly, no distractions",
    "daily_movement": "some movement every day",
    "sleep_hygiene": "consistent sleep schedule",

    # Tension-specific
    "release_neck_shoulders": "shoulder rolls, neck stretches",
    "release_back": "gentle back stretches, cat-cow",
    "release_jaw": "jaw massage, open mouth stretches",
}


def translate_body_state(body_state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Translate body_state to user-friendly descriptions.

    Converts Ayurvedic dosha signals, recommendations, and
    body metrics into everyday language.
    """
    result: Dict[str, Any] = {}

    # Summary
    summary = body_state.get("summary", {})
    overall = summary.get("overall_score", 0.5)

    if overall >= 0.8:
        result["overall_status"] = "Body's doing great"
    elif overall >= 0.6:
        result["overall_status"] = "Body's okay, some things to watch"
    elif overall >= 0.4:
        result["overall_status"] = "Body's asking for attention"
    else:
        result["overall_status"] = "Body needs care"

    # Primary need
    primary_need = summary.get("primary_need", "balance")
    result["primary_need"] = BODY_NEED_TRANSLATIONS.get(
        primary_need,
        "Listen to what your body's telling you"
    )

    # Dosha status
    dosha_body = body_state.get("dosha_body", {})
    dominant = dosha_body.get("dominant_imbalance")

    if dominant:
        dosha_info = BODY_DOSHA_TRANSLATIONS.get(dominant, {})
        result["dosha_status"] = dosha_info.get("name", "something's off")

        # Translate signals
        signals = dosha_body.get(f"{dominant}_signs", {}).get("signals", [])
        translated_signals = []
        for signal in signals[:3]:  # Top 3
            translated = dosha_info.get("signals", {}).get(signal, signal.replace("_", " "))
            translated_signals.append(translated)
        result["body_signals"] = translated_signals

        result["what_helps"] = dosha_info.get("what_helps", "take care of yourself")
    else:
        result["dosha_status"] = "in balance"
        result["body_signals"] = []
        result["what_helps"] = "keep doing what you're doing"

    # Translate recommendations
    raw_recs = summary.get("top_recommendations", [])
    result["recommendations"] = [
        BODY_RECOMMENDATION_TRANSLATIONS.get(rec, rec.replace("_", " "))
        for rec in raw_recs[:4]
    ]

    # Energy
    energy = body_state.get("energy", {})
    energy_level = energy.get("level", 0.5)
    if energy_level >= 0.7:
        result["energy_status"] = "energy's good"
    elif energy_level >= 0.4:
        result["energy_status"] = "energy's okay"
    else:
        result["energy_status"] = "running low"

    # Sleep
    sleep = body_state.get("sleep", {})
    sleep_quality = sleep.get("quality_score")
    if sleep_quality:
        if sleep_quality >= 0.8:
            result["sleep_status"] = "sleeping well"
        elif sleep_quality >= 0.5:
            result["sleep_status"] = "sleep could be better"
        else:
            result["sleep_status"] = "sleep needs work"

    sleep_debt = sleep.get("sleep_debt_hours", 0)
    if sleep_debt > 5:
        result["sleep_debt"] = "significant sleep debt"
    elif sleep_debt > 2:
        result["sleep_debt"] = "a bit behind on sleep"

    # Ojas
    ojas = body_state.get("ojas", {})
    ojas_level = ojas.get("level", 0.5)
    if ojas_level < 0.4:
        result["vitality_status"] = "running on empty — need real rest"
    elif ojas_level < 0.6:
        result["vitality_status"] = "vitality's a bit low"
    else:
        result["vitality_status"] = "good reserves"

    # Tension
    tension = body_state.get("tension_map", {})
    primary_tension = tension.get("primary_holding")
    if primary_tension:
        tension_map = {
            "neck_shoulders": "carrying tension in neck/shoulders",
            "back": "tension in your back",
            "jaw": "holding tension in your jaw",
        }
        result["tension_status"] = tension_map.get(
            primary_tension, f"tension in {primary_tension.replace('_', ' ')}"
        )

    return result


__all__ = [
    "translate_operating_system",
    "translate_friction_state",
    "translate_energy_mode",
    "translate_food_quality",
    "translate_practice_name",
    "translate_constitution",
    "translate_drift_severity",
    "translate_body_state",
    "build_jargon_free_context",
    "build_jargon_free_prompt_section",
    "JargonFreeContext",
    "OPERATING_SYSTEM_DESCRIPTIONS",
    "FRICTION_TRANSLATIONS",
    "ENERGY_MODE_TRANSLATIONS",
    "BODY_DOSHA_TRANSLATIONS",
    "BODY_NEED_TRANSLATIONS",
    "BODY_RECOMMENDATION_TRANSLATIONS",
]
