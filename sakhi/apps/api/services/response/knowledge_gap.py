"""
Knowledge Gap Analysis

Queries existing memory to determine:
- KNOWN: Facts we already have about the user
- INFERRED: Deductions from state vectors and patterns
- UNKNOWN: Questions we need to ask

Prevents redundant questioning by checking memory before asking.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

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
            ctx.life_context = row["life_context"] if isinstance(row["life_context"], dict) else {}

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
            WHERE person_id = $1 AND state_vector IS NOT NULL
            ORDER BY created_at DESC
            LIMIT 1
            """,
            person_id,
        )

        if rows and rows[0].get("state_vector"):
            state = rows[0]["state_vector"]
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
            WHERE person_id = $1
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
# MAIN ANALYSIS FUNCTION
# =============================================================================

async def analyze_knowledge_gap(
    person_id: str,
    sense: SenseFrame,
    diagnostic_questions: List[DiagnosticQuestion],
) -> KnowledgeGap:
    """
    Main function to analyze knowledge gaps.

    Args:
        person_id: User ID
        sense: SenseFrame from sensing layer
        diagnostic_questions: Questions from diagnostic KB for this symptom

    Returns:
        KnowledgeGap with known facts, inferences, and remaining questions
    """
    gap = KnowledgeGap()

    # 1. Load constitution context
    gap.constitution = await load_constitution_context(person_id)
    await load_state_vectors(person_id, gap.constitution)

    # 2. Search memory for common topics related to the symptom
    topics_to_search = _get_relevant_topics(sense)

    for topic, keywords in topics_to_search.items():
        # Try short-term first (most recent)
        fact = await search_short_term_memory(person_id, topic, keywords)

        # Fall back to episodic memory
        if not fact:
            fact = await search_memory_for_topic(person_id, topic, keywords)

        if fact:
            gap.known[topic] = fact

    # 3. Check for unresolved references (pronouns like "her", "it", "that")
    #    If found, do a semantic search to help resolve them
    if needs_context_resolution(sense.raw_text):
        context_facts = await semantic_recall_for_references(
            person_id,
            sense.raw_text,
            gap.constitution.life_context,
        )
        # Add context facts with unique keys
        for i, fact in enumerate(context_facts):
            gap.known[f"context_ref_{i}"] = fact

    # 4. Generate inferences from state vectors
    gap.inferred = generate_inferences(gap.constitution, sense)

    # 5. Determine which diagnostic questions are still unknown
    gap.unknown = _filter_unknown_questions(diagnostic_questions, gap.known, gap.inferred)

    return gap


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


def _filter_unknown_questions(
    all_questions: List[DiagnosticQuestion],
    known: Dict[str, KnownFact],
    inferred: Dict[str, Inference],
) -> List[DiagnosticQuestion]:
    """
    Filter diagnostic questions to only those we don't have answers for.

    A question is considered "known" if:
    - We have a KnownFact for its topic
    - We have an Inference that addresses it
    """
    unknown = []

    for q in all_questions:
        q_id = q.id
        topic = q_id.split("_")[0] if "_" in q_id else q_id

        # Check if we have knowledge about this topic
        if topic in known and known[topic].confidence > 0.5:
            continue

        # Check if we have a relevant inference
        if any(topic in inf_topic for inf_topic in inferred.keys()):
            # Reduce priority but still include
            q.priority = "low"

        unknown.append(q)

    # Sort by priority
    priority_order = {"high": 0, "medium": 1, "low": 2}
    unknown.sort(key=lambda x: priority_order.get(x.priority, 2))

    return unknown


__all__ = [
    "KnownFact",
    "Inference",
    "DiagnosticQuestion",
    "ConstitutionContext",
    "KnowledgeGap",
    "analyze_knowledge_gap",
    "load_constitution_context",
    "load_state_vectors",
    "detect_unresolved_references",
    "needs_context_resolution",
    "semantic_recall_for_references",
]
