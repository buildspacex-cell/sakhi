"""
Relationships API Routes
------------------------
Endpoints for managing relationships with people in the user's life.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from sakhi.apps.api.services.relationships import (
    get_relationship,
    get_all_relationships,
    upsert_relationship,
    update_relationship_contact,
    get_relationships_needing_attention,
    get_relationship_for_scheduling,
    extract_people_from_text,
    process_entry_for_relationships,
)

router = APIRouter(prefix="/relationships", tags=["Relationships"])


# =============================================================================
# Request/Response Models
# =============================================================================

class RelationshipCreate(BaseModel):
    """Request model for creating/updating a relationship."""
    name: str = Field(..., description="Name of the person")
    relationship_type: str = Field(
        default="acquaintance",
        description="Type: close_friend, friend, family, partner, colleague, etc."
    )
    closeness: float = Field(default=0.5, ge=0.0, le=1.0)
    frequency_target: Optional[str] = Field(
        default=None,
        description="How often to connect: daily, weekly, monthly, etc."
    )
    context: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Rich context about the relationship"
    )
    patterns: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Observed patterns"
    )
    scheduling: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Scheduling preferences for this relationship"
    )


class ContactUpdate(BaseModel):
    """Request model for updating contact timestamp."""
    contact_type: str = Field(
        default="contact",
        description="Type of contact: seen (in-person), contact (any), mentioned"
    )


class TextAnalysis(BaseModel):
    """Request model for analyzing text for relationships."""
    text: str = Field(..., description="Text to analyze")


# =============================================================================
# Endpoints
# =============================================================================

@router.get("/{person_id}")
async def list_relationships(
    person_id: str,
    relationship_type: Optional[str] = None,
    min_closeness: float = 0.0,
    limit: int = 50,
) -> Dict[str, Any]:
    """
    List all relationships for a person.

    Optionally filter by relationship type and minimum closeness.
    """
    relationships = await get_all_relationships(
        person_id=person_id,
        relationship_type=relationship_type,
        min_closeness=min_closeness,
        limit=limit,
    )

    return {
        "person_id": person_id,
        "count": len(relationships),
        "relationships": relationships,
    }


@router.get("/{person_id}/{name}")
async def get_relationship_detail(
    person_id: str,
    name: str,
) -> Dict[str, Any]:
    """Get detailed information about a specific relationship."""
    relationship = await get_relationship(person_id, name)

    if not relationship:
        raise HTTPException(status_code=404, detail=f"Relationship with {name} not found")

    return relationship


@router.post("/{person_id}")
async def create_or_update_relationship(
    person_id: str,
    data: RelationshipCreate,
) -> Dict[str, Any]:
    """
    Create or update a relationship.

    If a relationship with this name exists, it will be updated (merged).
    """
    rel_id = await upsert_relationship(
        person_id=person_id,
        name=data.name,
        relationship_type=data.relationship_type,
        closeness=data.closeness,
        frequency_target=data.frequency_target,
        context=data.context,
        patterns=data.patterns,
        scheduling=data.scheduling,
    )

    return {
        "id": rel_id,
        "name": data.name,
        "status": "created_or_updated",
    }


@router.post("/{person_id}/{name}/contact")
async def record_contact(
    person_id: str,
    name: str,
    data: ContactUpdate,
) -> Dict[str, Any]:
    """
    Record a contact with someone.

    Use this to update last_seen_at / last_contact_at timestamps.
    """
    success = await update_relationship_contact(
        person_id=person_id,
        name=name,
        contact_type=data.contact_type,
    )

    if not success:
        raise HTTPException(status_code=404, detail=f"Relationship with {name} not found")

    return {
        "name": name,
        "contact_type": data.contact_type,
        "status": "recorded",
    }


@router.get("/{person_id}/needing-attention")
async def relationships_needing_attention(
    person_id: str,
    limit: int = 5,
) -> Dict[str, Any]:
    """
    Get relationships that may need reconnection.

    Returns close relationships that haven't been contacted recently.
    """
    relationships = await get_relationships_needing_attention(
        person_id=person_id,
        limit=limit,
    )

    return {
        "person_id": person_id,
        "relationships": relationships,
    }


@router.get("/{person_id}/{name}/scheduling")
async def get_scheduling_context(
    person_id: str,
    name: str,
) -> Dict[str, Any]:
    """
    Get relationship data optimized for scheduling.

    Returns information useful for Sakhi-to-Sakhi coordination.
    """
    context = await get_relationship_for_scheduling(person_id, name)

    if not context:
        raise HTTPException(status_code=404, detail=f"Relationship with {name} not found")

    return context


@router.post("/{person_id}/extract")
async def extract_from_text(
    person_id: str,
    data: TextAnalysis,
) -> Dict[str, Any]:
    """
    Extract people mentioned in text.

    Uses LLM to identify people and their relationship context.
    """
    people = await extract_people_from_text(data.text, person_id)

    return {
        "person_id": person_id,
        "people": people,
    }


@router.post("/{person_id}/process-entry")
async def process_entry(
    person_id: str,
    data: TextAnalysis,
) -> Dict[str, Any]:
    """
    Full relationship processing for a journal entry.

    Extracts people, signals, and enriches relationships.
    """
    result = await process_entry_for_relationships(
        person_id=person_id,
        entry_text=data.text,
    )

    return result


__all__ = ["router"]
