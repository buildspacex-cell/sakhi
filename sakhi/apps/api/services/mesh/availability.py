"""
Mesh Availability Sharing
-------------------------
Privacy-respecting availability sharing based on trust levels.

Trust levels control what information is shared:
- ACQUAINTANCE: busy/free only
- FRIEND: preferred/available/suboptimal windows
- CLOSE_FRIEND: full availability with energy states
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from enum import Enum

from pydantic import BaseModel

from sakhi.apps.api.core.db import q
from sakhi.apps.api.services.mesh.connections import TrustLevel, get_trust_level
from sakhi.apps.api.services.mesh.entities import get_entity_by_person as get_profile

logger = logging.getLogger(__name__)


class AvailabilityDetail(str, Enum):
    """Level of detail for availability sharing."""
    NONE = "none"           # Don't share availability
    BUSY_FREE = "busy_free"  # Only show busy/free
    WINDOWS = "windows"      # Show preferred/available/suboptimal windows
    FULL = "full"           # Full details with energy states


class TimeSlot(BaseModel):
    """A time slot with quality indicator."""
    start: datetime
    end: datetime
    status: str = "free"  # busy, free
    quality: Optional[str] = None  # preferred, available, suboptimal
    energy_state: Optional[str] = None  # Only for FULL detail
    event_type_hint: Optional[str] = None  # What kind of event might fit here


class SharedAvailability(BaseModel):
    """Availability data formatted for sharing."""
    person_id: str
    valid_from: datetime
    valid_until: datetime
    detail_level: AvailabilityDetail
    slots: List[TimeSlot]
    computed_at: datetime


async def get_calendar_events(
    person_id: str,
    start: datetime,
    end: datetime,
) -> List[Dict[str, Any]]:
    """Get calendar events for a person in a time range."""
    rows = await q(
        """
        SELECT id, title, start_time, end_time, event_type, energy_required
        FROM calendar_events
        WHERE person_id = $1
          AND start_time >= $2
          AND end_time <= $3
          AND status != 'cancelled'
        ORDER BY start_time
        """,
        person_id,
        start,
        end,
    )
    return [dict(r) for r in rows] if rows else []


async def get_energy_predictions(
    person_id: str,
    start: datetime,
    end: datetime,
) -> Dict[str, Any]:
    """Get energy predictions for time slots."""
    # For now, return a simple pattern based on time of day
    # In full implementation, this would query energy_predictions table
    try:
        row = await q(
            """
            SELECT rhythm_state
            FROM personal_model
            WHERE person_id = $1
            """,
            person_id,
            one=True,
        )
        if row and row.get("rhythm_state"):
            return row.get("rhythm_state") or {}
    except Exception:
        pass
    return {}


def _compute_busy_free(
    events: List[Dict[str, Any]],
    start: datetime,
    end: datetime,
) -> List[TimeSlot]:
    """Compute simple busy/free slots (ACQUAINTANCE level)."""
    slots: List[TimeSlot] = []
    current = start

    # Sort events by start time
    sorted_events = sorted(events, key=lambda e: e.get("start_time", start))

    for event in sorted_events:
        event_start = event.get("start_time")
        event_end = event.get("end_time")

        if not event_start or not event_end:
            continue

        # Add free slot before this event
        if current < event_start:
            slots.append(TimeSlot(
                start=current,
                end=event_start,
                status="free",
            ))

        # Add busy slot for the event
        slots.append(TimeSlot(
            start=event_start,
            end=event_end,
            status="busy",
        ))

        current = max(current, event_end)

    # Add final free slot if needed
    if current < end:
        slots.append(TimeSlot(
            start=current,
            end=end,
            status="free",
        ))

    return slots


def _compute_windows(
    events: List[Dict[str, Any]],
    start: datetime,
    end: datetime,
    rhythm_state: Dict[str, Any],
) -> List[TimeSlot]:
    """Compute windows with quality indicators (FRIEND level)."""
    slots = _compute_busy_free(events, start, end)

    # Enhance free slots with quality based on time of day and patterns
    enhanced_slots: List[TimeSlot] = []

    for slot in slots:
        if slot.status == "busy":
            enhanced_slots.append(slot)
            continue

        # Determine quality based on time of day
        hour = slot.start.hour
        duration_hours = (slot.end - slot.start).total_seconds() / 3600

        # Morning: 9-12 is preferred for focused work
        # Afternoon: 14-17 is available for meetings
        # Evening: 19-21 is suboptimal for work meetings
        if 9 <= hour < 12 and duration_hours >= 1:
            quality = "preferred"
        elif 14 <= hour < 17 and duration_hours >= 0.5:
            quality = "available"
        elif 19 <= hour < 21:
            quality = "suboptimal"
        elif 10 <= hour < 18:
            quality = "available"
        else:
            quality = "suboptimal"

        enhanced_slots.append(TimeSlot(
            start=slot.start,
            end=slot.end,
            status="free",
            quality=quality,
        ))

    return enhanced_slots


def _compute_full_availability(
    events: List[Dict[str, Any]],
    start: datetime,
    end: datetime,
    rhythm_state: Dict[str, Any],
) -> List[TimeSlot]:
    """Compute full availability with energy states (CLOSE_FRIEND level)."""
    slots = _compute_windows(events, start, end, rhythm_state)

    # Enhance with energy predictions
    enhanced_slots: List[TimeSlot] = []

    for slot in slots:
        if slot.status == "busy":
            enhanced_slots.append(slot)
            continue

        hour = slot.start.hour

        # Simple energy model based on typical patterns
        # Can be enhanced with actual rhythm_state data
        if 9 <= hour < 11:
            energy = "high"
        elif 11 <= hour < 13:
            energy = "medium"
        elif 13 <= hour < 15:
            energy = "low"  # Post-lunch dip
        elif 15 <= hour < 17:
            energy = "medium"
        elif 17 <= hour < 19:
            energy = "winding_down"
        else:
            energy = "low"

        # Suggest event types based on energy and quality
        event_hint = None
        if slot.quality == "preferred" and energy == "high":
            event_hint = "deep_work or important_meeting"
        elif slot.quality == "available" and energy in ("medium", "high"):
            event_hint = "meeting or call"
        elif slot.quality == "suboptimal":
            event_hint = "light_catch_up or social"

        enhanced_slots.append(TimeSlot(
            start=slot.start,
            end=slot.end,
            status="free",
            quality=slot.quality,
            energy_state=energy,
            event_type_hint=event_hint,
        ))

    return enhanced_slots


async def compute_shareable_availability(
    person_id: str,
    requester_id: str,
    start: datetime,
    end: datetime,
) -> Optional[SharedAvailability]:
    """
    Compute availability to share based on trust level and preferences.

    Returns None if:
    - Not connected
    - Profile has share_availability=False
    - Profile has availability_detail='none'
    """
    # Check connection and trust level
    trust = await get_trust_level(person_id, requester_id)
    if not trust:
        logger.debug("No connection between %s and %s", person_id, requester_id)
        return None

    # Get profile preferences
    profile = await get_profile(person_id)
    if not profile:
        logger.debug("No profile for %s", person_id)
        return None

    if not profile.share_availability:
        logger.debug("%s has disabled availability sharing", person_id)
        return None

    detail_pref = AvailabilityDetail(profile.availability_detail)
    if detail_pref == AvailabilityDetail.NONE:
        logger.debug("%s has availability_detail=none", person_id)
        return None

    # Determine effective detail level based on trust
    effective_detail = detail_pref

    # Trust-based restrictions
    if trust == TrustLevel.ACQUAINTANCE:
        # Acquaintances only get busy/free regardless of preference
        effective_detail = AvailabilityDetail.BUSY_FREE
    elif trust == TrustLevel.FRIEND:
        # Friends get up to windows, but not full
        if detail_pref == AvailabilityDetail.FULL:
            effective_detail = AvailabilityDetail.WINDOWS

    # Close friends can see whatever the profile allows

    # Get calendar events
    events = await get_calendar_events(person_id, start, end)

    # Get rhythm state for energy predictions
    rhythm_state = await get_energy_predictions(person_id, start, end)

    # Compute slots based on detail level
    if effective_detail == AvailabilityDetail.BUSY_FREE:
        slots = _compute_busy_free(events, start, end)
    elif effective_detail == AvailabilityDetail.WINDOWS:
        slots = _compute_windows(events, start, end, rhythm_state)
    else:  # FULL
        slots = _compute_full_availability(events, start, end, rhythm_state)

    return SharedAvailability(
        person_id=person_id,
        valid_from=start,
        valid_until=end,
        detail_level=effective_detail,
        slots=slots,
        computed_at=datetime.utcnow(),
    )


async def cache_shared_availability(
    availability: SharedAvailability,
) -> str:
    """Cache computed availability for quick access."""
    rows = await q(
        """
        INSERT INTO shared_availability (
            person_id, valid_from, valid_until,
            busy_free, windows, detailed, computed_at
        )
        VALUES ($1, $2, $3, $4, $5, $6, $7)
        ON CONFLICT (person_id, valid_from)
        DO UPDATE SET
            valid_until = EXCLUDED.valid_until,
            busy_free = EXCLUDED.busy_free,
            windows = EXCLUDED.windows,
            detailed = EXCLUDED.detailed,
            computed_at = EXCLUDED.computed_at
        RETURNING id
        """,
        availability.person_id,
        availability.valid_from,
        availability.valid_until,
        [s.model_dump() for s in availability.slots if s.status in ("busy", "free")],
        [s.model_dump() for s in availability.slots if s.quality],
        [s.model_dump() for s in availability.slots if s.energy_state],
        availability.computed_at,
        one=True,
    )
    return str(rows["id"]) if rows else ""


async def find_overlapping_times(
    person_a_id: str,
    person_b_id: str,
    start: datetime,
    end: datetime,
    duration_minutes: int = 60,
) -> List[Dict[str, Any]]:
    """
    Find overlapping free times between two people.

    Returns times that work for both, sorted by quality.
    """
    # Get availability for both
    avail_a = await compute_shareable_availability(
        person_a_id, person_b_id, start, end
    )
    avail_b = await compute_shareable_availability(
        person_b_id, person_a_id, start, end
    )

    if not avail_a or not avail_b:
        return []

    # Find overlapping free slots
    overlaps: List[Dict[str, Any]] = []

    for slot_a in avail_a.slots:
        if slot_a.status != "free":
            continue

        for slot_b in avail_b.slots:
            if slot_b.status != "free":
                continue

            # Find overlap
            overlap_start = max(slot_a.start, slot_b.start)
            overlap_end = min(slot_a.end, slot_b.end)

            # Check if overlap is long enough
            overlap_minutes = (overlap_end - overlap_start).total_seconds() / 60
            if overlap_minutes >= duration_minutes:
                # Determine combined quality
                quality_order = {"preferred": 3, "available": 2, "suboptimal": 1, None: 2}
                combined_quality_score = (
                    quality_order.get(slot_a.quality, 2) +
                    quality_order.get(slot_b.quality, 2)
                ) / 2

                if combined_quality_score >= 2.5:
                    quality = "preferred"
                elif combined_quality_score >= 1.5:
                    quality = "available"
                else:
                    quality = "suboptimal"

                overlaps.append({
                    "start": overlap_start,
                    "end": overlap_end,
                    "quality": quality,
                    "quality_reason": f"Works for both ({slot_a.quality or 'available'} for you, {slot_b.quality or 'available'} for them)",
                })

    # Sort by quality (preferred first) then by time
    quality_sort = {"preferred": 0, "available": 1, "suboptimal": 2}
    overlaps.sort(key=lambda x: (quality_sort.get(x["quality"], 1), x["start"]))

    return overlaps


__all__ = [
    "AvailabilityDetail",
    "TimeSlot",
    "SharedAvailability",
    "compute_shareable_availability",
    "cache_shared_availability",
    "find_overlapping_times",
]
