"""
Context Synthesizer

Compresses all gathered context into a prompt-ready format for the LLM.
This creates the final structured context that guides response generation.

IMPORTANT: All output is jargon-free. No Ayurvedic or yogic terminology
is exposed to the user or the LLM. The science remains—the Sanskrit transforms.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from sakhi.apps.api.services.response.diagnostic_kb import (
    ConstitutionGuidance,
    get_constitution_guidance,
    get_symptom_from_sense,
)
from sakhi.apps.api.services.response.knowledge_gap import (
    ConstitutionContext,
    KnowledgeGap,
    KnownFact,
)
from sakhi.apps.api.services.response.sensing import SenseFrame
from sakhi.apps.api.services.response.strategy import ResponseMode, ResponseStrategy
from sakhi.apps.api.services.response.translation import (
    build_jargon_free_context,
    build_jargon_free_prompt_section,
    translate_operating_system,
    translate_friction_state,
    translate_energy_mode,
    translate_constitution,
    translate_drift_severity,
    JargonFreeContext,
)


# =============================================================================
# SYNTHESIZED CONTEXT
# =============================================================================

@dataclass
class SynthesizedContext:
    """Final synthesized context for LLM prompt."""

    # User's constitutional frame (INTERNAL - not exposed to prompt directly)
    constitution: str = ""  # Internal reference only
    operating_mode: str = ""  # Internal reference only
    operating_system: str = ""  # e.g., "Adaptive-Performance"
    dosha_baseline: Dict[str, float] = field(default_factory=dict)  # Internal

    # Jargon-free context (THIS is what goes to the LLM)
    jargon_free: Optional[JargonFreeContext] = None

    # Persistent context from profile
    life_context: Dict[str, Any] = field(default_factory=dict)  # People, work, ongoing concerns
    life_context_formatted: List[str] = field(default_factory=list)  # Human-readable life context

    # Session context for continuity
    session_summary: str = ""  # Compressed older conversation context

    # What we know
    known_facts: List[str] = field(default_factory=list)  # Human-readable facts
    inferences: List[str] = field(default_factory=list)  # State-based inferences

    # Current symptom context
    domain: str = ""  # "body", "mind", "life", "general"
    symptom: str = ""  # Primary symptom
    symptom_characteristics: Dict[str, str] = field(default_factory=dict)  # Details from message
    temporal: str = ""  # "recurring", "acute", "chronic"
    specificity: str = ""  # "low", "medium", "high"

    # Response guidance
    response_mode: str = ""  # ResponseMode value
    likely_causes: List[str] = field(default_factory=list)  # Constitution-specific (jargon-free)
    tone_guidance: str = ""  # How to frame response
    avoid_suggesting: List[str] = field(default_factory=list)  # What not to recommend

    # Questions to ask (if INQUIRY mode)
    questions_to_ask: List[str] = field(default_factory=list)  # Formatted questions

    # Guardrails
    guardrails: List[str] = field(default_factory=list)

    # Friction state (jargon-free)
    friction_state: str = ""  # "chaos", "intensity", "stagnation", "balanced"
    drift_percentage: float = 0.0  # How far off baseline
    energy_mode: str = ""  # "sattva", "rajas", "tamas"

    # Recommendations (from knowledge graph, will be translated)
    recommendations: Optional[Dict[str, Any]] = None

    # Memory graph context (cross-entity relationships)
    memory_graph_context: Optional[Dict[str, Any]] = None
    competing_entities: List[Dict[str, Any]] = field(default_factory=list)
    supporting_entities: List[Dict[str, Any]] = field(default_factory=list)
    related_context: List[str] = field(default_factory=list)  # Formatted for prompt

    # Body state (physical/somatic intelligence)
    body_state: Optional[Dict[str, Any]] = None  # Lightweight summary
    body_state_translated: Optional[Dict[str, Any]] = None  # Friendly language


# =============================================================================
# GUARDRAILS (JARGON-FREE)
# =============================================================================

JARGON_FREE_GUARDRAILS = [
    "Talk like a friend, not a therapist or doctor. Simple words.",
    "NEVER use Ayurvedic terms (vata, pitta, kapha, dosha, etc.) or clinical language.",
    "Be warm, direct, real. Skip the filler words.",
    "Pick the 1-2 most likely things, don't list options.",
    "Max 2 questions. Make them feel natural, not like an interview.",
    "If we already know something, reference it — don't re-ask.",
    "No diagnosis. You're a friend, not a doctor.",
    "Keep it short. 30-50 words usually. Say what matters.",
    "If you have enough context to help, help first. Only ask a question if the answer would genuinely change your advice.",
    "For new users: ask naturally to learn about them. For returning users: help with what you already know.",
]

# Keep for backwards compatibility
DEFAULT_GUARDRAILS = JARGON_FREE_GUARDRAILS


# =============================================================================
# SYNTHESIS FUNCTIONS
# =============================================================================

def synthesize_context(
    sense: SenseFrame,
    gap: KnowledgeGap,
    strategy: ResponseStrategy,
    session_summary: str = "",
    friction_state: str = "balanced",
    drift_percentage: float = 0.0,
    energy_mode: str = "sattva",
    recommendations: Optional[Dict[str, Any]] = None,
    memory_graph_context: Optional[Dict[str, Any]] = None,
    body_state: Optional[Dict[str, Any]] = None,
    body_state_translated: Optional[Dict[str, Any]] = None,
    symptom_protocol: Optional[Dict[str, Any]] = None,
) -> SynthesizedContext:
    """
    Synthesize all gathered context into a prompt-ready format.

    All output is jargon-free—no Ayurvedic terminology exposed.

    Args:
        sense: SenseFrame from sensing layer
        gap: KnowledgeGap from knowledge gap analysis
        strategy: ResponseStrategy from strategy selection
        session_summary: Compressed older conversation context
        friction_state: Current friction state (chaos/intensity/stagnation/balanced)
        drift_percentage: How far off baseline (0-100)
        energy_mode: Current energy mode (sattva/rajas/tamas)
        recommendations: Optional recommendations from knowledge graph
        memory_graph_context: Optional cross-entity relationship context

    Returns:
        SynthesizedContext for LLM prompt
    """
    ctx = SynthesizedContext()

    # Internal references (not exposed to LLM directly)
    ctx.constitution = _format_constitution(gap.constitution)
    ctx.operating_mode = _format_operating_mode(gap.constitution)
    ctx.operating_system = gap.constitution.operating_system or "Balanced"
    ctx.dosha_baseline = gap.constitution.dosha_baseline or {}

    # Friction state (already jargon-free)
    ctx.friction_state = friction_state
    ctx.drift_percentage = drift_percentage
    ctx.energy_mode = energy_mode
    ctx.recommendations = recommendations

    # Memory graph context (cross-entity relationships)
    ctx.memory_graph_context = memory_graph_context
    if memory_graph_context and memory_graph_context.get("enabled"):
        ctx.competing_entities = memory_graph_context.get("competing_entities", [])
        ctx.supporting_entities = memory_graph_context.get("supporting_entities", [])
        ctx.related_context = _format_memory_graph_context(memory_graph_context)

    # Body state (physical/somatic intelligence)
    ctx.body_state = body_state
    ctx.body_state_translated = body_state_translated

    # Build jargon-free context (THIS is what actually goes to the LLM)
    ctx.jargon_free = build_jargon_free_context(
        operating_system=ctx.operating_system,
        dosha_baseline=ctx.dosha_baseline,
        friction_state=friction_state,
        drift_percentage=drift_percentage,
        energy_mode=energy_mode,
        recommendations=recommendations.get("recommendations") if recommendations else None,
        symptom_protocol=symptom_protocol,
    )

    # Life context (persistent facts about the user)
    ctx.life_context = gap.constitution.life_context or {}
    ctx.life_context_formatted = _format_life_context(ctx.life_context)

    # Session summary for continuity
    ctx.session_summary = session_summary

    # Known facts
    ctx.known_facts = _format_known_facts(strategy.known_to_reference)
    ctx.inferences = strategy.inferences_to_include

    # Symptom context
    ctx.domain = sense.domain
    ctx.symptom = get_symptom_from_sense(sense)
    ctx.symptom_characteristics = _extract_characteristics(sense)
    ctx.temporal = sense.temporal
    ctx.specificity = sense.specificity

    # Response guidance (translate to jargon-free)
    ctx.response_mode = strategy.mode
    guidance = get_constitution_guidance(ctx.symptom, gap.constitution.dominant_dosha)
    if guidance:
        # Translate likely causes to jargon-free
        ctx.likely_causes = _translate_likely_causes(
            guidance.likely_causes[:4],
            gap.constitution.dominant_dosha
        )
        ctx.tone_guidance = guidance.tone
        ctx.avoid_suggesting = guidance.avoid_suggesting[:3]
    else:
        # Default tone based on friction state (jargon-free)
        tone_defaults = {
            "chaos": "warm, grounding, steady",
            "intensity": "measured, clear, cooling",
            "stagnation": "energizing, light, motivating",
            "balanced": "warm, balanced, exploratory",
        }
        ctx.tone_guidance = tone_defaults.get(friction_state, "warm, exploratory, gentle")

    # Questions to ask
    ctx.questions_to_ask = [q.question for q in strategy.questions_to_ask]

    # Guardrails (updated for jargon-free responses)
    ctx.guardrails = JARGON_FREE_GUARDRAILS.copy()

    return ctx


def _translate_likely_causes(causes: List[str], dosha: str) -> List[str]:
    """Translate likely causes to remove any Ayurvedic terminology."""
    translations = {
        "vata": {
            "excess vata": "scattered energy",
            "vata": "variable energy",
            "ama": "accumulated stress",
        },
        "pitta": {
            "excess pitta": "running too hot",
            "pitta": "intensity",
            "ama": "unprocessed emotions",
        },
        "kapha": {
            "excess kapha": "stuck energy",
            "kapha": "heaviness",
            "ama": "accumulated stagnation",
        },
    }
    dosha_map = translations.get(dosha, {})

    translated = []
    for cause in causes:
        cause_lower = cause.lower()
        # Apply all translations
        for sanskrit, english in dosha_map.items():
            cause_lower = cause_lower.replace(sanskrit, english)
        translated.append(cause_lower)
    return translated


def _format_constitution(constitution: ConstitutionContext) -> str:
    """Format constitution into a readable string."""
    if not constitution.dosha_baseline:
        return "Unknown constitution"

    # Find dominant dosha
    dominant = constitution.dominant_dosha
    percentages = constitution.dosha_baseline

    if dominant == "balanced":
        return "Balanced constitution"

    # Format as "Pitta-dominant (45% pitta, 30% vata, 25% kapha)"
    parts = []
    for dosha in ["vata", "pitta", "kapha"]:
        pct = percentages.get(dosha, 0)
        parts.append(f"{int(pct * 100)}% {dosha}")

    return f"{dominant.capitalize()}-dominant ({', '.join(parts)})"


def _format_operating_mode(constitution: ConstitutionContext) -> str:
    """Format operating mode from guna vector."""
    guna = constitution.guna_mode

    mode_descriptions = {
        "sattva": "Sattva-dominant (clarity, balance)",
        "rajas": "Rajas-dominant (activation, drive)",
        "tamas": "Tamas-dominant (inertia, heaviness)",
    }

    return mode_descriptions.get(guna, "Unknown mode")


def _format_life_context(life_context: Dict[str, Any]) -> List[str]:
    """
    Format life_context into human-readable strings for the prompt.

    life_context typically contains:
    - people: {name: relationship, context}
    - work: job title, company, stressors
    - ongoing_concerns: list of persistent topics
    - location, preferences, etc.
    """
    formatted = []

    if not life_context:
        return formatted

    # People/Relationships
    people = life_context.get("people") or life_context.get("relationships") or {}
    if isinstance(people, dict):
        for name, info in people.items():
            if isinstance(info, dict):
                rel = info.get("relationship", "")
                context = info.get("context", "")
                formatted.append(f"{name} ({rel}){': ' + context if context else ''}")
            elif isinstance(info, str):
                formatted.append(f"{name}: {info}")

    # Work context
    work = life_context.get("work") or {}
    if isinstance(work, dict):
        job = work.get("title") or work.get("job") or work.get("role")
        company = work.get("company") or work.get("organization")
        if job:
            work_str = job
            if company:
                work_str += f" at {company}"
            formatted.append(f"Work: {work_str}")
        stressors = work.get("stressors") or work.get("challenges")
        if stressors:
            if isinstance(stressors, list):
                formatted.append(f"Work challenges: {', '.join(stressors)}")
            else:
                formatted.append(f"Work challenges: {stressors}")
    elif isinstance(work, str) and work:
        formatted.append(f"Work: {work}")

    # Ongoing concerns
    concerns = life_context.get("ongoing_concerns") or life_context.get("concerns") or []
    if isinstance(concerns, list) and concerns:
        formatted.append(f"Ongoing concerns: {', '.join(concerns)}")
    elif isinstance(concerns, str) and concerns:
        formatted.append(f"Ongoing concerns: {concerns}")

    # Location
    location = life_context.get("location") or life_context.get("city")
    if location:
        formatted.append(f"Location: {location}")

    # Any other string values
    skip_keys = {"people", "relationships", "work", "ongoing_concerns", "concerns", "location", "city"}
    for key, value in life_context.items():
        if key in skip_keys:
            continue
        if isinstance(value, str) and value:
            formatted.append(f"{key.replace('_', ' ').title()}: {value}")

    return formatted


def _format_known_facts(facts: List[KnownFact]) -> List[str]:
    """Format known facts into human-readable strings."""
    formatted = []
    for fact in facts:
        # Create a concise summary
        recency_prefix = {
            "recent": "Recently mentioned:",
            "moderate": "Previously shared:",
            "old": "Earlier mentioned:",
        }
        prefix = recency_prefix.get(fact.recency, "Known:")
        formatted.append(f"{prefix} {fact.value}")

    return formatted


def _format_memory_graph_context(graph_ctx: Dict[str, Any]) -> List[str]:
    """
    Format memory graph context into human-readable strings for the prompt.

    This surfaces cross-entity relationships like:
    - Competing entities (both want morning time slot)
    - Supporting entities (meditation supports sleep goal)
    - Related patterns and themes
    """
    formatted = []

    # Competing entities (important for decision-making)
    competing = graph_ctx.get("competing_entities", [])
    for comp in competing[:3]:  # Limit to top 3
        entity_a = comp.get("entity_a", {}).get("label", "")
        entity_b = comp.get("entity_b", {}).get("label", "")
        resource = comp.get("shared_resource", "")
        if entity_a and entity_b:
            if resource:
                formatted.append(f"Tension: {entity_a} and {entity_b} both need {resource}")
            else:
                formatted.append(f"Tension: {entity_a} competes with {entity_b}")

    # Supporting entities (reinforce positive connections)
    supporting = graph_ctx.get("supporting_entities", [])
    for sup in supporting[:3]:  # Limit to top 3
        source = sup.get("source", {}).get("label", "")
        target = sup.get("target", {}).get("label", "")
        relation = sup.get("relation", "supports")
        if source and target:
            formatted.append(f"Connection: {source} {relation} {target}")

    # Related nodes (broader context)
    related = graph_ctx.get("related_nodes", [])
    for rel in related[:3]:  # Limit to top 3
        label = rel.get("label", "")
        kind = rel.get("kind", "")
        if label and kind:
            kind_readable = kind.replace("_", " ")
            formatted.append(f"Related {kind_readable}: {label}")

    return formatted


def _extract_characteristics(sense: SenseFrame) -> Dict[str, str]:
    """Extract any specific characteristics from the message."""
    chars = {}
    text_lower = sense.raw_text.lower()

    # Location
    location_words = ["left", "right", "front", "back", "temple", "forehead", "side"]
    for loc in location_words:
        if loc in text_lower:
            chars["location"] = loc
            break

    # Quality
    quality_words = {
        "sharp": "sharp",
        "dull": "dull",
        "throbbing": "throbbing",
        "pulsing": "pulsing",
        "burning": "burning",
        "heavy": "heavy",
        "pressure": "pressure-like",
        "tight": "tight",
    }
    for word, label in quality_words.items():
        if word in text_lower:
            chars["quality"] = label
            break

    # Timing
    timing_words = {
        "morning": "morning",
        "afternoon": "afternoon",
        "evening": "evening",
        "night": "night",
        "after meal": "after meals",
        "after work": "after work",
        "after meeting": "after meetings",
        "after screen": "after screen time",
    }
    for phrase, label in timing_words.items():
        if phrase in text_lower:
            chars["timing"] = label
            break

    return chars


def _build_body_state_section(body_translated: Optional[Dict[str, Any]]) -> str:
    """
    Build body state section for prompt if meaningful data exists.

    Only includes body state if we have actual health data (not defaults).
    """
    if not body_translated:
        return ""

    # Check if we have meaningful content
    overall = body_translated.get("overall_status", "")
    primary_need = body_translated.get("primary_need", "")
    dosha_status = body_translated.get("dosha_status", "")

    # Skip if default/balanced state
    if dosha_status == "in balance" and "okay" in overall.lower():
        return ""

    lines = []
    lines.append("""
───────────────────────────────────────────────────────────────────────────────
BODY RIGHT NOW
───────────────────────────────────────────────────────────────────────────────""")

    # Overall status
    if overall:
        lines.append(f"- {overall}")

    # Dosha status (translated to friendly)
    if dosha_status and dosha_status != "in balance":
        lines.append(f"- {dosha_status.capitalize()}")

    # What helps
    what_helps = body_translated.get("what_helps", "")
    if what_helps and what_helps != "keep doing what you're doing":
        lines.append(f"- What helps: {what_helps}")

    # Body signals (top 2)
    signals = body_translated.get("body_signals", [])
    if signals:
        for signal in signals[:2]:
            lines.append(f"- {signal}")

    # Energy status
    energy = body_translated.get("energy_status", "")
    if energy and energy != "energy's okay":
        lines.append(f"- Energy: {energy}")

    # Sleep status
    sleep = body_translated.get("sleep_status", "")
    if sleep and sleep != "sleeping well":
        lines.append(f"- Sleep: {sleep}")

    # Sleep debt
    sleep_debt = body_translated.get("sleep_debt", "")
    if sleep_debt:
        lines.append(f"- {sleep_debt.capitalize()}")

    # Tension
    tension = body_translated.get("tension_status", "")
    if tension:
        lines.append(f"- {tension.capitalize()}")

    # Vitality
    vitality = body_translated.get("vitality_status", "")
    if vitality and "good reserves" not in vitality:
        lines.append(f"- Vitality: {vitality}")

    # Only return if we have more than just the header
    if len(lines) > 1:
        return "\n".join(lines)
    return ""


# =============================================================================
# DECISION REASONING
# =============================================================================

def _build_decision_reasoning(synth: SynthesizedContext) -> str:
    """
    Build a clear explanation of WHY the response mode was chosen.
    This helps the LLM understand the reasoning behind the decision.
    """
    mode = synth.response_mode
    known_count = len(synth.known_facts)
    has_inferences = len(synth.inferences) > 0
    specificity = synth.specificity
    questions_count = len(synth.questions_to_ask)

    if mode == ResponseMode.RESPOND:
        reasoning = f"""Mode chosen: RESPOND (provide guidance)
Reasoning:
- User provided {specificity} specificity in their message
- We have enough context to offer constitution-specific guidance
- No critical information gaps remain

Action: Acknowledge → Provide insight → Offer one practical suggestion → Check in"""

    elif mode == ResponseMode.CONNECT_AND_INQUIRE:
        known_summary = f"{known_count} known facts" if known_count > 0 else "some inferences"
        reasoning = f"""Mode chosen: CONNECT_AND_INQUIRE (reference history + ask targeted question)
Reasoning:
- We have {known_summary} from their history
- But we still need {questions_count} more piece(s) of information
- We can show we remember them while gathering what's missing

Action: Acknowledge → Reference what we know → Ask 1-2 targeted questions"""

    else:  # INQUIRE
        reasoning = f"""Mode chosen: INQUIRE (gather information first)
Reasoning:
- This appears to be a first interaction about this concern
- User message has {specificity} specificity
- We need more information before offering guidance
- Questions are prioritized for their constitution ({synth.constitution})

Action: Acknowledge → Frame with constitution → Ask 1-2 targeted questions"""

    return reasoning


# =============================================================================
# PROMPT BUILDER
# =============================================================================

def build_adaptive_prompt(
    user_text: str,
    synth: SynthesizedContext,
) -> str:
    """
    Build the final adaptive response prompt.

    IMPORTANT: This prompt is COMPLETELY JARGON-FREE.
    No Ayurvedic or yogic terminology is exposed to the LLM.

    Args:
        user_text: Original user message
        synth: SynthesizedContext with all guidance

    Returns:
        Formatted prompt string
    """
    # Get jargon-free context
    jf = synth.jargon_free
    if not jf:
        # Fallback: build it now
        jf = build_jargon_free_context(
            operating_system=synth.operating_system or "Balanced",
            dosha_baseline=synth.dosha_baseline or {},
            friction_state=synth.friction_state or "balanced",
            drift_percentage=synth.drift_percentage,
            energy_mode=synth.energy_mode or "sattva",
            recommendations=synth.recommendations.get("recommendations") if synth.recommendations else None,
        )

    # Format known facts section
    known_section_text = ""
    if synth.known_facts or synth.inferences:
        known_items = synth.known_facts + synth.inferences
        known_section_text = "\n".join(f"- {item}" for item in known_items)
    else:
        known_section_text = "- First interaction about this concern — we have no prior context yet"

    # Format symptom characteristics
    chars_section = ""
    if synth.symptom_characteristics:
        chars_items = [f"{k}: {v}" for k, v in synth.symptom_characteristics.items()]
        chars_section = "From their message:\n" + "\n".join(f"  • {item}" for item in chars_items) + "\n"

    # Format likely causes (already translated to jargon-free)
    causes_section = ""
    if synth.likely_causes:
        causes_section = f"Likely contributors for their pattern: {', '.join(synth.likely_causes)}\n"

    # Format questions to ask
    questions_section = ""
    if synth.questions_to_ask and synth.response_mode != ResponseMode.RESPOND:
        questions_section = "Questions to choose from (pick max 2):\n"
        questions_section += "\n".join(f"  • {q}" for q in synth.questions_to_ask) + "\n"

    # Format avoid section
    avoid_section = ""
    if synth.avoid_suggesting:
        avoid_section = f"Avoid suggesting: {', '.join(synth.avoid_suggesting)}\n"

    # Format guardrails
    guardrails_formatted = "\n".join("• " + g for g in synth.guardrails)

    # Format life context section
    life_context_section = ""
    if synth.life_context_formatted:
        life_context_section = "\n".join(f"- {item}" for item in synth.life_context_formatted)
    else:
        life_context_section = "- No persistent context yet"

    # Format memory graph relationships section
    relationships_section = ""
    if synth.related_context:
        relationships_section = "\n".join(f"- {item}" for item in synth.related_context)

    # Format body state section
    body_state_section = _build_body_state_section(synth.body_state_translated)

    # Format session summary section (for pronoun/reference resolution)
    session_summary_section = ""
    if synth.session_summary:
        session_summary_section = f"""
EARLIER IN THIS CONVERSATION
───────────────────────────────────────────────────────────────────────────────
{synth.session_summary}
"""

    # Build decision reasoning section
    decision_reasoning = _build_decision_reasoning_jargon_free(synth, jf)

    # Format response template guidance
    template_guidance = _get_template_guidance_jargon_free(synth.response_mode)

    # Build recommendations section (jargon-free)
    recommendations_section = _build_recommendations_section_jargon_free(jf)

    prompt = f"""You are Sakhi — a friend who really gets this person. You understand their patterns.

VOICE: Talk like a friend. Not a therapist, not formal. Just real.
- Simple words. Short sentences. Say what matters.
- No Ayurvedic jargon ever (vata, pitta, kapha, dosha = never say these).
- Warm but direct. Skip fluff.

───────────────────────────────────────────────────────────────────────────────
THEM: {jf.operating_system_name} — {jf.constitution_description}
───────────────────────────────────────────────────────────────────────────────
{jf.operating_system_description}

Right now: {jf.friction_state_name} ({jf.drift_description})
{jf.friction_description}

{jf.friction_quick_reframe}

Watch for: {jf.body_signals_to_watch}
Energy: {jf.energy_mode_name} — {jf.energy_mode_description}
{session_summary_section}
───────────────────────────────────────────────────────────────────────────────
THEIR LIFE
───────────────────────────────────────────────────────────────────────────────
{life_context_section}
{body_state_section}{f'''
───────────────────────────────────────────────────────────────────────────────
CONNECTIONS (things pulling in different directions or supporting each other)
───────────────────────────────────────────────────────────────────────────────
{relationships_section}
''' if relationships_section else ''}
───────────────────────────────────────────────────────────────────────────────
WHAT WE KNOW (don't ask again)
───────────────────────────────────────────────────────────────────────────────
{known_section_text}

───────────────────────────────────────────────────────────────────────────────
WHAT THEY'RE TALKING ABOUT
───────────────────────────────────────────────────────────────────────────────
Area: {synth.domain}
About: {synth.symptom}
Pattern: {synth.temporal}
{chars_section}
───────────────────────────────────────────────────────────────────────────────
HOW TO RESPOND: {synth.response_mode}
───────────────────────────────────────────────────────────────────────────────
{decision_reasoning}

Tone: {synth.tone_guidance}
{causes_section}{questions_section}{avoid_section}
───────────────────────────────────────────────────────────────────────────────
{recommendations_section}RULES
───────────────────────────────────────────────────────────────────────────────
{guardrails_formatted}

{template_guidance}

───────────────────────────────────────────────────────────────────────────────
THEY SAID:
───────────────────────────────────────────────────────────────────────────────
{user_text.strip()}

───────────────────────────────────────────────────────────────────────────────
YOUR RESPONSE (like a friend would say it — warm, simple, real):
───────────────────────────────────────────────────────────────────────────────"""

    return prompt.strip()


def _build_recommendations_section_jargon_free(jf: JargonFreeContext) -> str:
    """Build simple, friendly recommendations."""
    sections = []

    # Symptom-specific protocol takes priority (OS-aware, 1-2 targeted recs)
    if jf.symptom_insight:
        sections.append(f"""WHAT COULD HELP
───────────────────────────────────────────────────────────────────────────────
{jf.symptom_insight}""")
        if jf.symptom_best_food:
            sections.append(f"\n  → {jf.symptom_best_food['what']} — {jf.symptom_best_food['why']}")
        if jf.symptom_best_practice:
            sections.append(f"  → {jf.symptom_best_practice['what']} — {jf.symptom_best_practice['why']}")
        if jf.symptom_avoid:
            sections.append(f"Skip: {jf.symptom_avoid}")
        sections.append("")
        return "\n".join(sections)

    # Fallback: generic friction-state recommendations
    sections.append(f"""WHAT COULD HELP
───────────────────────────────────────────────────────────────────────────────
{jf.what_helps_now}""")

    if jf.immediate_actions:
        sections.append("\nQuick things:")
        for action in jf.immediate_actions[:2]:
            sections.append(f"  → {action['action']}")

    if jf.foods_translated:
        foods = ", ".join(f['name'] for f in jf.foods_translated[:3])
        sections.append(f"\nGood to eat: {foods}")

    if jf.practices_translated:
        practices = ", ".join(p['name'] for p in jf.practices_translated[:2])
        sections.append(f"Try: {practices}")

    sections.append("")
    return "\n".join(sections)


def _build_decision_reasoning_jargon_free(synth: SynthesizedContext, jf: JargonFreeContext) -> str:
    """
    Simple explanation of what kind of response to give.
    """
    mode = synth.response_mode
    known_count = len(synth.known_facts)
    questions_count = len(synth.questions_to_ask)

    if mode == ResponseMode.RESPOND:
        reasoning = f"""Give them something useful.
We know enough. They're {jf.friction_state_name} right now — that tells us what might help."""

    elif mode == ResponseMode.CONNECT_AND_INQUIRE:
        reasoning = f"""Show we remember them, then ask what we're missing.
We know {known_count} things already. Need {questions_count} more piece(s)."""

    else:  # INQUIRE
        reasoning = f"""Ask first, advise later.
This is new territory — need to understand more before suggesting anything."""

    return reasoning


def _get_template_guidance_jargon_free(mode: str) -> str:
    """How to structure the response — kept simple."""
    if mode == ResponseMode.RESPOND:
        return """HOW TO SAY IT:
1. Acknowledge what they're feeling (brief)
2. Share one insight — "For you, this usually means..."
3. One suggestion — something they can actually do
4. Check in — "Does that land?" or "Worth a try?"

Keep it short. 2-4 sentences total."""

    elif mode == ResponseMode.CONNECT_AND_INQUIRE:
        return """HOW TO SAY IT:
1. Brief acknowledgment
2. Connect to something we know ("I remember you mentioned...")
3. Only ask if the answer would change your advice — if not, offer help instead
4. Max 1 question, framed naturally

Keep it conversational. Not an interview."""

    else:  # INQUIRE
        return """HOW TO SAY IT:
1. Acknowledge this tells us something
2. Ask 1-2 questions that actually help

Don't list options. Just ask what you need to know."""


# Legacy function for backwards compatibility
def _build_recommendations_section(synth: SynthesizedContext) -> str:
    """Build recommendations section if available. DEPRECATED: Use jargon-free version."""
    if synth.jargon_free:
        return _build_recommendations_section_jargon_free(synth.jargon_free)

    if not synth.recommendations:
        return ""

    # Fallback to old behavior if no jargon-free context
    recs = synth.recommendations
    sections = []

    immediate = recs.get("immediate_actions", [])
    if immediate:
        sections.append("Quick actions now:")
        for action in immediate[:2]:
            act = action.get("action", "")
            why = action.get("why", "")
            sections.append(f"  • {act} — {why}")

    foods = recs.get("foods_now", [])
    if foods:
        food_names = [f.get("name", "").replace("_", " ") for f in foods[:3]]
        sections.append(f"Foods that help: {', '.join(food_names)}")

    if sections:
        return "\n".join(sections) + "\n\n"
    return ""


def _get_template_guidance(mode: str) -> str:
    """Get response template guidance based on mode."""
    if mode == ResponseMode.RESPOND:
        return """RESPONSE TEMPLATE:
[ACKNOWLEDGE] Brief acknowledgment of their symptom
[INSIGHT] For their constitution, this often happens when... (constitution-specific cause)
[SUGGESTION] One practical, doable suggestion
[CHECK] Does that resonate? / Does that feel doable?"""

    elif mode == ResponseMode.CONNECT_AND_INQUIRE:
        return """RESPONSE TEMPLATE:
[ACKNOWLEDGE] Brief acknowledgment of symptom
[CONNECT] Reference what we know (e.g., "I notice sleep has been rough...")
[ASK] 1-2 targeted questions from the list above"""

    else:  # INQUIRE
        return """RESPONSE TEMPLATE:
[ACKNOWLEDGE] Brief acknowledgment that this tells us something
[FRAME] "Given your nature..." or "For your system..."
[ASK] 1-2 targeted questions from the list above"""


__all__ = [
    "SynthesizedContext",
    "synthesize_context",
    "build_adaptive_prompt",
    "DEFAULT_GUARDRAILS",
    "JARGON_FREE_GUARDRAILS",
]
