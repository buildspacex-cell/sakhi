"""
Calendar Events Service
-----------------------
CRUD operations for calendar events with Sakhi-native context.

Events are more than time blocks - they carry:
- Who you're meeting (relationship context)
- Why you're meeting (conversation context)
- How it affects you (energy requirements)
- What Sakhi noticed (reflective notes)
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from sakhi.apps.api.core.db import q as dbfetch, exec as execute

LOGGER = logging.getLogger(__name__)


# =============================================================================
# Models
# =============================================================================

class CalendarEvent(BaseModel):
    """A calendar event with Sakhi-native context."""
    id: str
    person_id: str
    title: str
    description: Optional[str] = None
    start_time: datetime
    end_time: datetime
    location: Optional[str] = None
    location_data: Optional[Dict[str, Any]] = None

    # Classification
    event_type: str = "personal"
    category: Optional[str] = None
    energy_required: str = "medium"
    is_flexible: bool = False

    # Sakhi context
    created_by: str = "user"
    related_person_ids: Optional[List[str]] = None
    conversation_context: Optional[str] = None
    source_entry_id: Optional[str] = None

    # Coordination
    coordination_id: Optional[str] = None
    coordination_status: Optional[str] = None

    # Reflective context
    energy_note: Optional[str] = None
    relationship_note: Optional[str] = None
    pre_event_ritual: Optional[str] = None
    post_event_note: Optional[str] = None

    # Status
    status: str = "confirmed"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class CreateEventRequest(BaseModel):
    """Request to create a calendar event."""
    title: str = Field(..., min_length=1, max_length=500)
    description: Optional[str] = None
    start_time: datetime
    end_time: datetime
    location: Optional[str] = None
    location_data: Optional[Dict[str, Any]] = None

    event_type: str = Field(default="personal")
    category: Optional[str] = None
    energy_required: str = Field(default="medium")
    is_flexible: bool = False

    created_by: str = Field(default="user")
    related_person_ids: Optional[List[str]] = None
    conversation_context: Optional[str] = None
    source_entry_id: Optional[str] = None

    status: str = Field(default="confirmed")


class UpdateEventRequest(BaseModel):
    """Request to update a calendar event."""
    title: Optional[str] = None
    description: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    location: Optional[str] = None
    location_data: Optional[Dict[str, Any]] = None

    event_type: Optional[str] = None
    category: Optional[str] = None
    energy_required: Optional[str] = None
    is_flexible: Optional[bool] = None

    related_person_ids: Optional[List[str]] = None
    conversation_context: Optional[str] = None

    energy_note: Optional[str] = None
    relationship_note: Optional[str] = None
    pre_event_ritual: Optional[str] = None
    post_event_note: Optional[str] = None

    status: Optional[str] = None


# =============================================================================
# CRUD Operations
# =============================================================================

async def create_event(
    person_id: str,
    request: CreateEventRequest,
) -> CalendarEvent:
    """
    Create a new calendar event.

    Args:
        person_id: The user's ID
        request: Event creation request

    Returns:
        The created event
    """
    # Validate time range
    if request.end_time <= request.start_time:
        raise ValueError("End time must be after start time")

    result = await dbfetch(
        """
        INSERT INTO calendar_events (
            person_id, title, description,
            start_time, end_time,
            location, location_data,
            event_type, category, energy_required, is_flexible,
            created_by, related_person_ids, conversation_context, source_entry_id,
            status
        ) VALUES (
            $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16
        )
        RETURNING *
        """,
        person_id,
        request.title,
        request.description,
        request.start_time,
        request.end_time,
        request.location,
        request.location_data,
        request.event_type,
        request.category,
        request.energy_required,
        request.is_flexible,
        request.created_by,
        request.related_person_ids,
        request.conversation_context,
        request.source_entry_id,
        request.status,
        one=True,
    )

    LOGGER.info(
        "[Calendar] Created event: person=%s title=%s start=%s",
        person_id,
        request.title,
        request.start_time.isoformat(),
    )

    return _row_to_event(result)


async def get_event(
    person_id: str,
    event_id: str,
) -> Optional[CalendarEvent]:
    """
    Get a single event by ID.

    Args:
        person_id: The user's ID
        event_id: The event ID

    Returns:
        The event if found, None otherwise
    """
    result = await dbfetch(
        """
        SELECT * FROM calendar_events
        WHERE id = $1 AND person_id = $2
        """,
        event_id,
        person_id,
        one=True,
    )

    if not result:
        return None

    return _row_to_event(result)


async def update_event(
    person_id: str,
    event_id: str,
    request: UpdateEventRequest,
) -> Optional[CalendarEvent]:
    """
    Update an existing event.

    Args:
        person_id: The user's ID
        event_id: The event ID
        request: Update request with fields to change

    Returns:
        The updated event if found
    """
    # Build dynamic update query
    updates = []
    params = []
    param_idx = 1

    update_fields = request.model_dump(exclude_unset=True)
    for field, value in update_fields.items():
        if value is not None:
            updates.append(f"{field} = ${param_idx}")
            params.append(value)
            param_idx += 1

    if not updates:
        # Nothing to update
        return await get_event(person_id, event_id)

    # Add WHERE clause params
    params.extend([event_id, person_id])

    query = f"""
        UPDATE calendar_events
        SET {', '.join(updates)}, updated_at = NOW()
        WHERE id = ${param_idx} AND person_id = ${param_idx + 1}
        RETURNING *
    """

    result = await dbfetch(query, *params, one=True)

    if not result:
        return None

    LOGGER.info(
        "[Calendar] Updated event: person=%s event_id=%s fields=%s",
        person_id,
        event_id,
        list(update_fields.keys()),
    )

    return _row_to_event(result)


async def delete_event(
    person_id: str,
    event_id: str,
    soft_delete: bool = True,
) -> bool:
    """
    Delete an event.

    Args:
        person_id: The user's ID
        event_id: The event ID
        soft_delete: If True, mark as cancelled instead of deleting

    Returns:
        True if event was deleted/cancelled
    """
    if soft_delete:
        result = await dbfetch(
            """
            UPDATE calendar_events
            SET status = 'cancelled', updated_at = NOW()
            WHERE id = $1 AND person_id = $2
            RETURNING id
            """,
            event_id,
            person_id,
            one=True,
        )
    else:
        result = await dbfetch(
            """
            DELETE FROM calendar_events
            WHERE id = $1 AND person_id = $2
            RETURNING id
            """,
            event_id,
            person_id,
            one=True,
        )

    if result:
        LOGGER.info(
            "[Calendar] Deleted event: person=%s event_id=%s soft=%s",
            person_id,
            event_id,
            soft_delete,
        )
        return True

    return False


# =============================================================================
# Query Operations
# =============================================================================

async def get_events_in_range(
    person_id: str,
    start: datetime,
    end: datetime,
    include_cancelled: bool = False,
    event_types: Optional[List[str]] = None,
) -> List[CalendarEvent]:
    """
    Get events in a time range.

    Args:
        person_id: The user's ID
        start: Range start (inclusive)
        end: Range end (exclusive)
        include_cancelled: Whether to include cancelled events
        event_types: Filter by event types

    Returns:
        List of events in the range
    """
    query = """
        SELECT * FROM calendar_events
        WHERE person_id = $1
          AND start_time < $3
          AND end_time > $2
    """
    params = [person_id, start, end]

    if not include_cancelled:
        query += " AND status != 'cancelled'"

    if event_types:
        query += f" AND event_type = ANY(${len(params) + 1})"
        params.append(event_types)

    query += " ORDER BY start_time"

    results = await dbfetch(query, *params)

    return [_row_to_event(row) for row in (results or [])]


async def get_upcoming_events(
    person_id: str,
    limit: int = 10,
    event_types: Optional[List[str]] = None,
) -> List[CalendarEvent]:
    """
    Get upcoming events.

    Args:
        person_id: The user's ID
        limit: Maximum number of events
        event_types: Filter by event types

    Returns:
        List of upcoming events
    """
    query = """
        SELECT * FROM calendar_events
        WHERE person_id = $1
          AND status != 'cancelled'
          AND start_time > NOW()
    """
    params = [person_id]

    if event_types:
        query += f" AND event_type = ANY(${len(params) + 1})"
        params.append(event_types)

    query += f" ORDER BY start_time LIMIT ${len(params) + 1}"
    params.append(limit)

    results = await dbfetch(query, *params)

    return [_row_to_event(row) for row in (results or [])]


async def get_events_for_day(
    person_id: str,
    date: datetime,
) -> List[CalendarEvent]:
    """
    Get all events for a specific day.

    Args:
        person_id: The user's ID
        date: The day to query

    Returns:
        List of events on that day
    """
    day_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
    day_end = day_start + timedelta(days=1)

    return await get_events_in_range(person_id, day_start, day_end)


async def get_events_for_week(
    person_id: str,
    week_start: Optional[datetime] = None,
) -> List[CalendarEvent]:
    """
    Get all events for a week.

    Args:
        person_id: The user's ID
        week_start: Start of week (defaults to current week's Monday)

    Returns:
        List of events in the week
    """
    if week_start is None:
        today = datetime.now()
        # Go to Monday of current week
        week_start = today - timedelta(days=today.weekday())

    week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
    week_end = week_start + timedelta(days=7)

    return await get_events_in_range(person_id, week_start, week_end)


async def check_conflicts(
    person_id: str,
    start: datetime,
    end: datetime,
    exclude_event_id: Optional[str] = None,
) -> List[CalendarEvent]:
    """
    Check for conflicting events in a time range.

    Args:
        person_id: The user's ID
        start: Proposed start time
        end: Proposed end time
        exclude_event_id: Event ID to exclude (for updates)

    Returns:
        List of conflicting events
    """
    query = """
        SELECT * FROM calendar_events
        WHERE person_id = $1
          AND status != 'cancelled'
          AND start_time < $3
          AND end_time > $2
    """
    params = [person_id, start, end]

    if exclude_event_id:
        query += f" AND id != ${len(params) + 1}"
        params.append(exclude_event_id)

    query += " ORDER BY start_time"

    results = await dbfetch(query, *params)

    return [_row_to_event(row) for row in (results or [])]


# =============================================================================
# Summary Operations
# =============================================================================

async def get_week_summary(
    person_id: str,
    week_start: Optional[datetime] = None,
) -> Dict[str, Any]:
    """
    Get a summary of the week's schedule.

    Returns:
        Dict with event counts, busy times, and notable events
    """
    events = await get_events_for_week(person_id, week_start)

    # Count by type
    type_counts: Dict[str, int] = {}
    total_hours = 0.0
    people_seeing: List[str] = []

    for event in events:
        type_counts[event.event_type] = type_counts.get(event.event_type, 0) + 1
        duration = (event.end_time - event.start_time).total_seconds() / 3600
        total_hours += duration
        if event.related_person_ids:
            people_seeing.extend(event.related_person_ids)

    # Unique people
    unique_people = list(set(people_seeing))

    return {
        "event_count": len(events),
        "type_breakdown": type_counts,
        "total_scheduled_hours": round(total_hours, 1),
        "people_count": len(unique_people),
        "people_ids": unique_people,
        "busiest_day": _find_busiest_day(events) if events else None,
    }


def _find_busiest_day(events: List[CalendarEvent]) -> Optional[str]:
    """Find the day with most events."""
    day_counts: Dict[str, int] = {}
    for event in events:
        day = event.start_time.strftime("%A")
        day_counts[day] = day_counts.get(day, 0) + 1

    if not day_counts:
        return None

    return max(day_counts, key=day_counts.get)


# =============================================================================
# Helpers
# =============================================================================

def _row_to_event(row: Dict[str, Any]) -> CalendarEvent:
    """Convert a database row to a CalendarEvent."""
    return CalendarEvent(
        id=str(row["id"]),
        person_id=row["person_id"],
        title=row["title"],
        description=row.get("description"),
        start_time=row["start_time"],
        end_time=row["end_time"],
        location=row.get("location"),
        location_data=row.get("location_data"),
        event_type=row.get("event_type", "personal"),
        category=row.get("category"),
        energy_required=row.get("energy_required", "medium"),
        is_flexible=row.get("is_flexible", False),
        created_by=row.get("created_by", "user"),
        related_person_ids=row.get("related_person_ids"),
        conversation_context=row.get("conversation_context"),
        source_entry_id=str(row["source_entry_id"]) if row.get("source_entry_id") else None,
        coordination_id=str(row["coordination_id"]) if row.get("coordination_id") else None,
        coordination_status=row.get("coordination_status"),
        energy_note=row.get("energy_note"),
        relationship_note=row.get("relationship_note"),
        pre_event_ritual=row.get("pre_event_ritual"),
        post_event_note=row.get("post_event_note"),
        status=row.get("status", "confirmed"),
        created_at=row.get("created_at"),
        updated_at=row.get("updated_at"),
    )


__all__ = [
    "CalendarEvent",
    "CreateEventRequest",
    "UpdateEventRequest",
    "create_event",
    "get_event",
    "update_event",
    "delete_event",
    "get_events_in_range",
    "get_upcoming_events",
    "get_events_for_day",
    "get_events_for_week",
    "check_conflicts",
    "get_week_summary",
]
