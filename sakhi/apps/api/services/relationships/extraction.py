"""
Relationship Extraction Service
-------------------------------
Extract people and relationship signals from text.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from sakhi.apps.api.core.llm import call_llm

logger = logging.getLogger(__name__)


# =============================================================================
# Pydantic Schemas for LLM Responses
# =============================================================================

class PersonMention(BaseModel):
    """A person mentioned in text."""
    name: str = Field(description="The name or identifier of the person (e.g., 'Alex', 'Mom', 'my manager')")
    relationship_type: Optional[str] = Field(
        default=None,
        description="Inferred relationship type: close_friend, friend, family, partner, colleague, mentor, professional, acquaintance"
    )
    context: Optional[str] = Field(
        default=None,
        description="Brief context about this person from the text"
    )
    sentiment: Optional[str] = Field(
        default=None,
        description="Sentiment when mentioning: positive, negative, neutral, mixed"
    )


class PeopleExtractionResult(BaseModel):
    """Result of extracting people from text."""
    people: List[PersonMention] = Field(default_factory=list)


class RelationshipSignal(BaseModel):
    """A signal about a relationship extracted from text."""
    person_name: str = Field(description="The person this signal is about")
    signal_type: str = Field(
        description="Type: interaction, emotion, situation, preference, history"
    )
    content: str = Field(description="The actual signal content")
    confidence: float = Field(default=0.7, ge=0.0, le=1.0)


class RelationshipSignalsResult(BaseModel):
    """Result of extracting relationship signals."""
    signals: List[RelationshipSignal] = Field(default_factory=list)


# =============================================================================
# Extraction Functions
# =============================================================================

PEOPLE_EXTRACTION_PROMPT = """Analyze the following text and extract all people mentioned.

For each person, identify:
1. Their name or identifier (e.g., "Alex", "Mom", "my boss", "Sarah from work")
2. The likely relationship type based on context
3. Any context provided about them in the text
4. The sentiment when they're mentioned

Text to analyze:
---
{text}
---

Return a JSON object with a "people" array. Each person should have:
- name: string (the name/identifier)
- relationship_type: string or null (close_friend, friend, family, partner, colleague, mentor, professional, acquaintance, other)
- context: string or null (brief context from the text)
- sentiment: string or null (positive, negative, neutral, mixed)

If no people are mentioned, return {"people": []}"""


async def extract_people_from_text(
    text: str,
    person_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Extract people mentioned in text using LLM.

    Args:
        text: The text to analyze (journal entry, conversation, etc.)
        person_id: Optional user ID for context

    Returns:
        List of people with their details
    """
    if not text or len(text.strip()) < 10:
        return []

    try:
        result = await call_llm(
            prompt=PEOPLE_EXTRACTION_PROMPT.format(text=text),
            schema=PeopleExtractionResult,
            person_id=person_id,
        )

        if isinstance(result, PeopleExtractionResult):
            return [p.model_dump() for p in result.people]

        return []

    except Exception as e:
        logger.warning(f"Failed to extract people from text: {e}")
        return []


RELATIONSHIP_SIGNALS_PROMPT = """Analyze the following text and extract signals about relationships with the people mentioned.

Look for:
1. Interactions: Did they meet, talk, or do something together?
2. Emotions: How does the author feel about or around this person?
3. Situations: What's happening in this person's life?
4. Preferences: What does the author like/dislike about interactions with them?
5. History: Any backstory or shared history mentioned?

Text to analyze:
---
{text}
---

Return a JSON object with a "signals" array. Each signal should have:
- person_name: string (who this signal is about)
- signal_type: string (interaction, emotion, situation, preference, history)
- content: string (the actual signal/information)
- confidence: float (0.0 to 1.0, how confident you are in this extraction)

Focus on concrete, specific signals that help understand the relationship."""


async def extract_relationship_signals(
    text: str,
    person_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Extract relationship signals from text.

    These signals enrich our understanding of relationships over time.

    Args:
        text: The text to analyze
        person_id: Optional user ID for context

    Returns:
        List of relationship signals
    """
    if not text or len(text.strip()) < 20:
        return []

    try:
        result = await call_llm(
            prompt=RELATIONSHIP_SIGNALS_PROMPT.format(text=text),
            schema=RelationshipSignalsResult,
            person_id=person_id,
        )

        if isinstance(result, RelationshipSignalsResult):
            return [s.model_dump() for s in result.signals]

        return []

    except Exception as e:
        logger.warning(f"Failed to extract relationship signals: {e}")
        return []


# =============================================================================
# Lightweight Pattern-Based Extraction (No LLM)
# =============================================================================

# Common relationship indicators
FAMILY_INDICATORS = {"mom", "dad", "mother", "father", "sister", "brother", "aunt", "uncle", "grandma", "grandpa", "wife", "husband", "son", "daughter"}
PROFESSIONAL_INDICATORS = {"boss", "manager", "colleague", "coworker", "client", "team", "CEO", "director"}

def quick_extract_people_patterns(text: str) -> List[Dict[str, Any]]:
    """
    Quick pattern-based extraction without LLM.

    Use this for real-time extraction during conversation.
    For deeper analysis, use extract_people_from_text().
    """
    import re

    results = []
    text_lower = text.lower()

    # Check for family mentions
    for indicator in FAMILY_INDICATORS:
        if indicator in text_lower:
            # Try to find if there's a name nearby (e.g., "my mom Sarah")
            pattern = rf"my\s+{indicator}\s+([A-Z][a-z]+)"
            match = re.search(pattern, text, re.IGNORECASE)
            name = match.group(1) if match else indicator.capitalize()
            results.append({
                "name": name,
                "relationship_type": "family",
                "detected_by": "pattern",
            })

    # Check for professional mentions
    for indicator in PROFESSIONAL_INDICATORS:
        if indicator in text_lower:
            pattern = rf"my\s+{indicator}\s+([A-Z][a-z]+)"
            match = re.search(pattern, text, re.IGNORECASE)
            name = match.group(1) if match else indicator.capitalize()
            results.append({
                "name": name,
                "relationship_type": "colleague" if indicator in {"colleague", "coworker", "team"} else "professional",
                "detected_by": "pattern",
            })

    # Look for "with [Name]" patterns
    with_pattern = r"with\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)"
    for match in re.finditer(with_pattern, text):
        name = match.group(1)
        # Filter out common non-names
        if name.lower() not in {"the", "a", "an", "my", "this", "that", "some"}:
            if not any(r["name"].lower() == name.lower() for r in results):
                results.append({
                    "name": name,
                    "relationship_type": None,
                    "detected_by": "pattern",
                })

    return results


__all__ = [
    "extract_people_from_text",
    "extract_relationship_signals",
    "quick_extract_people_patterns",
    "PersonMention",
    "RelationshipSignal",
]
