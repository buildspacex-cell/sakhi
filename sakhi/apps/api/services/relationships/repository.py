"""
Relationships Repository
------------------------
Database operations for relationship management.
"""

from __future__ import annotations

import json
import uuid
from typing import Any, Dict, List, Optional
from datetime import datetime

from sakhi.apps.api.core.db import q, exec, dbfetchrow, dbfetchall


async def get_relationship(
    person_id: str,
    name: str,
) -> Optional[Dict[str, Any]]:
    """Get a specific relationship by name."""
    return await dbfetchrow(
        """
        SELECT
            r.*,
            EXTRACT(DAY FROM (now() - COALESCE(r.last_contact_at, r.created_at)))::INTEGER as days_since_contact
        FROM relationships r
        WHERE r.person_id = $1 AND r.name = $2
        """,
        person_id,
        name,
    )


async def get_all_relationships(
    person_id: str,
    relationship_type: Optional[str] = None,
    min_closeness: float = 0.0,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    """Get all relationships for a person, optionally filtered."""
    if relationship_type:
        return await dbfetchall(
            """
            SELECT
                r.*,
                EXTRACT(DAY FROM (now() - COALESCE(r.last_contact_at, r.created_at)))::INTEGER as days_since_contact
            FROM relationships r
            WHERE r.person_id = $1
              AND r.relationship_type = $2
              AND r.closeness >= $3
            ORDER BY r.closeness DESC, r.last_contact_at DESC NULLS LAST
            LIMIT $4
            """,
            person_id,
            relationship_type,
            min_closeness,
            limit,
        )
    else:
        return await dbfetchall(
            """
            SELECT
                r.*,
                EXTRACT(DAY FROM (now() - COALESCE(r.last_contact_at, r.created_at)))::INTEGER as days_since_contact
            FROM relationships r
            WHERE r.person_id = $1
              AND r.closeness >= $2
            ORDER BY r.closeness DESC, r.last_contact_at DESC NULLS LAST
            LIMIT $3
            """,
            person_id,
            min_closeness,
            limit,
        )


async def upsert_relationship(
    person_id: str,
    name: str,
    relationship_type: str = "acquaintance",
    closeness: float = 0.5,
    context: Optional[Dict[str, Any]] = None,
    patterns: Optional[Dict[str, Any]] = None,
    scheduling: Optional[Dict[str, Any]] = None,
    frequency_target: Optional[str] = None,
) -> str:
    """
    Create or update a relationship.

    Args:
        person_id: The user's ID
        name: Name of the person (e.g., "Alex", "Mom")
        relationship_type: Type of relationship
        closeness: How close (0.0 to 1.0)
        context: Rich context about the relationship
        patterns: Observed patterns
        scheduling: Scheduling preferences for this relationship
        frequency_target: How often they want to connect

    Returns:
        The relationship ID
    """
    context_json = json.dumps(context or {})
    patterns_json = json.dumps(patterns or {})
    scheduling_json = json.dumps(scheduling or {})

    # First ensure memory_node exists
    node_row = await dbfetchrow(
        """
        SELECT id FROM memory_nodes
        WHERE person_id = $1 AND node_kind = 'person' AND label = $2
        """,
        person_id,
        name,
    )

    if node_row:
        memory_node_id = node_row["id"]
    else:
        memory_node_id = str(uuid.uuid4())
        await exec(
            """
            INSERT INTO memory_nodes (id, person_id, node_kind, label, data, weight)
            VALUES ($1, $2, 'person', $3, '{}'::jsonb, $4)
            """,
            memory_node_id,
            person_id,
            name,
            closeness,
        )

    # Now upsert relationship
    row = await dbfetchrow(
        """
        INSERT INTO relationships (
            person_id, memory_node_id, name, relationship_type,
            closeness, context, patterns, scheduling, frequency_target
        )
        VALUES ($1, $2, $3, $4, $5, $6::jsonb, $7::jsonb, $8::jsonb, $9)
        ON CONFLICT (person_id, name) DO UPDATE SET
            relationship_type = COALESCE(EXCLUDED.relationship_type, relationships.relationship_type),
            closeness = GREATEST(EXCLUDED.closeness, relationships.closeness),
            context = relationships.context || EXCLUDED.context,
            patterns = relationships.patterns || EXCLUDED.patterns,
            scheduling = CASE
                WHEN EXCLUDED.scheduling != '{}'::jsonb
                THEN relationships.scheduling || EXCLUDED.scheduling
                ELSE relationships.scheduling
            END,
            frequency_target = COALESCE(EXCLUDED.frequency_target, relationships.frequency_target),
            updated_at = now()
        RETURNING id
        """,
        person_id,
        memory_node_id,
        name,
        relationship_type,
        closeness,
        context_json,
        patterns_json,
        scheduling_json,
        frequency_target,
    )

    return row["id"] if row else None


async def update_relationship_contact(
    person_id: str,
    name: str,
    contact_type: str = "contact",  # "seen", "contact", "mentioned"
) -> bool:
    """
    Update the last contact timestamp for a relationship.

    Args:
        person_id: The user's ID
        name: Name of the person
        contact_type: Type of contact
            - "seen": In-person meeting
            - "contact": Any contact (call, text, etc.)
            - "mentioned": Mentioned in journal

    Returns:
        True if updated, False if relationship not found
    """
    result = await exec(
        """
        UPDATE relationships
        SET
            last_contact_at = CASE
                WHEN $3 IN ('seen', 'contact') THEN now()
                ELSE last_contact_at
            END,
            last_seen_at = CASE
                WHEN $3 = 'seen' THEN now()
                ELSE last_seen_at
            END,
            last_mentioned_at = CASE
                WHEN $3 = 'mentioned' THEN now()
                ELSE last_mentioned_at
            END,
            updated_at = now()
        WHERE person_id = $1 AND name = $2
        """,
        person_id,
        name,
        contact_type,
    )

    return "UPDATE 1" in result


async def get_relationships_needing_attention(
    person_id: str,
    limit: int = 5,
) -> List[Dict[str, Any]]:
    """
    Get relationships that may need reconnection.

    Prioritizes by closeness * days since contact.
    """
    return await dbfetchall(
        """
        SELECT
            r.id,
            r.name,
            r.relationship_type,
            r.closeness,
            r.last_contact_at,
            r.last_seen_at,
            EXTRACT(DAY FROM (now() - COALESCE(r.last_contact_at, r.created_at)))::INTEGER as days_since_contact,
            r.frequency_target,
            r.context
        FROM relationships r
        WHERE r.person_id = $1
          AND r.closeness >= 0.5
        ORDER BY
            r.closeness * EXTRACT(DAY FROM (now() - COALESCE(r.last_contact_at, r.created_at))) DESC
        LIMIT $2
        """,
        person_id,
        limit,
    )


async def get_relationship_for_scheduling(
    person_id: str,
    name: str,
) -> Optional[Dict[str, Any]]:
    """
    Get relationship data optimized for scheduling context.

    Returns relevant fields for Sakhi-to-Sakhi scheduling.
    """
    row = await dbfetchrow(
        """
        SELECT
            r.name,
            r.relationship_type,
            r.closeness,
            r.last_seen_at,
            r.last_contact_at,
            EXTRACT(DAY FROM (now() - COALESCE(r.last_contact_at, r.created_at)))::INTEGER as days_since_contact,
            r.context->>'current_situation' as current_situation,
            r.context->>'important_to_know' as important_to_know,
            r.patterns->>'user_energy_after' as energy_effect,
            r.patterns->'usual_activities' as usual_activities,
            r.patterns->'preferred_times' as preferred_times,
            r.patterns->>'typical_duration' as typical_duration,
            r.scheduling,
            r.their_sakhi_id
        FROM relationships r
        WHERE r.person_id = $1 AND r.name = $2
        """,
        person_id,
        name,
    )

    return row


async def get_close_relationships(
    person_id: str,
    min_closeness: float = 0.7,
    limit: int = 10,
) -> List[Dict[str, Any]]:
    """Get the closest relationships for a person."""
    return await dbfetchall(
        """
        SELECT
            r.name,
            r.relationship_type,
            r.closeness,
            r.context->>'current_situation' as current_situation,
            r.their_sakhi_id IS NOT NULL as has_sakhi
        FROM relationships r
        WHERE r.person_id = $1 AND r.closeness >= $2
        ORDER BY r.closeness DESC
        LIMIT $3
        """,
        person_id,
        min_closeness,
        limit,
    )


async def link_sakhi(
    person_id: str,
    name: str,
    their_sakhi_id: str,
) -> bool:
    """Link a relationship to their Sakhi ID for mesh coordination."""
    result = await exec(
        """
        UPDATE relationships
        SET their_sakhi_id = $3, updated_at = now()
        WHERE person_id = $1 AND name = $2
        """,
        person_id,
        name,
        their_sakhi_id,
    )

    return "UPDATE 1" in result


__all__ = [
    "get_relationship",
    "get_all_relationships",
    "upsert_relationship",
    "update_relationship_contact",
    "get_relationships_needing_attention",
    "get_relationship_for_scheduling",
    "get_close_relationships",
    "link_sakhi",
]
