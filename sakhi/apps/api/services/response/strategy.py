"""
Response Strategy Selection

Determines the response mode based on knowledge gap analysis:
- RESPOND: Enough information to provide guidance
- CONNECT_AND_INQUIRE: Reference what we know, ask targeted questions
- INQUIRE: Need more info before responding

Also selects which questions to ask (max 2 per turn).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from sakhi.apps.api.services.response.knowledge_gap import (
    DiagnosticQuestion,
    KnowledgeGap,
    KnownFact,
)
from sakhi.apps.api.services.response.sensing import SenseFrame


# =============================================================================
# RESPONSE MODES
# =============================================================================

class ResponseMode:
    """Response mode constants."""
    RESPOND = "RESPOND"  # Enough info to provide guidance
    CONNECT_AND_INQUIRE = "CONNECT_AND_INQUIRE"  # Reference known, ask targeted
    INQUIRE = "INQUIRE"  # Need more info first


# =============================================================================
# RESPONSE STRATEGY
# =============================================================================

@dataclass
class ResponseStrategy:
    """Result of strategy selection."""

    mode: str = ResponseMode.INQUIRE  # Default to INQUIRE (safest)
    questions_to_ask: List[DiagnosticQuestion] = field(default_factory=list)  # Max 2
    known_to_reference: List[KnownFact] = field(default_factory=list)  # Facts to mention
    inferences_to_include: List[str] = field(default_factory=list)  # Inferences to mention
    reasoning: str = ""  # Why this mode was selected


# =============================================================================
# STRATEGY SELECTION
# =============================================================================

def select_response_strategy(
    sense: SenseFrame,
    gap: KnowledgeGap,
    *,
    max_questions: int = 2,
) -> ResponseStrategy:
    """
    Select the appropriate response strategy based on knowledge gap.

    Decision logic:
    1. High specificity in message + no critical unknowns → RESPOND
    2. We have known facts → CONNECT_AND_INQUIRE
    3. Little/no known facts → INQUIRE

    Args:
        sense: SenseFrame from sensing layer
        gap: KnowledgeGap from knowledge gap analysis
        max_questions: Maximum questions to include (default 2)

    Returns:
        ResponseStrategy with mode, questions, and facts to reference
    """
    strategy = ResponseStrategy()

    # Count high-priority unknowns
    critical_unknowns = [q for q in gap.unknown if q.priority == "high"]
    all_unknowns = gap.unknown

    # Count what we know
    known_count = len(gap.known)
    inference_count = len(gap.inferred)

    # Decision tree

    # Case 1: User provided high specificity and we have enough context
    if sense.specificity == "high" and len(critical_unknowns) == 0:
        strategy.mode = ResponseMode.RESPOND
        strategy.reasoning = "User provided detailed information, no critical gaps"

    # Case 1b: Medium specificity but strong existing knowledge — help directly
    # This only fires for established users (known_count >= 2 or inference_count >= 2).
    # New users with no personal_model/dosha_baseline have 0 known + 0 inferred,
    # so they still fall through to CONNECT_AND_INQUIRE/INQUIRE for assessment.
    elif (
        sense.specificity == "medium"
        and len(critical_unknowns) == 0
        and (known_count >= 2 or inference_count >= 2)
    ):
        strategy.mode = ResponseMode.RESPOND
        strategy.reasoning = "Medium detail + strong existing knowledge — enough context to help directly"

    # Case 2: We have known facts, can connect and inquire
    elif known_count > 0 or inference_count > 0:
        strategy.mode = ResponseMode.CONNECT_AND_INQUIRE
        strategy.reasoning = f"Have {known_count} known facts and {inference_count} inferences"

    # Case 3: Little knowledge, need to inquire first
    else:
        strategy.mode = ResponseMode.INQUIRE
        strategy.reasoning = "Limited knowledge about user's context"

    # Select questions to ask (if not RESPOND mode)
    if strategy.mode != ResponseMode.RESPOND:
        strategy.questions_to_ask = _select_questions(
            gap.unknown,
            gap.constitution.dominant_dosha,
            max_questions,
        )

    # Select known facts to reference
    strategy.known_to_reference = _select_relevant_facts(gap.known, sense)

    # Select inferences to mention
    strategy.inferences_to_include = _select_relevant_inferences(gap.inferred)

    return strategy


def _select_questions(
    unknowns: List[DiagnosticQuestion],
    dominant_dosha: str,
    max_count: int,
) -> List[DiagnosticQuestion]:
    """
    Select the best questions to ask.

    Prioritization:
    1. High-priority questions for dominant dosha
    2. High-priority questions for any dosha
    3. Medium-priority questions

    Args:
        unknowns: List of unknown questions
        dominant_dosha: User's dominant dosha
        max_count: Maximum questions to return

    Returns:
        List of selected questions (max max_count)
    """
    if not unknowns:
        return []

    selected = []

    # First pass: high-priority for dominant dosha
    for q in unknowns:
        if q.priority == "high" and q.dosha_relevance == dominant_dosha:
            selected.append(q)
            if len(selected) >= max_count:
                return selected

    # Second pass: high-priority for any dosha
    for q in unknowns:
        if q.priority == "high" and q not in selected:
            selected.append(q)
            if len(selected) >= max_count:
                return selected

    # Third pass: medium-priority
    for q in unknowns:
        if q.priority == "medium" and q not in selected:
            selected.append(q)
            if len(selected) >= max_count:
                return selected

    # Fourth pass: any remaining
    for q in unknowns:
        if q not in selected:
            selected.append(q)
            if len(selected) >= max_count:
                return selected

    return selected[:max_count]


def _select_relevant_facts(
    known: dict,
    sense: SenseFrame,
) -> List[KnownFact]:
    """
    Select the most relevant known facts to reference.

    Prioritizes:
    1. Recent facts (high confidence)
    2. Facts related to the symptom domain
    3. Maximum 3 facts to avoid overwhelming

    Args:
        known: Dict of topic -> KnownFact
        sense: SenseFrame for relevance matching

    Returns:
        List of relevant KnownFacts
    """
    if not known:
        return []

    # Convert to list and sort by relevance
    facts = list(known.values())

    # Score each fact
    def score_fact(fact: KnownFact) -> float:
        score = fact.confidence

        # Boost recent facts
        if fact.recency == "recent":
            score += 0.3
        elif fact.recency == "moderate":
            score += 0.1

        # Boost domain-relevant facts
        domain_topics = {
            "body": ["sleep", "meals", "hydration", "exercise", "pain"],
            "mind": ["stress", "anxiety", "mood", "energy"],
            "life": ["stress", "energy"],
        }
        relevant_topics = domain_topics.get(sense.domain, [])
        if fact.topic in relevant_topics:
            score += 0.2

        return score

    # Sort by score
    facts.sort(key=score_fact, reverse=True)

    # Return top 3
    return facts[:3]


def _select_relevant_inferences(inferred: dict) -> List[str]:
    """
    Select relevant inferences to include in response.

    Args:
        inferred: Dict of topic -> Inference

    Returns:
        List of inference statements to include
    """
    if not inferred:
        return []

    # Only include high-confidence inferences
    statements = []
    for inf in inferred.values():
        if inf.confidence >= 0.6:
            statements.append(inf.statement)

    return statements[:2]  # Max 2 inferences


# =============================================================================
# STRATEGY ADJUSTMENTS
# =============================================================================

def adjust_strategy_for_tone(
    strategy: ResponseStrategy,
    sense: SenseFrame,
) -> ResponseStrategy:
    """
    Adjust strategy based on user's tone.

    - Venting tone → fewer questions, more validation
    - Seeking help tone → normal questions
    - Exploring tone → fewer questions, more reflective

    Args:
        strategy: Current strategy
        sense: SenseFrame with tone info

    Returns:
        Adjusted strategy
    """
    if sense.tone == "venting":
        # Reduce questions, they need to be heard first
        strategy.questions_to_ask = strategy.questions_to_ask[:1]
        strategy.reasoning += " (reduced questions for venting tone)"

    elif sense.tone == "exploring":
        # Reduce questions, allow space for exploration
        strategy.questions_to_ask = strategy.questions_to_ask[:1]
        strategy.reasoning += " (reduced questions for exploratory tone)"

    return strategy


def adjust_strategy_for_urgency(
    strategy: ResponseStrategy,
    sense: SenseFrame,
) -> ResponseStrategy:
    """
    Adjust strategy based on urgency level.

    - High urgency → respond mode if possible, acknowledge urgency
    - Low urgency → normal inquiry flow

    Args:
        strategy: Current strategy
        sense: SenseFrame with urgency info

    Returns:
        Adjusted strategy
    """
    if sense.urgency == "high":
        # Try to respond even with less info
        if strategy.mode == ResponseMode.INQUIRE:
            strategy.mode = ResponseMode.CONNECT_AND_INQUIRE
            strategy.reasoning += " (escalated for high urgency)"
        elif strategy.mode == ResponseMode.CONNECT_AND_INQUIRE and (
            len(strategy.known_to_reference) >= 1 or len(strategy.inferences_to_include) >= 1
        ):
            strategy.mode = ResponseMode.RESPOND
            strategy.reasoning += " (escalated for high urgency — enough context to help now)"

    return strategy


__all__ = [
    "ResponseMode",
    "ResponseStrategy",
    "select_response_strategy",
    "adjust_strategy_for_tone",
    "adjust_strategy_for_urgency",
]
