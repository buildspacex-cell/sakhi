"""
Relationship Enrichment Service
-------------------------------
Enrich relationship data from journal entries and conversations.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from sakhi.apps.api.core.llm import call_llm
from sakhi.apps.api.services.relationships.repository import (
    get_relationship,
    upsert_relationship,
    update_relationship_contact,
)
from sakhi.apps.api.services.relationships.extraction import (
    extract_people_from_text,
    extract_relationship_signals,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Pydantic Schemas
# =============================================================================

class RelationshipEnrichment(BaseModel):
    """Enriched relationship data from analysis."""
    current_situation: Optional[str] = Field(
        default=None,
        description="What's currently happening in this person's life"
    )
    important_to_know: Optional[str] = Field(
        default=None,
        description="Important facts to remember about them"
    )
    shared_interests: List[str] = Field(
        default_factory=list,
        description="Interests shared with the user"
    )
    relationship_quality: Optional[str] = Field(
        default=None,
        description="Current quality: strong, good, neutral, strained, distant"
    )
    energy_effect: Optional[str] = Field(
        default=None,
        description="How user feels after interacting: energized, drained, neutral"
    )
    suggested_closeness: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Suggested closeness score based on context"
    )


class RelationshipEnrichmentResult(BaseModel):
    """Result of relationship enrichment."""
    enrichments: Dict[str, RelationshipEnrichment] = Field(
        default_factory=dict,
        description="Map of person name to their enrichment"
    )


# =============================================================================
# Enrichment Functions
# =============================================================================

ENRICHMENT_PROMPT = """Based on this journal entry/conversation, extract relationship insights.

For each person mentioned, identify:
1. Their current situation (what's happening in their life)
2. Important things to remember about them
3. Shared interests with the author
4. The current quality of the relationship
5. How the author feels after interacting with them
6. A suggested closeness score (0.0 = acquaintance, 1.0 = very close)

People to analyze: {people}

Text:
---
{text}
---

Return a JSON object with an "enrichments" dictionary where keys are person names."""


async def enrich_relationship_from_entry(
    person_id: str,
    text: str,
    detected_people: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Dict[str, Any]]:
    """
    Enrich relationships from a journal entry or conversation.

    This is the main entry point called during memory ingestion.

    Args:
        person_id: The user's ID
        text: The entry text
        detected_people: Optional pre-detected people (skips extraction)

    Returns:
        Dict mapping person names to their enriched data
    """
    # Extract people if not provided
    if detected_people is None:
        detected_people = await extract_people_from_text(text, person_id)

    if not detected_people:
        return {}

    people_names = [p["name"] for p in detected_people]

    try:
        # Get enrichment from LLM
        result = await call_llm(
            prompt=ENRICHMENT_PROMPT.format(
                people=", ".join(people_names),
                text=text,
            ),
            schema=RelationshipEnrichmentResult,
            person_id=person_id,
        )

        enrichments = {}
        if isinstance(result, RelationshipEnrichmentResult):
            enrichments = {
                name: e.model_dump()
                for name, e in result.enrichments.items()
            }

        # Process each person
        for person_data in detected_people:
            name = person_data["name"]
            enrichment = enrichments.get(name, {})

            # Build context from enrichment
            context = {}
            if enrichment.get("current_situation"):
                context["current_situation"] = enrichment["current_situation"]
            if enrichment.get("important_to_know"):
                context["important_to_know"] = enrichment["important_to_know"]
            if enrichment.get("shared_interests"):
                context["shared_interests"] = enrichment["shared_interests"]

            # Build patterns
            patterns = {}
            if enrichment.get("energy_effect"):
                patterns["user_energy_after"] = enrichment["energy_effect"]

            # Determine closeness
            closeness = enrichment.get("suggested_closeness", 0.5)
            if person_data.get("relationship_type") in ("close_friend", "family", "partner"):
                closeness = max(closeness, 0.7)

            # Upsert the relationship
            await upsert_relationship(
                person_id=person_id,
                name=name,
                relationship_type=person_data.get("relationship_type") or "acquaintance",
                closeness=closeness,
                context=context if context else None,
                patterns=patterns if patterns else None,
            )

            # Update mention timestamp
            await update_relationship_contact(person_id, name, "mentioned")

        return enrichments

    except Exception as e:
        logger.warning(f"Failed to enrich relationships: {e}")
        # Still try to save basic relationship data
        for person_data in detected_people:
            try:
                await upsert_relationship(
                    person_id=person_id,
                    name=person_data["name"],
                    relationship_type=person_data.get("relationship_type") or "acquaintance",
                )
                await update_relationship_contact(person_id, person_data["name"], "mentioned")
            except Exception as inner_e:
                logger.warning(f"Failed to save relationship {person_data['name']}: {inner_e}")

        return {}


CONTEXT_ENRICHMENT_PROMPT = """You are helping enrich relationship context for scheduling purposes.

Current relationship data:
- Name: {name}
- Type: {relationship_type}
- Current situation: {current_situation}
- Important to know: {important_to_know}

New information from recent entry:
---
{text}
---

Extract any NEW information that would be useful to remember about this person, especially:
1. Updates to their situation
2. New things to remember
3. Scheduling preferences (when they're typically available, what they like to do)
4. Communication preferences

Return a JSON object with:
- current_situation: string or null (updated situation)
- important_to_know: string or null (new important info, append to existing)
- scheduling_hints: object or null (preferred_times, usual_activities, typical_duration, etc.)
- communication_style: string or null (how they prefer to communicate)"""


async def enrich_relationship_context(
    person_id: str,
    name: str,
    text: str,
) -> Dict[str, Any]:
    """
    Enrich a specific relationship with new context from text.

    Used when we detect a specific person is being discussed in detail.

    Args:
        person_id: The user's ID
        name: The person's name
        text: Text containing information about them

    Returns:
        The enriched context
    """
    # Get existing relationship
    existing = await get_relationship(person_id, name)

    current_situation = ""
    important_to_know = ""

    if existing:
        context = existing.get("context", {})
        if isinstance(context, dict):
            current_situation = context.get("current_situation", "")
            important_to_know = context.get("important_to_know", "")

    try:
        result = await call_llm(
            prompt=CONTEXT_ENRICHMENT_PROMPT.format(
                name=name,
                relationship_type=existing.get("relationship_type", "unknown") if existing else "unknown",
                current_situation=current_situation or "Not known",
                important_to_know=important_to_know or "Nothing specific",
                text=text,
            ),
            person_id=person_id,
        )

        # Parse result and update
        if isinstance(result, str):
            from sakhi.apps.api.core.llm import extract_json_from_llm_response
            enrichment = extract_json_from_llm_response(result)
        else:
            enrichment = result

        if isinstance(enrichment, dict):
            # Build updated context
            new_context = {}
            if enrichment.get("current_situation"):
                new_context["current_situation"] = enrichment["current_situation"]
            if enrichment.get("important_to_know"):
                # Append to existing
                if important_to_know:
                    new_context["important_to_know"] = f"{important_to_know}. {enrichment['important_to_know']}"
                else:
                    new_context["important_to_know"] = enrichment["important_to_know"]
            if enrichment.get("communication_style"):
                new_context["communication_style"] = enrichment["communication_style"]

            # Build scheduling
            scheduling = enrichment.get("scheduling_hints", {})

            # Update relationship
            if new_context or scheduling:
                await upsert_relationship(
                    person_id=person_id,
                    name=name,
                    context=new_context if new_context else None,
                    scheduling=scheduling if scheduling else None,
                )

            return enrichment

        return {}

    except Exception as e:
        logger.warning(f"Failed to enrich relationship context for {name}: {e}")
        return {}


async def process_entry_for_relationships(
    person_id: str,
    entry_text: str,
    entry_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Full relationship processing pipeline for a journal entry.

    This is the main hook to call from memory ingestion.

    Args:
        person_id: The user's ID
        entry_text: The journal entry text
        entry_id: Optional entry ID for tracking

    Returns:
        Processing result with detected people and enrichments
    """
    result = {
        "entry_id": entry_id,
        "people_detected": [],
        "signals_extracted": [],
        "relationships_updated": [],
    }

    # 1. Extract people
    people = await extract_people_from_text(entry_text, person_id)
    result["people_detected"] = people

    if not people:
        return result

    # 2. Extract relationship signals
    signals = await extract_relationship_signals(entry_text, person_id)
    result["signals_extracted"] = signals

    # 3. Enrich and save relationships
    enrichments = await enrich_relationship_from_entry(
        person_id=person_id,
        text=entry_text,
        detected_people=people,
    )

    result["relationships_updated"] = list(enrichments.keys())

    return result


__all__ = [
    "enrich_relationship_from_entry",
    "enrich_relationship_context",
    "process_entry_for_relationships",
]
