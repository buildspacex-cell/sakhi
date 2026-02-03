"""
Calendar API Routes
-------------------
Endpoints for Sakhi's native calendar that understands you.

Capabilities:
- Event CRUD with rich context
- Availability computation (calendar + preferences + rhythm)
- Intelligent scheduling suggestions
- Week/day summaries with context
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from sakhi.apps.api.services.calendar import (
    # Events
    create_event,
    get_event,
    update_event,
    delete_event,
    get_events_in_range,
    get_upcoming_events,
    CreateEventRequest,
    UpdateEventRequest,
    # Availability
    get_availability_windows,
    is_time_slot_available,
    find_best_times,
    WindowQuality,
)
from sakhi.apps.api.services.calendar.events import (
    get_events_for_day,
    get_events_for_week,
    get_week_summary,
    check_conflicts,
)

LOGGER = logging.getLogger(__name__)
router = APIRouter(prefix="/calendar", tags=["calendar"])


# =============================================================================
# Request/Response Models
# =============================================================================

class CreateEventBody(BaseModel):
    """Request body for creating an event."""
    title: str = Field(..., min_length=1, description="Event title")
    description: Optional[str] = None
    start_time: datetime
    end_time: datetime
    location: Optional[str] = None
    location_data: Optional[Dict[str, Any]] = None

    event_type: str = Field(default="personal", description="meeting, social, personal, work, blocked")
    category: Optional[str] = None
    energy_required: str = Field(default="medium", description="low, medium, high")
    is_flexible: bool = False

    related_person_ids: Optional[List[str]] = None
    conversation_context: Optional[str] = None


class UpdateEventBody(BaseModel):
    """Request body for updating an event."""
    title: Optional[str] = None
    description: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    location: Optional[str] = None

    event_type: Optional[str] = None
    category: Optional[str] = None
    energy_required: Optional[str] = None
    is_flexible: Optional[bool] = None

    related_person_ids: Optional[List[str]] = None
    energy_note: Optional[str] = None
    relationship_note: Optional[str] = None
    post_event_note: Optional[str] = None
    status: Optional[str] = None


class FindTimesRequest(BaseModel):
    """Request to find best times for an event."""
    duration_minutes: int = Field(default=60, ge=15, le=480)
    event_type: str = Field(default="meeting", description="meeting, social, focus, dinner, coffee")
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    limit: int = Field(default=5, ge=1, le=10)


class CheckAvailabilityRequest(BaseModel):
    """Request to check availability for a time slot."""
    start_time: datetime
    end_time: datetime


# =============================================================================
# Event CRUD Endpoints
# =============================================================================

@router.post("/{person_id}/events")
async def create_calendar_event(
    person_id: str,
    body: CreateEventBody,
) -> Dict[str, Any]:
    """
    Create a new calendar event.

    The event carries rich Sakhi context:
    - Who you're meeting (related_person_ids)
    - Why (conversation_context)
    - Energy requirements
    """
    request = CreateEventRequest(
        title=body.title,
        description=body.description,
        start_time=body.start_time,
        end_time=body.end_time,
        location=body.location,
        location_data=body.location_data,
        event_type=body.event_type,
        category=body.category,
        energy_required=body.energy_required,
        is_flexible=body.is_flexible,
        related_person_ids=body.related_person_ids,
        conversation_context=body.conversation_context,
        created_by="user",
    )

    try:
        event = await create_event(person_id, request)
        return {
            "status": "created",
            "event": event.model_dump(),
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        LOGGER.error(f"[Calendar] Create failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to create event")


@router.get("/{person_id}/events/{event_id}")
async def get_calendar_event(
    person_id: str,
    event_id: str,
) -> Dict[str, Any]:
    """Get a single event by ID."""
    event = await get_event(person_id, event_id)

    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    return {"event": event.model_dump()}


@router.patch("/{person_id}/events/{event_id}")
async def update_calendar_event(
    person_id: str,
    event_id: str,
    body: UpdateEventBody,
) -> Dict[str, Any]:
    """Update an existing event."""
    request = UpdateEventRequest(**body.model_dump(exclude_unset=True))

    event = await update_event(person_id, event_id, request)

    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    return {
        "status": "updated",
        "event": event.model_dump(),
    }


@router.delete("/{person_id}/events/{event_id}")
async def delete_calendar_event(
    person_id: str,
    event_id: str,
    hard_delete: bool = Query(default=False, description="Permanently delete instead of cancelling"),
) -> Dict[str, Any]:
    """Delete (or cancel) an event."""
    success = await delete_event(person_id, event_id, soft_delete=not hard_delete)

    if not success:
        raise HTTPException(status_code=404, detail="Event not found")

    return {
        "status": "deleted" if hard_delete else "cancelled",
        "event_id": event_id,
    }


# =============================================================================
# Query Endpoints
# =============================================================================

@router.get("/{person_id}/events")
async def list_events(
    person_id: str,
    start: Optional[datetime] = Query(default=None, description="Start of range"),
    end: Optional[datetime] = Query(default=None, description="End of range"),
    event_type: Optional[str] = Query(default=None, description="Filter by event type"),
    limit: int = Query(default=50, ge=1, le=200),
) -> Dict[str, Any]:
    """
    List events in a time range.

    If no range specified, returns upcoming events.
    """
    if start and end:
        events = await get_events_in_range(
            person_id,
            start,
            end,
            event_types=[event_type] if event_type else None,
        )
    else:
        events = await get_upcoming_events(
            person_id,
            limit=limit,
            event_types=[event_type] if event_type else None,
        )

    return {
        "events": [e.model_dump() for e in events],
        "count": len(events),
    }


@router.get("/{person_id}/today")
async def get_today_events(person_id: str) -> Dict[str, Any]:
    """Get all events for today."""
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    events = await get_events_for_day(person_id, today)

    return {
        "date": today.date().isoformat(),
        "events": [e.model_dump() for e in events],
        "count": len(events),
    }


@router.get("/{person_id}/week")
async def get_week_events(
    person_id: str,
    week_start: Optional[datetime] = Query(default=None, description="Start of week (Monday)"),
) -> Dict[str, Any]:
    """
    Get all events for a week with summary.

    Returns events plus contextual summary (how busy, who you're seeing).
    """
    events = await get_events_for_week(person_id, week_start)
    summary = await get_week_summary(person_id, week_start)

    # Determine actual week bounds
    if week_start is None:
        today = datetime.now()
        actual_start = today - timedelta(days=today.weekday())
    else:
        actual_start = week_start
    actual_start = actual_start.replace(hour=0, minute=0, second=0, microsecond=0)

    return {
        "week_start": actual_start.date().isoformat(),
        "week_end": (actual_start + timedelta(days=6)).date().isoformat(),
        "events": [e.model_dump() for e in events],
        "summary": summary,
    }


# =============================================================================
# Availability Endpoints
# =============================================================================

@router.get("/{person_id}/availability")
async def get_availability(
    person_id: str,
    start: datetime = Query(..., description="Start of range"),
    end: datetime = Query(..., description="End of range"),
    min_quality: str = Query(default="available", description="Minimum quality: preferred, available, suboptimal, emergency_only"),
    event_type: Optional[str] = Query(default=None, description="Filter for event type: meeting, social, focus"),
) -> Dict[str, Any]:
    """
    Get availability windows for a time range.

    Windows are quality-rated:
    - preferred: Ideal time for this type of activity
    - available: Good, can do
    - suboptimal: Rather not, but can if needed
    - emergency_only: Only for urgent matters
    """
    try:
        quality = WindowQuality(min_quality)
    except ValueError:
        quality = WindowQuality.AVAILABLE

    windows = await get_availability_windows(
        person_id,
        start,
        end,
        min_quality=quality,
        event_type=event_type,
    )

    return {
        "windows": [
            {
                "start": w.start.isoformat(),
                "end": w.end.isoformat(),
                "quality": w.quality.value,
                "reason": w.reason,
                "energy_level": w.energy_level,
                "good_for": w.good_for,
            }
            for w in windows
        ],
        "count": len(windows),
        "range": {
            "start": start.isoformat(),
            "end": end.isoformat(),
        },
    }


@router.post("/{person_id}/availability/check")
async def check_slot_availability(
    person_id: str,
    body: CheckAvailabilityRequest,
) -> Dict[str, Any]:
    """Check if a specific time slot is available."""
    is_available, reason = await is_time_slot_available(
        person_id,
        body.start_time,
        body.end_time,
    )

    # Also check for conflicts
    conflicts = await check_conflicts(person_id, body.start_time, body.end_time)

    return {
        "available": is_available,
        "reason": reason,
        "conflicts": [
            {"id": c.id, "title": c.title, "start": c.start_time.isoformat()}
            for c in conflicts
        ] if conflicts else [],
    }


@router.post("/{person_id}/availability/find-times")
async def find_available_times(
    person_id: str,
    body: FindTimesRequest,
) -> Dict[str, Any]:
    """
    Find the best times for a specific type of event.

    Returns scored suggestions based on:
    - Calendar availability
    - Your preferences
    - Energy patterns
    - Event type requirements
    """
    # Default to next 7 days if not specified
    start_date = body.start_date or datetime.now()
    end_date = body.end_date or (start_date + timedelta(days=7))

    suggestions = await find_best_times(
        person_id,
        body.duration_minutes,
        body.event_type,
        start_date,
        end_date,
        body.limit,
    )

    return {
        "suggestions": [
            {
                "start": s["start"].isoformat(),
                "end": s["end"].isoformat(),
                "score": s["score"],
                "quality": s["quality"],
                "energy_level": s["energy_level"],
                "reasoning": s["reasoning"],
            }
            for s in suggestions
        ],
        "search_params": {
            "duration_minutes": body.duration_minutes,
            "event_type": body.event_type,
            "range_start": start_date.isoformat(),
            "range_end": end_date.isoformat(),
        },
    }


# =============================================================================
# Summary Endpoints
# =============================================================================

@router.get("/{person_id}/summary")
async def get_calendar_summary(
    person_id: str,
    days: int = Query(default=7, ge=1, le=30, description="Number of days to summarize"),
) -> Dict[str, Any]:
    """
    Get a summary of upcoming schedule.

    Returns:
    - Event counts by type
    - Total scheduled hours
    - People you're meeting
    - Busiest day
    """
    start = datetime.now()
    end = start + timedelta(days=days)

    events = await get_events_in_range(person_id, start, end)

    # Build summary
    type_counts: Dict[str, int] = {}
    total_hours = 0.0
    people: List[str] = []

    for event in events:
        type_counts[event.event_type] = type_counts.get(event.event_type, 0) + 1
        duration = (event.end_time - event.start_time).total_seconds() / 3600
        total_hours += duration
        if event.related_person_ids:
            people.extend(event.related_person_ids)

    unique_people = list(set(people))

    # Find free days
    days_with_events = set()
    for event in events:
        days_with_events.add(event.start_time.date())

    free_days = []
    current_date = start.date()
    while current_date <= end.date():
        if current_date not in days_with_events:
            free_days.append(current_date.isoformat())
        current_date += timedelta(days=1)

    return {
        "period": {
            "start": start.date().isoformat(),
            "end": end.date().isoformat(),
            "days": days,
        },
        "event_count": len(events),
        "type_breakdown": type_counts,
        "total_scheduled_hours": round(total_hours, 1),
        "people_count": len(unique_people),
        "people_ids": unique_people[:10],  # Limit for response size
        "free_days": free_days[:5],  # First 5 free days
    }


__all__ = ["router"]
