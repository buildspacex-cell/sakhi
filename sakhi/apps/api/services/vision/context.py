"""
Visual Context Service
----------------------
Manage visual context within conversations.

Tracks what images/documents have been shared in a conversation
so Sakhi can reference them naturally.
"""

from __future__ import annotations

import logging
import json
from typing import Any, Dict, List, Optional

from pydantic import BaseModel

from sakhi.apps.api.core.db import q as dbfetch, exec as dbexec

LOGGER = logging.getLogger(__name__)


class VisualContextItem(BaseModel):
    """A single item in visual context."""
    media_id: str
    description: str
    relevance: float = 1.0
    turn_index: Optional[int] = None


class VisualContext(BaseModel):
    """Visual context for a conversation session."""
    person_id: str
    session_id: str
    active_media: List[VisualContextItem] = []
    visual_summary: Optional[str] = None
    objects_mentioned: List[str] = []
    people_mentioned: List[str] = []


async def add_to_visual_context(
    person_id: str,
    session_id: str,
    media_id: str,
    description: str,
    turn_index: Optional[int] = None,
    relevance: float = 1.0,
) -> bool:
    """
    Add a media item to the visual context.

    Args:
        person_id: User ID
        session_id: Conversation session ID
        media_id: ID of the media attachment
        description: Brief description of what's in the image
        turn_index: Which turn in the conversation
        relevance: How relevant (1.0 = current focus, 0.5 = background)
    """
    # Get or create visual context
    existing = await dbfetch(
        "SELECT * FROM visual_context WHERE person_id = $1 AND session_id = $2",
        person_id,
        session_id,
        one=True,
    )

    new_item = {
        "media_id": media_id,
        "description": description,
        "relevance": relevance,
        "turn_index": turn_index,
    }

    if existing:
        # Add to existing context
        active_media = existing.get("active_media") or []
        active_media.append(new_item)

        # Keep only last 10 items, decay relevance of older items
        for item in active_media[:-1]:
            item["relevance"] = item.get("relevance", 1.0) * 0.8

        active_media = active_media[-10:]

        await dbexec(
            """
            UPDATE visual_context
            SET active_media = $3::jsonb,
                updated_at = NOW()
            WHERE person_id = $1 AND session_id = $2
            """,
            person_id,
            session_id,
            json.dumps(active_media),
        )
    else:
        # Create new context
        await dbexec(
            """
            INSERT INTO visual_context (person_id, session_id, active_media)
            VALUES ($1, $2, $3::jsonb)
            """,
            person_id,
            session_id,
            json.dumps([new_item]),
        )

    # Also link to conversation_media
    await dbexec(
        """
        INSERT INTO conversation_media (media_id, session_id, turn_index, role, purpose)
        VALUES ($1, $2, $3, 'user', 'context')
        """,
        media_id,
        session_id,
        turn_index,
    )

    LOGGER.info(
        "[visual_context] Added media %s to session %s",
        media_id,
        session_id,
    )

    return True


async def get_visual_context(
    person_id: str,
    session_id: str,
) -> Optional[VisualContext]:
    """Get current visual context for a conversation."""
    row = await dbfetch(
        "SELECT * FROM visual_context WHERE person_id = $1 AND session_id = $2",
        person_id,
        session_id,
        one=True,
    )

    if not row:
        return None

    active_media = row.get("active_media") or []

    return VisualContext(
        person_id=row["person_id"],
        session_id=row["session_id"],
        active_media=[VisualContextItem(**item) for item in active_media],
        visual_summary=row.get("visual_summary"),
        objects_mentioned=row.get("objects_mentioned") or [],
        people_mentioned=row.get("people_mentioned") or [],
    )


async def update_visual_summary(
    person_id: str,
    session_id: str,
    summary: str,
    objects: Optional[List[str]] = None,
    people: Optional[List[str]] = None,
) -> bool:
    """Update the visual summary for a session."""
    updates = ["visual_summary = $3", "updated_at = NOW()"]
    params = [person_id, session_id, summary]
    param_idx = 4

    if objects is not None:
        updates.append(f"objects_mentioned = ${param_idx}::jsonb")
        params.append(json.dumps(objects))
        param_idx += 1

    if people is not None:
        updates.append(f"people_mentioned = ${param_idx}::jsonb")
        params.append(json.dumps(people))
        param_idx += 1

    await dbexec(
        f"""
        UPDATE visual_context
        SET {', '.join(updates)}
        WHERE person_id = $1 AND session_id = $2
        """,
        *params,
    )

    return True


async def clear_visual_context(
    person_id: str,
    session_id: str,
) -> bool:
    """Clear visual context for a session."""
    await dbexec(
        "DELETE FROM visual_context WHERE person_id = $1 AND session_id = $2",
        person_id,
        session_id,
    )
    return True


async def get_session_media(
    session_id: str,
) -> List[Dict[str, Any]]:
    """Get all media shared in a session with their context."""
    rows = await dbfetch(
        """
        SELECT
            m.id as media_id,
            m.media_type,
            m.mime_type,
            m.description,
            m.extracted_text,
            m.analysis,
            cm.turn_index,
            cm.role,
            cm.purpose
        FROM media_attachments m
        JOIN conversation_media cm ON cm.media_id = m.id
        WHERE cm.session_id = $1
        ORDER BY cm.turn_index
        """,
        session_id,
    )

    return [
        {
            "media_id": str(row["media_id"]),
            "media_type": row["media_type"],
            "mime_type": row["mime_type"],
            "description": row.get("description"),
            "extracted_text": row.get("extracted_text"),
            "analysis": row.get("analysis") or {},
            "turn_index": row.get("turn_index"),
            "role": row["role"],
            "purpose": row.get("purpose"),
        }
        for row in (rows or [])
    ]


async def get_relevant_media_for_context(
    person_id: str,
    session_id: str,
    max_items: int = 3,
) -> List[Dict[str, Any]]:
    """
    Get the most relevant media items for including in LLM context.

    Returns recent, high-relevance items with their descriptions.
    """
    context = await get_visual_context(person_id, session_id)
    if not context or not context.active_media:
        return []

    # Sort by relevance and take top items
    sorted_media = sorted(
        context.active_media,
        key=lambda x: x.relevance,
        reverse=True,
    )[:max_items]

    # Fetch full details
    result = []
    for item in sorted_media:
        row = await dbfetch(
            "SELECT * FROM media_attachments WHERE id = $1",
            item.media_id,
            one=True,
        )
        if row:
            result.append({
                "media_id": item.media_id,
                "description": item.description,
                "extracted_text": row.get("extracted_text"),
                "analysis": row.get("analysis") or {},
                "relevance": item.relevance,
            })

    return result


__all__ = [
    "VisualContextItem",
    "VisualContext",
    "add_to_visual_context",
    "get_visual_context",
    "update_visual_summary",
    "clear_visual_context",
    "get_session_media",
    "get_relevant_media_for_context",
]
