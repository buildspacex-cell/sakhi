"""
Knowledge Gap Analysis

Queries existing memory to determine:
- KNOWN: Facts we already have about the user
- INFERRED: Deductions from state vectors and patterns
- UNKNOWN: Questions we need to ask

Prevents redundant questioning by checking memory before asking.
"""

from __future__ import annotations

import json
import os
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from sakhi.apps.api.core.db import q
from sakhi.apps.api.services.memory.recall import recall_advanced
from sakhi.apps.api.services.response.sensing import SenseFrame

logger = logging.getLogger(__name__)


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class KnownFact:
    """A fact we already know about the user."""
    topic: str  # What this fact is about (e.g., "sleep", "meals")
    value: str  # The fact itself
    source: str  # Where it came from (e.g., "episodic", "short_term", "onboarding")
    recency: str  # "recent" (< 7 days), "moderate" (7-30 days), "old" (> 30 days)
    confidence: float  # 0-1 confidence in this fact


@dataclass
class Inference:
    """A deduction we can make from available data."""
    topic: str  # What we're inferring about
    statement: str  # The inference
    basis: str  # What it's based on (e.g., "state_vector drift", "guna_vector")
    confidence: float  # 0-1 confidence


@dataclass
class DiagnosticQuestion:
    """A question we need to ask to fill a knowledge gap."""
    id: str  # Unique ID (e.g., "pain_quality")
    question: str  # The question to ask
    priority: str  # "high", "medium", "low"
    dosha_relevance: str  # Which dosha this is most relevant for
    why: str  # Why this question matters


@dataclass
class ConstitutionContext:
    """User's constitutional context for response guidance."""
    operating_system: Optional[str] = None  # e.g., "Adaptive-Performance"
    dosha_baseline: Dict[str, float] = field(default_factory=dict)  # {vata: 0.3, pitta: 0.45, kapha: 0.25}
    dominant_dosha: str = "balanced"  # "vata", "pitta", "kapha", or "balanced"
    current_state: Dict[str, float] = field(default_factory=dict)  # Current dosha levels
    drift: Dict[str, float] = field(default_factory=dict)  # Drift from baseline
    guna_mode: str = "sattva"  # "sattva", "rajas", "tamas"
    life_context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class KnowledgeGap:
    """Result of knowledge gap analysis."""
    known: Dict[str, KnownFact] = field(default_factory=dict)  # topic -> KnownFact
    inferred: Dict[str, Inference] = field(default_factory=dict)  # topic -> Inference
    unknown: List[DiagnosticQuestion] = field(default_factory=list)  # Questions to ask
    constitution: ConstitutionContext = field(default_factory=ConstitutionContext)


class DiagnosticQuestionPayload(BaseModel):
    """Structured LLM payload for one diagnostic question."""
    id: str = Field(default="q_0")
    question: str = Field(default="")
    priority: str = Field(default="medium")
    dosha_relevance: str = Field(default="balanced")
    why: str = Field(default="")


class DiagnosticQuestionEnvelope(BaseModel):
    """Structured LLM payload for the diagnostic questions list."""
    questions: List[DiagnosticQuestionPayload] = Field(default_factory=list)


# =============================================================================
# MEMORY QUERY CONFIGURATION
# =============================================================================

# Keywords to search for common topics
TOPIC_KEYWORDS = {
    "sleep": ["sleep", "insomnia", "tired", "rest", "night", "woke", "wake", "bed", "nap"],
    "meals": ["lunch", "dinner", "meal", "eat", "skip", "food", "breakfast", "hungry"],
    "hydration": ["water", "drink", "hydrate", "thirsty", "dehydrated"],
    "stress": ["stress", "work", "deadline", "pressure", "busy", "overwhelm", "tense"],
    "exercise": ["exercise", "workout", "gym", "run", "walk", "yoga", "move", "active"],
    "screen": ["screen", "computer", "phone", "eyes", "strain", "laptop", "monitor"],
    "anxiety": ["anxious", "anxiety", "worried", "worry", "nervous", "panic"],
    "mood": ["sad", "down", "depressed", "happy", "mood", "feeling"],
    "energy": ["energy", "fatigue", "exhausted", "drained", "tired", "low"],
    "pain": ["pain", "ache", "hurt", "sore", "tension"],
    "skin": ["skin", "dry", "dryness", "rash", "itch", "itchy", "flaky", "rough", "acne"],
    "digestion": ["digestion", "bloating", "constipation", "acidity", "stomach", "gut", "nausea"],
}

# Pronouns and references that indicate need for context resolution
UNRESOLVED_REFERENCE_PATTERNS = [
    # Personal pronouns (third person)
    "she", "her", "hers", "he", "him", "his", "they", "them", "their",
    # Demonstrative pronouns
    "it", "this", "that", "these", "those",
    # Reference phrases
    "the same", "again", "like before", "as usual", "the situation",
    "the issue", "the problem", "the thing", "what we talked about",
]


# =============================================================================
# CONSTITUTION LOADING
# =============================================================================

async def load_constitution_context(person_id: str) -> ConstitutionContext:
    """
    Load the user's constitutional context from personal_model.

    This includes:
    - Operating system type
    - Dosha baseline
    - Life context
    """
    ctx = ConstitutionContext()

    try:
        row = await q(
            """
            SELECT operating_system, life_context, decision_profile
            FROM personal_model
            WHERE person_id = $1
            """,
            person_id,
            one=True,
        )

        if row and row.get("operating_system"):
            os_data = row["operating_system"]
            if isinstance(os_data, str):
                os_data = json.loads(os_data)
            if isinstance(os_data, dict):
                ctx.operating_system = os_data.get("type")
                ctx.dosha_baseline = os_data.get("dosha_baseline") or {}

                # Determine dominant dosha
                if ctx.dosha_baseline:
                    max_dosha = max(ctx.dosha_baseline, key=ctx.dosha_baseline.get)
                    max_value = ctx.dosha_baseline[max_dosha]
                    # Only consider dominant if > 35%
                    if max_value > 0.35:
                        ctx.dominant_dosha = max_dosha
                    else:
                        ctx.dominant_dosha = "balanced"

        if row and row.get("life_context"):
            lc = row["life_context"]
            if isinstance(lc, str):
                lc = json.loads(lc)
            ctx.life_context = lc if isinstance(lc, dict) else {}

    except Exception as e:
        logger.warning("[load_constitution_context] Error: %s", e)

    return ctx


async def load_state_vectors(person_id: str, ctx: ConstitutionContext) -> None:
    """
    Load current state vectors from memory_episodic.

    Updates the context with:
    - Current dosha state
    - Drift from baseline
    - Guna mode
    """
    try:
        # Get most recent episodic entry with state vectors
        rows = await q(
            """
            SELECT state_vector, guna_vector, created_at
            FROM memory_episodic
            WHERE user_id = $1 AND state_vector IS NOT NULL
            ORDER BY created_at DESC
            LIMIT 1
            """,
            person_id,
        )

        if rows and rows[0].get("state_vector"):
            state = rows[0]["state_vector"]
            if isinstance(state, str):
                state = json.loads(state)
            if isinstance(state, dict):
                dosha = state.get("dosha") or {}
                if dosha:
                    ctx.current_state = dosha
                    # Calculate drift from baseline
                    for d in ["vata", "pitta", "kapha"]:
                        baseline = ctx.dosha_baseline.get(d, 0.33)
                        current = dosha.get(d, baseline)
                        ctx.drift[d] = round(current - baseline, 3)

        if rows and rows[0].get("guna_vector"):
            guna = rows[0]["guna_vector"]
            if isinstance(guna, str):
                guna = json.loads(guna)
            if isinstance(guna, dict):
                # Determine dominant guna
                max_guna = max(["sattva", "rajas", "tamas"], key=lambda g: guna.get(g, 0))
                ctx.guna_mode = max_guna

    except Exception as e:
        logger.warning("[load_state_vectors] Error: %s", e)


# =============================================================================
# PRONOUN/REFERENCE DETECTION
# =============================================================================

def detect_unresolved_references(text: str) -> List[str]:
    """
    Detect pronouns and references that may need context resolution.

    Returns list of detected reference patterns that suggest the user
    is referring to something/someone mentioned previously.
    """
    text_lower = text.lower()
    found = []

    for pattern in UNRESOLVED_REFERENCE_PATTERNS:
        # Use word boundary matching to avoid partial matches
        # e.g., "the" in "there" shouldn't match
        import re
        if re.search(rf'\b{re.escape(pattern)}\b', text_lower):
            found.append(pattern)

    return found


def needs_context_resolution(text: str) -> bool:
    """
    Check if the message contains unresolved references that need context.

    This triggers broader semantic search to resolve "her", "it", "that" etc.
    """
    references = detect_unresolved_references(text)
    # Threshold: if we find at least one reference pronoun, we need context
    return len(references) > 0


# =============================================================================
# MEMORY SEARCH
# =============================================================================

async def search_memory_for_topic(
    person_id: str,
    topic: str,
    keywords: List[str],
    *,
    recency_days: int = 14,
) -> Optional[KnownFact]:
    """
    Search memory for information about a specific topic.

    Returns a KnownFact if relevant information is found.
    """
    # Build a search query from keywords
    query = " ".join(keywords[:5])  # Use top 5 keywords

    try:
        # Use recall_advanced to search
        results = await recall_advanced(person_id, query, k=3)

        if not results:
            return None

        # Check if any result is relevant
        for result in results:
            score = result.get("score", 0)
            if score < 0.3:  # Relevance threshold
                continue

            text = result.get("text", "")
            source = result.get("type", "unknown")

            # Check if any keyword appears in the result
            text_lower = text.lower()
            if not any(kw in text_lower for kw in keywords):
                continue

            # Determine recency
            recency = "moderate"  # Default
            # Note: recall_advanced applies recency weighting, higher scores = more recent

            return KnownFact(
                topic=topic,
                value=text[:200],  # Truncate for brevity
                source=source,
                recency=recency,
                confidence=min(1.0, score * 1.5),  # Boost confidence slightly
            )

    except Exception as e:
        logger.warning("[search_memory_for_topic] Error searching for %s: %s", topic, e)

    return None


async def search_short_term_memory(
    person_id: str,
    topic: str,
    keywords: List[str],
) -> Optional[KnownFact]:
    """Search short-term memory for recent mentions."""
    try:
        rows = await q(
            """
            SELECT text, created_at
            FROM memory_short_term
            WHERE user_id = $1
            ORDER BY created_at DESC
            LIMIT 20
            """,
            person_id,
        )

        for row in rows:
            text = (row.get("text") or "").lower()
            if any(kw in text for kw in keywords):
                return KnownFact(
                    topic=topic,
                    value=row.get("text", "")[:200],
                    source="short_term",
                    recency="recent",
                    confidence=0.8,
                )

    except Exception as e:
        logger.warning("[search_short_term_memory] Error: %s", e)

    return None


async def semantic_recall_for_references(
    person_id: str,
    user_text: str,
    life_context: Dict[str, Any],
) -> List[KnownFact]:
    """
    Perform semantic search when unresolved references are detected.

    Uses the full user message + life_context to build a richer query
    that can resolve "her", "it", "that" etc.
    """
    facts = []

    # Build context-aware query
    # Include names from life_context to help resolve pronouns
    query_parts = [user_text]

    people = life_context.get("people") or life_context.get("relationships") or {}
    if isinstance(people, dict):
        # Add names to help semantic search find relevant memories
        for name in people.keys():
            query_parts.append(name)

    # Add any ongoing concerns
    concerns = life_context.get("ongoing_concerns") or []
    if isinstance(concerns, list):
        query_parts.extend(concerns[:3])  # Top 3 concerns

    query = " ".join(query_parts)

    try:
        # Search with enriched query
        results = await recall_advanced(person_id, query, k=5)

        for result in results:
            score = result.get("score", 0)
            if score < 0.25:  # Lower threshold for context resolution
                continue

            text = result.get("text", "")
            source = result.get("type", "episodic")

            facts.append(KnownFact(
                topic="context_reference",
                value=text[:250],
                source=source,
                recency="moderate",
                confidence=min(1.0, score * 1.3),
            ))

    except Exception as e:
        logger.warning("[semantic_recall_for_references] Error: %s", e)

    return facts


# =============================================================================
# INFERENCE ENGINE
# =============================================================================

def generate_inferences(
    constitution: ConstitutionContext,
    sense: SenseFrame,
) -> Dict[str, Inference]:
    """
    Generate inferences from state vectors and patterns.

    Example inferences:
    - "Pitta elevated +7% from baseline" -> likely heat/intensity related
    - "Rajas dominant" -> high activation mode, may be pushing too hard
    """
    inferences = {}

    # Dosha drift inferences
    for dosha, drift_value in constitution.drift.items():
        if abs(drift_value) > 0.05:  # Significant drift
            direction = "elevated" if drift_value > 0 else "reduced"
            percent = int(abs(drift_value) * 100)

            if dosha == "vata" and drift_value > 0:
                inferences["vata_elevation"] = Inference(
                    topic="vata_state",
                    statement=f"Vata {direction} {percent}% from baseline — may indicate irregularity, anxiety, or overstimulation",
                    basis="state_vector drift",
                    confidence=0.7,
                )
            elif dosha == "pitta" and drift_value > 0:
                inferences["pitta_elevation"] = Inference(
                    topic="pitta_state",
                    statement=f"Pitta {direction} {percent}% from baseline — may indicate intensity, heat, or frustration",
                    basis="state_vector drift",
                    confidence=0.7,
                )
            elif dosha == "kapha" and drift_value > 0:
                inferences["kapha_elevation"] = Inference(
                    topic="kapha_state",
                    statement=f"Kapha {direction} {percent}% from baseline — may indicate sluggishness or stagnation",
                    basis="state_vector drift",
                    confidence=0.7,
                )

    # Guna mode inferences
    if constitution.guna_mode == "rajas":
        inferences["rajas_mode"] = Inference(
            topic="operating_mode",
            statement="Operating in rajas mode — high activation, may be pushing or stressed",
            basis="guna_vector",
            confidence=0.6,
        )
    elif constitution.guna_mode == "tamas":
        inferences["tamas_mode"] = Inference(
            topic="operating_mode",
            statement="Operating in tamas mode — low energy, may be depleted or withdrawn",
            basis="guna_vector",
            confidence=0.6,
        )

    return inferences


# =============================================================================
# DETERMINISTIC INTELLIGENCE LOADING
# =============================================================================

async def _load_deterministic_intelligence(
    person_id: str,
    sense: SenseFrame,
) -> Dict[str, Any]:
    """
    Load deterministic intelligence for this person's current symptom.

    Queries (in parallel):
    - personal_patterns: User-specific cause→effect chains (by effect_value, any type)
    - behavior_log: Recent dosha-affecting behaviors (7 days)
    - symptom_log: Past episodes of this symptom
    - SYMPTOM_DOSHA_MAP: Deterministic dosha mapping

    Runs in parallel with constitution + STM fetch, so net latency ≈ 0ms.
    """
    import asyncio as _asyncio
    from sakhi.apps.api.services.ayurveda.causal_reasoning import (
        map_symptom_to_dosha,
        get_recent_behaviors,
    )

    symptom = sense.symptom or sense.sub_domain or ""
    dosha = map_symptom_to_dosha(symptom) if symptom else None

    async def _empty() -> list:
        return []

    try:
        # All 3 DB queries run in parallel (~50ms total)
        patterns, behaviors, past_episodes = await _asyncio.gather(
            _get_personal_patterns_for_symptom(person_id, symptom) if symptom else _empty(),
            get_recent_behaviors(person_id, hours_back=168),  # 7 days
            _get_past_symptom_episodes(person_id, symptom, limit=3) if symptom else _empty(),
        )
    except Exception as e:
        logger.warning("[_load_deterministic_intelligence] Error: %s", e)
        patterns, behaviors, past_episodes = [], [], []

    return {
        "symptom_dosha": dosha,
        "patterns": patterns or [],
        "behaviors": behaviors or [],
        "past_episodes": past_episodes or [],
    }


async def _get_personal_patterns_for_symptom(
    person_id: str,
    symptom: str,
    min_confidence: float = 0.3,
) -> List[Dict[str, Any]]:
    """
    Fetch personal patterns where effect_value matches the symptom.

    Searches across ALL effect_types (mental, emotional, physical, etc.)
    since the sensing domain taxonomy doesn't align 1:1 with pattern effect_types.
    """
    try:
        rows = await q(
            """
            SELECT cause_type, cause_value, effect_type, effect_value,
                   correlation_strength, confidence, observation_count,
                   ayurvedic_explanation, related_dosha
            FROM personal_patterns
            WHERE person_id = $1
              AND effect_value ILIKE $2
              AND confidence >= $3
            ORDER BY correlation_strength DESC, observation_count DESC
            LIMIT 5
            """,
            person_id,
            f"%{symptom}%",
            min_confidence,
        )
        return [dict(r) for r in rows] if rows else []
    except Exception as e:
        logger.warning("[_get_personal_patterns_for_symptom] Error: %s", e)
        return []


async def _get_past_symptom_episodes(
    person_id: str,
    symptom: str,
    limit: int = 3,
) -> List[Dict[str, Any]]:
    """Fetch past episodes of this symptom from symptom_log."""
    try:
        rows = await q(
            """
            SELECT symptom_name, severity, occurred_at, what_helped,
                   what_didnt_help, source_text, likely_dosha
            FROM symptom_log
            WHERE person_id = $1
              AND symptom_name ILIKE $2
            ORDER BY occurred_at DESC
            LIMIT $3
            """,
            person_id,
            f"%{symptom}%",
            limit,
        )
        return [dict(r) for r in rows] if rows else []
    except Exception as e:
        logger.warning("[_get_past_symptom_episodes] Error: %s", e)
        return []


def _integrate_deterministic_intelligence(
    gap: "KnowledgeGap",
    det_intel: Dict[str, Any],
) -> None:
    """
    Convert deterministic intelligence into KnownFacts and Inferences.

    - Personal patterns → Inferences (learned cause→effect correlations)
    - Recent behaviors → KnownFacts (concrete actions in last 48h)
    - Past symptom episodes → KnownFacts (what helped/didn't before)
    - Symptom→dosha mapping → Inference
    """
    # Personal patterns → Inferences
    for i, pattern in enumerate(det_intel.get("patterns", [])[:5]):
        cause = pattern.get("cause_value", "")
        effect = pattern.get("effect_value", "")
        strength = pattern.get("correlation_strength", 0.5)
        count = pattern.get("observation_count", 1)
        explanation = pattern.get("ayurvedic_explanation", "")

        gap.inferred[f"pattern_{i}"] = Inference(
            topic="personal_pattern",
            statement=(
                f"Known pattern: {cause} tends to cause {effect} "
                f"(observed {count}x, strength {strength:.0%})"
                + (f" — {explanation}" if explanation else "")
            ),
            basis="personal_patterns",
            confidence=min(0.9, strength),
        )

    # Recent behaviors → KnownFacts
    for i, behavior in enumerate(det_intel.get("behaviors", [])[:5]):
        name = behavior.get("behavior_name", "")
        dosha_eff = behavior.get("dosha_effect", "")
        direction = behavior.get("effect_direction", "")
        occurred = behavior.get("occurred_at", "")
        time_str = ""
        if occurred:
            try:
                from datetime import datetime
                if hasattr(occurred, "strftime"):
                    time_str = f" — {occurred.strftime('%b %d')}"
            except Exception:
                pass

        gap.known[f"behavior_{i}"] = KnownFact(
            topic="recent_behavior",
            value=f"{name} ({direction}s {dosha_eff}){time_str}",
            source="behavior_log",
            recency="recent",
            confidence=0.9,
        )

    # Past symptom episodes → KnownFacts
    for i, episode in enumerate(det_intel.get("past_episodes", [])[:3]):
        parts = [f"Had {episode.get('symptom_name', '?')} (severity {episode.get('severity', '?')})"]

        helped = episode.get("what_helped")
        if helped:
            if isinstance(helped, str):
                try:
                    helped = json.loads(helped)
                except Exception:
                    helped = []
            if isinstance(helped, list) and helped:
                parts.append(f"What helped: {', '.join(str(h) for h in helped[:3])}")

        didnt = episode.get("what_didnt_help")
        if didnt:
            if isinstance(didnt, str):
                try:
                    didnt = json.loads(didnt)
                except Exception:
                    didnt = []
            if isinstance(didnt, list) and didnt:
                parts.append(f"Didn't help: {', '.join(str(d) for d in didnt[:2])}")

        gap.known[f"past_episode_{i}"] = KnownFact(
            topic="past_episode",
            value=". ".join(parts),
            source="symptom_log",
            recency="moderate",
            confidence=0.85,
        )

    # Symptom-dosha mapping → Inference
    dosha = det_intel.get("symptom_dosha")
    if dosha:
        gap.inferred["symptom_dosha"] = Inference(
            topic="symptom_classification",
            statement=f"This symptom is associated with {dosha} tendency",
            basis="symptom_dosha_map",
            confidence=0.8,
        )


# =============================================================================
# PERSONALIZED QUESTION GENERATION (LLM)
# =============================================================================

async def generate_personalized_questions(
    sense: SenseFrame,
    constitution: ConstitutionContext,
    known: Dict[str, KnownFact],
    inferred: Dict[str, Inference],
) -> List[DiagnosticQuestion]:
    """
    Generate personalized diagnostic questions via LLM.

    Uses the user's full personal context (constitution, known facts,
    inferences from state vectors) to generate questions about what
    we DON'T yet know about their specific situation.
    """
    from sakhi.apps.api.core.llm import call_llm, extract_json_from_llm_response

    os_type = constitution.operating_system or "unknown"
    dosha = constitution.dominant_dosha or "balanced"

    # Separate data by source for structured prompt
    recent_conversation = [f.value for f in known.values() if f.topic == "recent_conversation"]
    recent_behaviors = [f.value for f in known.values() if f.topic == "recent_behavior"]
    past_episodes = [f.value for f in known.values() if f.topic == "past_episode"]
    topic_facts = [
        f"- {f.topic}: {f.value}" for f in known.values()
        if f.topic not in ("recent_conversation", "recent_behavior", "past_episode")
    ]

    # Inferences by source
    pattern_inferences = [inf.statement for inf in inferred.values() if inf.basis == "personal_patterns"]
    dosha_inferences = [inf.statement for inf in inferred.values() if inf.basis == "symptom_dosha_map"]
    state_inferences = [
        inf.statement for inf in inferred.values()
        if inf.basis not in ("personal_patterns", "symptom_dosha_map")
    ]

    # Build structured prompt sections
    known_parts = []
    if recent_conversation:
        known_parts.append("Recent things they've told us:\n" + "\n".join(f'- "{r}"' for r in recent_conversation[:8]))
    if recent_behaviors:
        known_parts.append("Recent behaviors (last 48h):\n" + "\n".join(f"- {b}" for b in recent_behaviors[:5]))
    if past_episodes:
        known_parts.append("Past episodes of this symptom:\n" + "\n".join(f"- {e}" for e in past_episodes[:3]))
    if topic_facts:
        known_parts.append("Known wellness context:\n" + "\n".join(topic_facts[:5]))
    if pattern_inferences:
        known_parts.append("Learned personal patterns:\n" + "\n".join(f"- {p}" for p in pattern_inferences[:5]))
    if dosha_inferences:
        known_parts.append("Symptom classification:\n" + "\n".join(f"- {d}" for d in dosha_inferences))
    known_summary = "\n\n".join(known_parts) if known_parts else "We don't have any context about this person yet."

    # State-based inferences (drift, guna mode)
    inference_summary = ""
    if state_inferences:
        inference_summary = "\nCurrent state:\n" + "\n".join(f"- {s}" for s in state_inferences[:3])

    symptom = sense.symptom or sense.sub_domain or "general concern"
    temporal = sense.temporal or "unspecified"

    prompt = (
        f"You are helping understand someone's wellness concern.\n\n"
        f"ABOUT THIS PERSON:\n"
        f"- System type: {os_type}\n"
        f"- Dominant tendency: {dosha}\n"
        f"{known_summary}\n"
        f"{inference_summary}\n\n"
        f"THEIR MESSAGE: \"{sense.raw_text}\"\n"
        f"Concern: {symptom} (domain: {sense.domain}, timing: {temporal})\n\n"
        f"Generate 2-3 questions to understand their situation better.\n"
        f"IMPORTANT: Do NOT ask about things we already know (listed above).\n"
        f"Focus on genuine gaps in our understanding.\n\n"
        f"Rules:\n"
        f"- Conversational, like a caring friend (not clinical)\n"
        f"- No Ayurvedic, Sanskrit, or medical terms\n"
        f"- Each question: 1 sentence\n"
        f"- Questions should help determine what's causing or worsening this\n\n"
        f'Return a JSON object in this exact shape: {{"questions": [{{"id": "short_id", '
        f'"question": "the question", "priority": "high|medium", '
        f'"dosha_relevance": "{dosha}", "why": "why this matters for this person"}}]}}'
    )

    try:
        raw = await call_llm(
            prompt,
            model=os.getenv("MODEL_CHAT", "gpt-4o-mini"),
            schema=DiagnosticQuestionEnvelope,
            max_repair_attempts=2,
        )

        if isinstance(raw, DiagnosticQuestionEnvelope):
            items = raw.questions
        elif isinstance(raw, list):
            items = raw
        elif isinstance(raw, dict):
            items = raw.get("questions", [])
        elif isinstance(raw, str):
            parsed = extract_json_from_llm_response(raw)
            if isinstance(parsed, list):
                items = parsed
            elif isinstance(parsed, dict):
                items = parsed.get("questions", [])
            else:
                items = []
        else:
            items = []

        questions = []
        for item in items[:3]:
            if isinstance(item, DiagnosticQuestionPayload):
                payload = item
            elif isinstance(item, dict):
                payload = DiagnosticQuestionPayload.model_validate(item)
            else:
                continue

            questions.append(DiagnosticQuestion(
                id=payload.id or f"q_{len(questions)}",
                question=payload.question,
                priority=payload.priority or "medium",
                dosha_relevance=payload.dosha_relevance or dosha,
                why=payload.why,
            ))
        return questions
    except Exception as e:
        logger.warning("[generate_personalized_questions] LLM error: %s", e)
        return []


# =============================================================================
# MAIN ANALYSIS FUNCTION
# =============================================================================

async def analyze_knowledge_gap(
    person_id: str,
    sense: SenseFrame,
) -> KnowledgeGap:
    """
    Main function to analyze knowledge gaps.

    Loads personal context first (constitution, memory, state vectors),
    then generates personalized diagnostic questions via LLM about
    what we don't yet know.

    Args:
        person_id: User ID
        sense: SenseFrame from sensing layer

    Returns:
        KnowledgeGap with known facts, inferences, and personalized questions
    """
    gap = KnowledgeGap()
    import asyncio as _asyncio

    # 1. Load constitution + STM + deterministic intelligence in parallel
    #    (all fast DB queries, no embedding calls)
    gap.constitution, recent_stm, det_intel = await _asyncio.gather(
        _load_constitution_with_vectors(person_id),
        _fetch_recent_stm(person_id),
        _load_deterministic_intelligence(person_id, sense),
    )

    # 2. Recent STM → known facts (no keyword filtering — LLM decides relevance)
    for i, entry in enumerate(recent_stm):
        gap.known[f"recent_{i}"] = KnownFact(
            topic="recent_conversation",
            value=entry,
            source="short_term",
            recency="recent",
            confidence=0.8,
        )

    # 3. Deterministic intelligence → known facts + inferences
    #    Personal patterns, recent behaviors, past episodes, symptom-dosha mapping
    _integrate_deterministic_intelligence(gap, det_intel)

    # 4. Supplementary: keyword-based topic search for episodic memory
    #    (vector search — slower, but finds older relevant memories)
    topics_to_search = _get_relevant_topics(sense)
    episodic_tasks = {
        topic: search_memory_for_topic(person_id, topic, keywords)
        for topic, keywords in topics_to_search.items()
    }
    if episodic_tasks:
        episodic_results = await _asyncio.gather(
            *episodic_tasks.values(), return_exceptions=True,
        )
        for topic, result in zip(episodic_tasks.keys(), episodic_results):
            if isinstance(result, Exception):
                logger.warning("[analyze_knowledge_gap] Episodic search failed for %s: %s", topic, result)
            elif result:
                gap.known[topic] = result

    # 5. Check for unresolved references (pronouns like "her", "it", "that")
    if needs_context_resolution(sense.raw_text):
        context_facts = await semantic_recall_for_references(
            person_id,
            sense.raw_text,
            gap.constitution.life_context,
        )
        for i, fact in enumerate(context_facts):
            gap.known[f"context_ref_{i}"] = fact

    # 6. Generate inferences from state vectors (adds to pattern-based inferences)
    gap.inferred.update(generate_inferences(gap.constitution, sense))

    # 7. Generate personalized questions using full context
    #    LLM sees known facts + inferences + deterministic intelligence → asks about genuine gaps
    gap.unknown = await generate_personalized_questions(
        sense, gap.constitution, gap.known, gap.inferred,
    )

    return gap


async def _load_constitution_with_vectors(person_id: str) -> ConstitutionContext:
    """Load constitution + state vectors in sequence (vectors need baseline)."""
    ctx = await load_constitution_context(person_id)
    await load_state_vectors(person_id, ctx)
    return ctx


async def _fetch_recent_stm(person_id: str, limit: int = 10) -> List[str]:
    """
    Fetch the N most recent short-term memory entries — no keyword filtering.

    The LLM decides what's relevant. This avoids the keyword whack-a-mole
    problem where "hydrate" doesn't match "hydrating", or pain topics
    aren't searched for headache scenarios.
    """
    try:
        rows = await q(
            """
            SELECT text
            FROM memory_short_term
            WHERE user_id = $1
            ORDER BY created_at DESC
            LIMIT $2
            """,
            person_id,
            limit,
        )
        # Deduplicate and filter empty
        seen = set()
        entries = []
        for row in rows:
            text = (row.get("text") or "").strip()
            if text and text not in seen:
                seen.add(text)
                entries.append(text)
        return entries
    except Exception as e:
        logger.warning("[_fetch_recent_stm] Error: %s", e)
        return []


def _get_relevant_topics(sense: SenseFrame) -> Dict[str, List[str]]:
    """
    Determine which topics are relevant to search based on the SenseFrame.

    Returns a dict of topic -> keywords to search.
    """
    relevant = {}

    # Always search for sleep (universal relevance)
    relevant["sleep"] = TOPIC_KEYWORDS["sleep"]

    # Domain-specific topics
    if sense.domain == "body":
        relevant["meals"] = TOPIC_KEYWORDS["meals"]
        relevant["hydration"] = TOPIC_KEYWORDS["hydration"]
        relevant["exercise"] = TOPIC_KEYWORDS["exercise"]

        if sense.sub_domain == "head_neurological":
            relevant["screen"] = TOPIC_KEYWORDS["screen"]
            relevant["stress"] = TOPIC_KEYWORDS["stress"]

        if sense.sub_domain == "energy":
            relevant["stress"] = TOPIC_KEYWORDS["stress"]

        if sense.sub_domain == "skin":
            relevant["skin"] = TOPIC_KEYWORDS["skin"]

        if sense.sub_domain in ("digestion", "digestive"):
            relevant["digestion"] = TOPIC_KEYWORDS["digestion"]

    elif sense.domain == "mind":
        relevant["stress"] = TOPIC_KEYWORDS["stress"]
        relevant["anxiety"] = TOPIC_KEYWORDS["anxiety"]
        relevant["mood"] = TOPIC_KEYWORDS["mood"]
        relevant["energy"] = TOPIC_KEYWORDS["energy"]

    elif sense.domain == "life":
        relevant["stress"] = TOPIC_KEYWORDS["stress"]
        relevant["energy"] = TOPIC_KEYWORDS["energy"]
        # Add mood for relationship/work topics
        relevant["mood"] = TOPIC_KEYWORDS["mood"]

    elif sense.domain == "general":
        # For general conversation, search for core wellness indicators
        # This gives constitution context for any conversation
        relevant["stress"] = TOPIC_KEYWORDS["stress"]
        relevant["energy"] = TOPIC_KEYWORDS["energy"]
        relevant["mood"] = TOPIC_KEYWORDS["mood"]

    else:
        # Unknown domain - still search for basic wellness context
        relevant["stress"] = TOPIC_KEYWORDS["stress"]
        relevant["energy"] = TOPIC_KEYWORDS["energy"]

    return relevant


__all__ = [
    "KnownFact",
    "Inference",
    "DiagnosticQuestion",
    "ConstitutionContext",
    "KnowledgeGap",
    "analyze_knowledge_gap",
    "generate_personalized_questions",
    "load_constitution_context",
    "load_state_vectors",
    "detect_unresolved_references",
    "needs_context_resolution",
    "semantic_recall_for_references",
    "_load_deterministic_intelligence",
    "_integrate_deterministic_intelligence",
    "_get_past_symptom_episodes",
]
