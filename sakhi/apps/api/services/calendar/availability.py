"""
Availability Service
--------------------
Computes availability windows by combining:
- Calendar events (what's already scheduled)
- Scheduling preferences (when you like to meet)
- Rhythm state (your energy patterns)
- Operating system (dosha-based energy awareness)

The result is not just "free/busy" but quality-scored windows:
- Preferred: Ideal time for this type of activity
- Available: Can do it, but not optimal
- Suboptimal: Would rather not, but can if needed
- Emergency Only: Only for urgent matters
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, time
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum

from pydantic import BaseModel

from sakhi.apps.api.core.db import q as dbfetch, exec as execute
from sakhi.apps.api.services.calendar.events import get_events_in_range

LOGGER = logging.getLogger(__name__)


# =============================================================================
# Models
# =============================================================================

class WindowQuality(str, Enum):
    """Quality rating for an availability window."""
    PREFERRED = "preferred"       # Ideal time
    AVAILABLE = "available"       # Good, can do
    SUBOPTIMAL = "suboptimal"     # Rather not, but can
    EMERGENCY = "emergency_only"  # Only if urgent


class AvailabilityWindow(BaseModel):
    """A window of availability with quality rating."""
    start: datetime
    end: datetime
    quality: WindowQuality
    reason: Optional[str] = None
    energy_level: Optional[str] = None  # 'high', 'medium', 'low'
    good_for: Optional[List[str]] = None  # ['meetings', 'focus', 'social']


class AvailabilityRequest(BaseModel):
    """Request for availability computation."""
    start_date: datetime
    end_date: datetime
    event_type: Optional[str] = None  # 'meeting', 'social', 'focus'
    duration_minutes: int = 60
    min_quality: WindowQuality = WindowQuality.AVAILABLE


# =============================================================================
# Core Availability Computation
# =============================================================================

async def compute_availability(
    person_id: str,
    start_date: datetime,
    end_date: datetime,
    granularity_minutes: int = 30,
) -> List[AvailabilityWindow]:
    """
    Compute availability windows for a date range.

    Combines:
    1. Calendar events (busy times)
    2. Scheduling preferences (preferred times)
    3. Energy patterns from rhythm state
    4. Operating system characteristics

    Args:
        person_id: The user's ID
        start_date: Start of range
        end_date: End of range
        granularity_minutes: Slot size for computation

    Returns:
        List of availability windows with quality ratings
    """
    # Load all inputs in parallel
    events = await get_events_in_range(person_id, start_date, end_date)
    preferences = await _load_scheduling_preferences(person_id)
    rhythm_state = await _load_rhythm_state(person_id)
    operating_system = await _load_operating_system(person_id)

    # Generate all potential slots
    slots = _generate_time_slots(start_date, end_date, granularity_minutes)

    # Mark busy times
    busy_periods = _extract_busy_periods(events)

    # Compute availability for each slot
    windows: List[AvailabilityWindow] = []
    current_window: Optional[AvailabilityWindow] = None

    for slot_start, slot_end in slots:
        # Check if busy
        if _is_period_busy(slot_start, slot_end, busy_periods):
            # Close any open window
            if current_window:
                windows.append(current_window)
                current_window = None
            continue

        # Compute quality based on preferences and rhythm
        quality, reason, energy = _compute_slot_quality(
            slot_start,
            slot_end,
            preferences,
            rhythm_state,
            operating_system,
        )

        # Determine what this slot is good for
        good_for = _determine_good_for(quality, energy, operating_system)

        # Extend current window or start new one
        if current_window and current_window.quality == quality:
            # Extend the window
            current_window.end = slot_end
        else:
            # Close previous window
            if current_window:
                windows.append(current_window)

            # Start new window
            current_window = AvailabilityWindow(
                start=slot_start,
                end=slot_end,
                quality=quality,
                reason=reason,
                energy_level=energy,
                good_for=good_for,
            )

    # Don't forget the last window
    if current_window:
        windows.append(current_window)

    # Cache the results
    await _cache_availability(person_id, windows, start_date, end_date)

    LOGGER.info(
        "[Availability] Computed %d windows for person=%s range=%s to %s",
        len(windows),
        person_id,
        start_date.isoformat(),
        end_date.isoformat(),
    )

    return windows


async def get_availability_windows(
    person_id: str,
    start_date: datetime,
    end_date: datetime,
    min_quality: WindowQuality = WindowQuality.AVAILABLE,
    event_type: Optional[str] = None,
) -> List[AvailabilityWindow]:
    """
    Get availability windows, filtered by quality and event type.

    Args:
        person_id: The user's ID
        start_date: Start of range
        end_date: End of range
        min_quality: Minimum quality to include
        event_type: Filter windows good for this event type

    Returns:
        Filtered list of availability windows
    """
    # Check cache first
    cached = await _get_cached_availability(person_id, start_date, end_date)

    if cached:
        windows = cached
    else:
        windows = await compute_availability(person_id, start_date, end_date)

    # Filter by quality
    quality_order = [WindowQuality.PREFERRED, WindowQuality.AVAILABLE,
                     WindowQuality.SUBOPTIMAL, WindowQuality.EMERGENCY]
    min_idx = quality_order.index(min_quality)
    acceptable_qualities = quality_order[:min_idx + 1]

    windows = [w for w in windows if w.quality in acceptable_qualities]

    # Filter by event type
    if event_type and event_type != "any":
        event_type_map = {
            "meeting": "meetings",
            "social": "social",
            "focus": "focus",
            "work": "meetings",
            "dinner": "social",
            "coffee": "social",
            "call": "meetings",
        }
        good_for_key = event_type_map.get(event_type, event_type)
        windows = [w for w in windows if w.good_for and good_for_key in w.good_for]

    return windows


async def is_time_slot_available(
    person_id: str,
    start: datetime,
    end: datetime,
) -> Tuple[bool, Optional[str]]:
    """
    Check if a specific time slot is available.

    Returns:
        Tuple of (is_available, reason if not available)
    """
    # Check for conflicts
    from sakhi.apps.api.services.calendar.events import check_conflicts
    conflicts = await check_conflicts(person_id, start, end)

    if conflicts:
        conflict_titles = [c.title for c in conflicts[:2]]
        reason = f"Conflicts with: {', '.join(conflict_titles)}"
        return False, reason

    return True, None


async def find_best_times(
    person_id: str,
    duration_minutes: int,
    event_type: str,
    start_date: datetime,
    end_date: datetime,
    limit: int = 5,
) -> List[Dict[str, Any]]:
    """
    Find the best times for a specific type of event.

    Args:
        person_id: The user's ID
        duration_minutes: How long the event needs
        event_type: Type of event ('meeting', 'social', 'focus')
        start_date: Search from this date
        end_date: Search until this date
        limit: Maximum options to return

    Returns:
        List of suggested times with scores and reasoning
    """
    windows = await get_availability_windows(
        person_id,
        start_date,
        end_date,
        min_quality=WindowQuality.SUBOPTIMAL,
        event_type=event_type,
    )

    # Find windows long enough
    duration = timedelta(minutes=duration_minutes)
    suitable: List[Dict[str, Any]] = []

    for window in windows:
        window_duration = window.end - window.start
        if window_duration >= duration:
            # Score based on quality
            quality_scores = {
                WindowQuality.PREFERRED: 1.0,
                WindowQuality.AVAILABLE: 0.7,
                WindowQuality.SUBOPTIMAL: 0.4,
                WindowQuality.EMERGENCY: 0.1,
            }
            score = quality_scores.get(window.quality, 0.5)

            # Bonus for high energy when needed
            if event_type in ["meeting", "social"] and window.energy_level == "high":
                score += 0.1

            # Generate suggestion at the start of the window
            suitable.append({
                "start": window.start,
                "end": window.start + duration,
                "score": round(score, 2),
                "quality": window.quality.value,
                "energy_level": window.energy_level,
                "reasoning": window.reason or f"Available ({window.quality.value})",
            })

    # Sort by score (descending) and limit
    suitable.sort(key=lambda x: -x["score"])
    return suitable[:limit]


# =============================================================================
# Helper Functions
# =============================================================================

def _generate_time_slots(
    start: datetime,
    end: datetime,
    granularity_minutes: int,
) -> List[Tuple[datetime, datetime]]:
    """Generate time slots for the given range."""
    slots = []
    current = start
    delta = timedelta(minutes=granularity_minutes)

    while current < end:
        slot_end = min(current + delta, end)
        slots.append((current, slot_end))
        current = slot_end

    return slots


def _extract_busy_periods(events: List[Any]) -> List[Tuple[datetime, datetime]]:
    """Extract busy time periods from events."""
    return [(e.start_time, e.end_time) for e in events if e.status != "cancelled"]


def _is_period_busy(
    start: datetime,
    end: datetime,
    busy_periods: List[Tuple[datetime, datetime]],
) -> bool:
    """Check if a time period overlaps with any busy period."""
    for busy_start, busy_end in busy_periods:
        if start < busy_end and end > busy_start:
            return True
    return False


def _compute_slot_quality(
    slot_start: datetime,
    slot_end: datetime,
    preferences: Dict[str, Any],
    rhythm_state: Dict[str, Any],
    operating_system: Dict[str, Any],
) -> Tuple[WindowQuality, str, str]:
    """
    Compute quality rating for a time slot.

    Returns:
        Tuple of (quality, reason, energy_level)
    """
    hour = slot_start.hour
    day_of_week = slot_start.weekday()
    is_weekend = day_of_week >= 5

    # Default energy based on time of day
    if 9 <= hour <= 11:
        energy = "high"
        base_quality = WindowQuality.PREFERRED
        reason = "Morning peak hours"
    elif 14 <= hour <= 16:
        energy = "medium"
        base_quality = WindowQuality.AVAILABLE
        reason = "Afternoon"
    elif 7 <= hour <= 9 or 16 <= hour <= 19:
        energy = "medium"
        base_quality = WindowQuality.AVAILABLE
        reason = "Transition hours"
    elif 19 <= hour <= 21:
        energy = "low"
        base_quality = WindowQuality.SUBOPTIMAL
        reason = "Evening wind-down"
    elif hour < 7 or hour >= 21:
        energy = "low"
        base_quality = WindowQuality.EMERGENCY
        reason = "Outside normal hours"
    else:
        energy = "medium"
        base_quality = WindowQuality.AVAILABLE
        reason = "Standard availability"

    # Adjust based on preferences
    preferred_times = preferences.get("preferred_meeting_times", [])
    if preferred_times:
        for pref in preferred_times:
            pref_start = pref.get("start_hour", 0)
            pref_end = pref.get("end_hour", 24)
            if pref_start <= hour < pref_end:
                base_quality = WindowQuality.PREFERRED
                reason = "Your preferred time"
                break

    # Check blocked times in preferences
    blocked_times = preferences.get("blocked_times", [])
    for blocked in blocked_times:
        blocked_start = blocked.get("start_hour", 0)
        blocked_end = blocked.get("end_hour", 0)
        if blocked_start <= hour < blocked_end:
            base_quality = WindowQuality.EMERGENCY
            reason = "Usually blocked"
            break

    # Weekend adjustment
    if is_weekend:
        if base_quality == WindowQuality.PREFERRED:
            base_quality = WindowQuality.AVAILABLE
            reason = "Weekend (not your usual work time)"

    # Adjust based on operating system / dosha
    os_type = operating_system.get("type", "").lower()
    if "vata" in os_type:
        # Vata types do better with morning stability
        if 6 <= hour <= 10:
            energy = "high"
            if base_quality != WindowQuality.EMERGENCY:
                base_quality = WindowQuality.PREFERRED
                reason = "Morning grounding time (good for your type)"
    elif "pitta" in os_type:
        # Pitta types should avoid midday heat/intensity
        if 12 <= hour <= 14:
            energy = "low"
            if base_quality == WindowQuality.PREFERRED:
                base_quality = WindowQuality.AVAILABLE
                reason = "Midday (consider pacing for your type)"
    elif "kapha" in os_type:
        # Kapha types benefit from morning movement
        if 6 <= hour <= 9:
            energy = "high"
            if base_quality != WindowQuality.EMERGENCY:
                base_quality = WindowQuality.PREFERRED
                reason = "Early morning (energizing for your type)"

    return base_quality, reason, energy


def _determine_good_for(
    quality: WindowQuality,
    energy: str,
    operating_system: Dict[str, Any],
) -> List[str]:
    """Determine what activities a slot is good for."""
    good_for = []

    if quality in [WindowQuality.PREFERRED, WindowQuality.AVAILABLE]:
        if energy == "high":
            good_for.extend(["meetings", "social", "creative"])
        elif energy == "medium":
            good_for.extend(["meetings", "focus"])
        else:
            good_for.extend(["focus", "routine"])

    if quality == WindowQuality.SUBOPTIMAL:
        good_for.extend(["routine", "optional"])

    return good_for


# =============================================================================
# Data Loading
# =============================================================================

async def _load_scheduling_preferences(person_id: str) -> Dict[str, Any]:
    """Load scheduling preferences for a user."""
    row = await dbfetch(
        """
        SELECT scheduling_preferences
        FROM personal_model
        WHERE person_id = $1
        """,
        person_id,
        one=True,
    )

    if row and row.get("scheduling_preferences"):
        return row["scheduling_preferences"]

    # Default preferences
    return {
        "preferred_meeting_times": [
            {"start_hour": 9, "end_hour": 12},
            {"start_hour": 14, "end_hour": 17},
        ],
        "blocked_times": [],
    }


async def _load_rhythm_state(person_id: str) -> Dict[str, Any]:
    """Load rhythm state for a user."""
    row = await dbfetch(
        """
        SELECT rhythm_state
        FROM personal_model
        WHERE person_id = $1
        """,
        person_id,
        one=True,
    )

    return row.get("rhythm_state", {}) if row else {}


async def _load_operating_system(person_id: str) -> Dict[str, Any]:
    """Load operating system for a user."""
    row = await dbfetch(
        """
        SELECT operating_system
        FROM personal_model
        WHERE person_id = $1
        """,
        person_id,
        one=True,
    )

    return row.get("operating_system", {}) if row else {}


# =============================================================================
# Caching
# =============================================================================

async def _cache_availability(
    person_id: str,
    windows: List[AvailabilityWindow],
    start_date: datetime,
    end_date: datetime,
) -> None:
    """Cache computed availability."""
    windows_json = [
        {
            "start": w.start.isoformat(),
            "end": w.end.isoformat(),
            "quality": w.quality.value,
            "reason": w.reason,
            "energy_level": w.energy_level,
            "good_for": w.good_for,
        }
        for w in windows
    ]

    await execute(
        """
        INSERT INTO availability_cache (person_id, windows, valid_until, computed_at)
        VALUES ($1, $2, $3, NOW())
        ON CONFLICT (person_id) DO UPDATE SET
            windows = $2,
            valid_until = $3,
            computed_at = NOW(),
            invalidated_at = NULL
        """,
        person_id,
        windows_json,
        end_date,
    )


async def _get_cached_availability(
    person_id: str,
    start_date: datetime,
    end_date: datetime,
) -> Optional[List[AvailabilityWindow]]:
    """Get cached availability if still valid."""
    row = await dbfetch(
        """
        SELECT windows, valid_until
        FROM availability_cache
        WHERE person_id = $1
          AND valid_until >= $2
          AND invalidated_at IS NULL
        """,
        person_id,
        end_date,
        one=True,
    )

    if not row:
        return None

    windows_json = row.get("windows", [])
    return [
        AvailabilityWindow(
            start=datetime.fromisoformat(w["start"]),
            end=datetime.fromisoformat(w["end"]),
            quality=WindowQuality(w["quality"]),
            reason=w.get("reason"),
            energy_level=w.get("energy_level"),
            good_for=w.get("good_for"),
        )
        for w in windows_json
    ]


__all__ = [
    "WindowQuality",
    "AvailabilityWindow",
    "AvailabilityRequest",
    "compute_availability",
    "get_availability_windows",
    "is_time_slot_available",
    "find_best_times",
]
