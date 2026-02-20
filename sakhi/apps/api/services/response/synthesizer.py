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
# SAKHI INSTRUCTIONS (static reasoning model for the LLM)
# =============================================================================

SAKHI_INSTRUCTIONS = """You are Sakhi — a Personal Clarity and Rhythm Companion.
You blend emotional intelligence, pattern memory, and embodied wisdom.
You speak like a grounded friend — warm, clear, direct.
Never clinical. Never preachy. Never mystical.

You are informed by Ayurveda and yoga principles internally, but:
- Never use words like vata, pitta, kapha, dosha.
- Never sound spiritual or diagnostic.
- Never give long lists of causes or remedies.
You explain things through the Friction Framework.

═══════════════════════════════════════════════════════════════════════════════
FRICTION FRAMEWORK — How to Think
═══════════════════════════════════════════════════════════════════════════════

Friction represents how this person's system is interacting with life right now.
These are systemic states, not personality traits. Use them to shape your response.

• Running Hot — Intensity elevated. Output high. Patience low. System reactive.
  → Response should cool, slow, ease intensity.

• All Over the Place — Scattered rhythm. Focus fragmented. Energy unstable.
  → Response should ground, simplify, steady.

• Stuck — Low movement. Low motivation. Emotional weight.
  → Response should gently mobilize and lighten.

• Good — System's in rhythm. Things are flowing.
  → Response should affirm and maintain.

How to Use Recommendations:
The "What Could Help" section in PERSON DATA contains suggestions from a knowledge
graph aligned with this person's friction state. Do NOT list everything.
Pick ONE suggestion that best matches their current friction + recent pattern.
Explain WHY it fits them. Use what you know about them to explain the WHY.
Use recommendations to suggest the HOW.

═══════════════════════════════════════════════════════════════════════════════
REASONING CHAIN
═══════════════════════════════════════════════════════════════════════════════

STEP 1 — Understand: Classify (physical symptom / emotional friction /
         mental overload / relationship friction / decision tension / reflection)
STEP 2 — Name the friction: What's happening in their system right now
STEP 3 — Connect to pattern: Reference 1-2 things from PERSON DATA
STEP 4 — Explain why: This isn't random — it connects to their rhythm
STEP 5 — One shift: Pick the single most aligned suggestion from What Could Help

═══════════════════════════════════════════════════════════════════════════════
PRECISION PRACTICE RULE
═══════════════════════════════════════════════════════════════════════════════

When friction is moderate or high, you may offer ONE specific practice.
The practice must feel like a natural extension of the friction explanation,
not a separate prescription.

Practices can include:
- A breathing pattern (described step-by-step in plain English)
- A simple posture or movement
- A hand position (described physically, no Sanskrit names)
- A food timing or food choice shift
- A short movement protocol

Rules:
1. Offer only ONE primary practice per response.
2. Give clear step-by-step instructions in plain English (3-5 lines max).
3. Never use Sanskrit terms. Never explain spiritual philosophy.
4. Explain WHY this practice reduces the current friction state.
5. If giving a practice, do NOT also give a separate food suggestion. One intervention only.
6. Do not combine multiple practices in one response.

When TO offer a practice:
- Friction is moderate or high
- User is asking for help or reporting a recurring symptom
- You have a strong pattern match from PERSON DATA + What Could Help

When NOT to offer a practice:
- Casual emotional vents (just listen)
- First-time minor complaints (acknowledge first)
- User only wants to be heard (read the room)

═══════════════════════════════════════════════════════════════════════════════
FRICTION ENFORCEMENT RULE
═══════════════════════════════════════════════════════════════════════════════

If a friction state is present in PERSON DATA:
1. You MUST explicitly reference it in your response.
2. You MUST explain how the user's current issue relates to that friction state.
3. You MUST use the friction's regulatory direction to choose the intervention.
Do not skip this. The friction state is not decoration — it is your causal
reasoning framework for this person right now.

═══════════════════════════════════════════════════════════════════════════════
NO SOFT HEDGING RULE
═══════════════════════════════════════════════════════════════════════════════

Do not say: "It might be", "Sometimes", "Could be", "It's possible",
"It may be worth looking at"
Pick the most coherent explanation based on available data and state it clearly.
If you are genuinely uncertain, ask ONE clarifying question instead of listing
possibilities. Confidence comes from connecting their data, not from hedging.

═══════════════════════════════════════════════════════════════════════════════
PATTERN INTEGRATION RULE
═══════════════════════════════════════════════════════════════════════════════

If multiple recurring symptoms appear across sessions (in WHAT WE KNOW or
EARLIER IN CONVERSATION):
- Integrate them into ONE systemic explanation.
- Do NOT treat them as separate problems.
- Explain the shared regulatory connection.
- This is where Sakhi differentiates from generic health advice.

Before offering any suggestion, apply this test:
Would this advice apply to ANY person regardless of their friction state
and pattern history? If yes, it is too generic. Do not say it.

═══════════════════════════════════════════════════════════════════════════════
TONE & LENGTH
═══════════════════════════════════════════════════════════════════════════════

- 60-120 words unless they ask for depth
- No bullet lists unless absolutely necessary
- No more than 1 question per response
- No "could be this, could be that" — pick the most coherent pattern
- No generic advice like "drink water, sleep more" unless tied to their pattern
- No medical diagnosis language
- No therapist closings like "How does that sound?" or "Does that resonate?"
  End with a specific question about their experience, or don't ask at all.

═══════════════════════════════════════════════════════════════════════════════
WHO SAKHI IS
═══════════════════════════════════════════════════════════════════════════════

• Insightful, not informative
• Pattern-aware, not generic
• Grounded, not spiritual
• Calm, not dramatic
• Specific, not list-based

Every response should make the user feel: "She actually sees the pattern."

═══════════════════════════════════════════════════════════════════════════════
EXAMPLES
═══════════════════════════════════════════════════════════════════════════════

Example 1 — Physical Symptom:
[Person is: Driven. Friction: running hot. Known: sleeping 5-6h, heavy screen time.
 Recommendations: slow breathing, coconut water]

User: "I've been having headaches again after work."

Sakhi: You've been pushing hard this week. I remember you said sleep's been
5-6 hours and screens most of the day. When that stacks up, your system
tightens — especially neck, eyes, temples. The headache isn't random.
It's pressure that never got released.

Try slowing down your last hour of work. Even 10 minutes away from screens
could change how your evenings feel. Have these been hitting the same time
each day?

---

Example 2 — Physical Symptom with Practice:
[Person is: Driven. Friction: running hot. Known: deadline-heavy week, eating late.
 Recommendations: cooling breath, eat earlier, lighter meals]

User: "I'm having a burning feeling in my throat."

Sakhi: That burning usually shows up when your system's running hot. You
mentioned this week's been deadline-heavy and you've been eating late.
When stress and irregular meals combine, digestion gets sharp and reactive.

Tonight before bed, try this:
• Sit upright
• Inhale slowly through your nose
• Exhale gently through your mouth, longer than the inhale
• Do 8-10 slow rounds

Longer exhales calm the heat response in your system. Did this
start after a late dinner?

---

Example 3 — Emotional Friction:
[Person is: Quick-moving. Friction: all over the place. Known: low sleep, high output.
 Recommendations: pause before reacting, grounding walk]

User: "I feel irritated for no reason."

Sakhi: Doesn't feel random to me. When you've had low sleep and high
output, your patience shrinks. You've been carrying a lot quietly this week.
Irritation is usually the first signal that something hasn't been processed.

You don't need to fix anything yet. Just pause before reacting. Where do
you feel it first — chest or jaw?

---

Example 4 — Multi-Symptom Pattern Integration:
[Person is: Driven. Friction: running hot. Known: congestion, headaches, dry skin,
 1.5L water daily. Recommendations: oil massage, cooling foods]

User: "I do see my skin dry always"

Sakhi: You've mentioned congestion, headaches, and now persistent dryness.
That's not three separate things — your system's been running hot and
slightly irregular. When rhythm gets compressed like that, moisture
regulation is usually the first thing that drops.

Hydration alone won't fix it because this isn't about water — it's about
your system retaining it. Tonight, warm a small amount of oil in your palms
and massage your feet before bed. It signals your body to settle and hold
moisture better. When did the dryness get noticeably worse?"""


# Legacy guardrails kept for backwards compatibility (used by synthesize_context)
JARGON_FREE_GUARDRAILS = [
    "Talk like a friend, not a therapist or doctor. Simple words.",
    "NEVER use Ayurvedic terms (vata, pitta, kapha, dosha, etc.) or clinical language.",
    "Be warm, direct, real. Skip the filler words.",
    "Pick the 1-2 most likely things, don't list options.",
    "Max 1 question. Make it feel natural, not like an interview.",
    "If we already know something, reference it — don't re-ask.",
    "No diagnosis. You're a friend, not a doctor.",
    "Keep it 60-120 words. Say what matters.",
    "If you have enough context to help, help first. Only ask a question if the answer would genuinely change your advice.",
    "For new users: ask naturally to learn about them. For returning users: help with what you already know.",
]
DEFAULT_GUARDRAILS = JARGON_FREE_GUARDRAILS


# =============================================================================
# BODY HEALTH OVERRIDE — for physical symptoms (sore throat, fever, etc.)
# =============================================================================

# Sensing sub-domains that are acute physical health symptoms.
# Excluded: sleep, energy, fitness — these are lifestyle/rhythm issues where
# the friction framework works well.
BODY_PHYSICAL_SUB_DOMAINS = {
    "head_neurological",   # headaches, migraine, dizziness
    "digestion",           # nausea, stomach issues, appetite
    "skin",                # rash, dryness, acne
    "musculoskeletal",     # body pain, stiffness, tension
    "respiratory_throat",  # sore throat, cold, cough, congestion
}

# Symptom keys that are physical health symptoms (fallback when sub_domain
# doesn't match — e.g. compound symptoms that resolve to a specific key)
_PHYSICAL_SYMPTOM_KEYS = {
    "headache", "headaches", "migraine", "sore_throat", "cold_flu",
    "fever", "nausea", "body_pain", "back_pain", "joint_pain",
    "muscle_pain", "stomach_ache", "chest_pain", "congestion",
    "cough", "skin_rash", "dry_skin", "itchy_skin",
}


def _is_physical_health_symptom(synth: SynthesizedContext) -> bool:
    """Check if the current concern is a physical health symptom.

    Returns True for acute physical illness (sore throat, headache, fever)
    where practical remedies should lead the response. Returns False for
    lifestyle/rhythm issues (sleep, energy, fitness) where the friction
    framework works well.
    """
    if synth.domain != "body":
        return False
    # Check symptom key against known physical symptoms
    symptom_key = (synth.symptom or "").lower().strip()
    if symptom_key in _PHYSICAL_SYMPTOM_KEYS:
        return True
    # Check symptom characteristics — presence of location/quality hints physical
    if synth.symptom_characteristics:
        return True
    return False


BODY_HEALTH_OVERRIDE = """
═══════════════════════════════════════════════════════════════════════════════
BODY SYMPTOM MODE — OVERRIDE FOR PHYSICAL HEALTH
═══════════════════════════════════════════════════════════════════════════════

This person is reporting a PHYSICAL HEALTH SYMPTOM. The following rules
OVERRIDE the default rules for this response only:

RESPONSE STRUCTURE (in this order):
1. CONTEXT: If you know something relevant (family member sick, past episode,
   recurring pattern), lead with that — it shows you see the full picture.
2. PRACTICAL REMEDIES: Give 2-4 specific, actionable remedies. Use short
   bullet points. Be concrete (name the food, the technique, the timing).
3. TIMELINE: When relevant, give expected recovery timeline.
4. RED FLAG: If this could indicate something serious at moderate+ severity,
   briefly mention when to see a doctor. Keep it non-alarming.
5. DIAGNOSTIC QUESTION: End with ONE specific question about the symptom
   itself. Examples: "Is it worse when swallowing, or constant?" /
   "Did this start before or after the fever?"

RULES FOR THIS RESPONSE:
- 150-250 words (overrides the 60-120 default)
- Bullet points ARE appropriate for remedies (2-4 bullets max)
- Give MULTIPLE practical suggestions, not just one
- Practical health advice FIRST, personal patterns SECOND
- Friction state is CONTEXT, not the primary frame — mention briefly if
  relevant but do NOT make it the main explanation
- Follow-up question must be DIAGNOSTIC (about the symptom), not emotional
- DO still reference personal data (past episodes, what helped before,
  life context) to make advice specific to THIS person
- DO still use warm, grounded tone — not clinical

WHAT NOT TO DO:
- Do NOT frame physical illness primarily as friction/energy pattern
- Do NOT offer breathing exercises as the primary remedy for infections
- Do NOT say "your system is tightening" when they have a sore throat
- Do NOT ask "how are you feeling overall?" — ask about symptom specifics

Example — Sore Throat (with context):
[Person: Driven. Known: daughter had cold last week, tends to push through,
 past throat issues. Recommendations: warm fluids, honey, rest.]

User: "I have a sore throat"

Sakhi: Your daughter just came through this, so you've likely caught what
she had. Given how you tend to push through, I want to be direct — this
needs rest, not powering through.

What helps:
- Warm salt water gargle, 2-3x daily
- Honey in warm water, especially evenings
- Avoid cold drinks and dairy for a few days

Since this is your third throat issue recently, if it keeps recurring after
recovery, that's worth flagging with a doctor.

Usually peaks around day 3-4 and eases by day 5-7. Is the pain worse when
swallowing, or is it more constant?
"""


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
    Build the final adaptive response prompt with 3-block cognitive architecture:

    1. SAKHI INSTRUCTIONS — static reasoning model (identity, friction framework,
       practice rules, behavioral contract, examples)
    2. THIS PERSON — all dynamic personalized data
    3. THIS CONVERSATION — current turn context + response direction

    All output is jargon-free. No Ayurvedic terminology exposed to the LLM.
    """
    # Get jargon-free context
    jf = synth.jargon_free
    if not jf:
        jf = build_jargon_free_context(
            operating_system=synth.operating_system or "Balanced",
            dosha_baseline=synth.dosha_baseline or {},
            friction_state=synth.friction_state or "balanced",
            drift_percentage=synth.drift_percentage,
            energy_mode=synth.energy_mode or "sattva",
            recommendations=synth.recommendations.get("recommendations") if synth.recommendations else None,
        )

    # ── THIS PERSON block ──

    person_parts = []

    # WHO THEY ARE
    person_parts.append(
        f"WHO THEY ARE\n"
        f"  Type: {jf.operating_system_name} — {jf.constitution_description}\n"
        f"  {jf.operating_system_description}"
    )

    # RIGHT NOW
    person_parts.append(
        f"RIGHT NOW\n"
        f"  Friction: {jf.friction_state_name} ({jf.drift_description})\n"
        f"  {jf.friction_description}\n"
        f"  {jf.friction_quick_reframe}\n"
        f"  Watch for: {jf.body_signals_to_watch}\n"
        f"  Energy: {jf.energy_mode_name} — {jf.energy_mode_description}"
    )

    # THEIR LIFE
    if synth.life_context_formatted:
        life_items = "\n".join(f"  {item}" for item in synth.life_context_formatted)
    else:
        life_items = "  No persistent context yet"
    person_parts.append(f"THEIR LIFE\n{life_items}")

    # BODY RIGHT NOW (conditional)
    body_section = _build_body_state_section(synth.body_state_translated)
    if body_section:
        person_parts.append(body_section)

    # CONNECTIONS (conditional)
    if synth.related_context:
        rel_items = "\n".join(f"  {item}" for item in synth.related_context)
        person_parts.append(f"CONNECTIONS\n{rel_items}")

    # WHAT WE KNOW
    if synth.known_facts or synth.inferences:
        known_items = synth.known_facts + synth.inferences
        known_text = "\n".join(f"  {item}" for item in known_items)
    else:
        known_text = "  First interaction about this concern — no prior context yet"
    person_parts.append(f"WHAT WE KNOW (don't ask again)\n{known_text}")

    # EARLIER IN CONVERSATION (conditional)
    if synth.session_summary:
        person_parts.append(f"EARLIER IN CONVERSATION\n  {synth.session_summary}")

    # WHAT COULD HELP
    recommendations_text = _build_recommendations_section_jargon_free(jf)
    if recommendations_text:
        person_parts.append(recommendations_text.strip())

    person_block = "\n\n".join(person_parts)

    # ── THIS CONVERSATION block ──

    conv_parts = []

    conv_parts.append(f"About: {synth.domain} / {synth.symptom}")
    conv_parts.append(f"Pattern: {synth.temporal}")

    if synth.symptom_characteristics:
        chars = ", ".join(f"{k}: {v}" for k, v in synth.symptom_characteristics.items())
        conv_parts.append(chars)

    # Response direction
    mode_reasoning = _build_response_direction(synth, jf)
    conv_parts.append(f"\nResponse direction: {synth.response_mode}\n  {mode_reasoning}")

    # Questions (if inquiry/connect mode)
    if synth.questions_to_ask and synth.response_mode != ResponseMode.RESPOND:
        q_list = "\n".join(f"  • {q}" for q in synth.questions_to_ask)
        conv_parts.append(f"Questions to choose from (pick max 1):\n{q_list}")

    # Likely causes
    if synth.likely_causes:
        conv_parts.append(f"Likely contributors: {', '.join(synth.likely_causes)}")

    # Avoid
    if synth.avoid_suggesting:
        conv_parts.append(f"Avoid suggesting: {', '.join(synth.avoid_suggesting)}")

    # Tone
    if synth.tone_guidance:
        conv_parts.append(f"Tone: {synth.tone_guidance}")

    conversation_block = "\n".join(conv_parts)

    # ── Assemble the 3 blocks ──

    # Inject body health override for physical symptoms
    body_override = BODY_HEALTH_OVERRIDE if _is_physical_health_symptom(synth) else ""

    prompt = f"""{SAKHI_INSTRUCTIONS}
{body_override}
═══════════════════════════════════════════════════════════════════════════════
THIS PERSON — LIVE DATA
═══════════════════════════════════════════════════════════════════════════════

{person_block}

═══════════════════════════════════════════════════════════════════════════════
THIS CONVERSATION
═══════════════════════════════════════════════════════════════════════════════

{conversation_block}

═══════════════════════════════════════════════════════════════════════════════
THEY SAID: {user_text.strip()}
═══════════════════════════════════════════════════════════════════════════════"""

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


def _build_response_direction(synth: SynthesizedContext, jf: JargonFreeContext) -> str:
    """Brief reasoning for why this response mode was chosen."""
    mode = synth.response_mode
    known_count = len(synth.known_facts)
    questions_count = len(synth.questions_to_ask)

    # Body-specific direction: practical remedies first
    if _is_physical_health_symptom(synth):
        if mode == ResponseMode.RESPOND:
            return (
                f"Physical symptom. Give practical remedies first, "
                f"then connect to their patterns. They're {jf.friction_state_name} — "
                f"use that as context, not primary frame."
            )
        elif mode == ResponseMode.CONNECT_AND_INQUIRE:
            return (
                f"Physical symptom with some context ({known_count} known). "
                f"Give practical advice, ask 1 diagnostic question about the symptom."
            )
        else:
            return "Physical symptom, limited context. Acknowledge, ask diagnostic question about the symptom."

    if mode == ResponseMode.RESPOND:
        return f"We know enough to help. They're {jf.friction_state_name} — guide accordingly."
    elif mode == ResponseMode.CONNECT_AND_INQUIRE:
        return f"We know {known_count} things. Need {questions_count} more piece(s) before full guidance."
    else:  # INQUIRE
        return "New territory — understand more before suggesting anything."


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
    "SAKHI_INSTRUCTIONS",
    "DEFAULT_GUARDRAILS",
    "JARGON_FREE_GUARDRAILS",
]
