"""
Scheduling API Routes
---------------------
Endpoints for managing scheduling preferences.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

from sakhi.apps.api.services.scheduling.preferences import (
    get_scheduling_preferences,
    update_scheduling_preferences,
    update_time_preferences,
    update_location_preferences,
    update_dining_preferences,
    is_preferred_time,
    get_preferred_time_slots,
    get_dining_context,
    get_scheduling_context_for_mesh,
)

router = APIRouter(prefix="/scheduling", tags=["Scheduling"])


# =============================================================================
# Request Models
# =============================================================================

class TimePreferencesUpdate(BaseModel):
    """Update time preferences."""
    preferred: Optional[Dict[str, List[str]]] = Field(
        default=None,
        description="Preferred times: {'weekday': ['evening'], 'weekend': ['afternoon']}"
    )
    avoid: Optional[Dict[str, List[str]]] = Field(
        default=None,
        description="Times to avoid: {'always': ['early_morning']}"
    )


class LocationPreferencesUpdate(BaseModel):
    """Update location preferences."""
    default_area: Optional[str] = None
    max_travel_minutes: Optional[int] = None
    preferred_spots: Optional[List[Dict[str, Any]]] = None
    avoid_areas: Optional[List[str]] = None


class DiningPreferencesUpdate(BaseModel):
    """Update dining preferences."""
    likes: Optional[List[str]] = None
    dislikes: Optional[List[str]] = None
    dietary: Optional[List[str]] = None
    favorites: Optional[List[Dict[str, Any]]] = None


class FullPreferencesUpdate(BaseModel):
    """Full scheduling preferences update."""
    preferred_times: Optional[Dict[str, Any]] = None
    avoid_times: Optional[Dict[str, Any]] = None
    buffer_minutes: Optional[int] = None
    max_events_per_day: Optional[int] = None
    preferred_durations: Optional[Dict[str, int]] = None
    location_preferences: Optional[Dict[str, Any]] = None
    dining_preferences: Optional[Dict[str, Any]] = None
    energy_preferences: Optional[Dict[str, Any]] = None
    communication_preferences: Optional[Dict[str, Any]] = None


# =============================================================================
# Endpoints
# =============================================================================

@router.get("/{person_id}/preferences")
async def get_preferences(person_id: str) -> Dict[str, Any]:
    """Get all scheduling preferences for a user."""
    return await get_scheduling_preferences(person_id)


@router.put("/{person_id}/preferences")
async def update_preferences(
    person_id: str,
    data: FullPreferencesUpdate,
) -> Dict[str, Any]:
    """Update scheduling preferences."""
    return await update_scheduling_preferences(
        person_id=person_id,
        preferred_times=data.preferred_times,
        avoid_times=data.avoid_times,
        buffer_minutes=data.buffer_minutes,
        max_events_per_day=data.max_events_per_day,
        preferred_durations=data.preferred_durations,
        location_preferences=data.location_preferences,
        dining_preferences=data.dining_preferences,
        energy_preferences=data.energy_preferences,
        communication_preferences=data.communication_preferences,
    )


@router.put("/{person_id}/preferences/times")
async def update_times(
    person_id: str,
    data: TimePreferencesUpdate,
) -> Dict[str, Any]:
    """Update time preferences specifically."""
    return await update_time_preferences(
        person_id=person_id,
        preferred=data.preferred,
        avoid=data.avoid,
    )


@router.put("/{person_id}/preferences/location")
async def update_location(
    person_id: str,
    data: LocationPreferencesUpdate,
) -> Dict[str, Any]:
    """Update location preferences."""
    return await update_location_preferences(
        person_id=person_id,
        default_area=data.default_area,
        max_travel_minutes=data.max_travel_minutes,
        preferred_spots=data.preferred_spots,
        avoid_areas=data.avoid_areas,
    )


@router.put("/{person_id}/preferences/dining")
async def update_dining(
    person_id: str,
    data: DiningPreferencesUpdate,
) -> Dict[str, Any]:
    """Update dining preferences."""
    return await update_dining_preferences(
        person_id=person_id,
        likes=data.likes,
        dislikes=data.dislikes,
        dietary=data.dietary,
        favorites=data.favorites,
    )


@router.get("/{person_id}/preferred-times/{day_of_week}")
async def get_preferred_times(
    person_id: str,
    day_of_week: str,
) -> Dict[str, Any]:
    """Get preferred time slots for a specific day."""
    slots = await get_preferred_time_slots(person_id, day_of_week)

    return {
        "person_id": person_id,
        "day_of_week": day_of_week,
        "preferred_slots": slots,
    }


@router.get("/{person_id}/check-time/{day_of_week}/{time_slot}")
async def check_time_preference(
    person_id: str,
    day_of_week: str,
    time_slot: str,
) -> Dict[str, Any]:
    """Check if a specific time is preferred."""
    is_preferred = await is_preferred_time(person_id, day_of_week, time_slot)

    return {
        "person_id": person_id,
        "day_of_week": day_of_week,
        "time_slot": time_slot,
        "is_preferred": is_preferred,
    }


@router.get("/{person_id}/dining-context")
async def get_dining(person_id: str) -> Dict[str, Any]:
    """Get dining context for scheduling."""
    return await get_dining_context(person_id)


@router.get("/{person_id}/mesh-context")
async def get_mesh_context(person_id: str) -> Dict[str, Any]:
    """
    Get scheduling context for Sakhi-to-Sakhi coordination.

    This is what gets shared with another Sakhi during scheduling.
    """
    return await get_scheduling_context_for_mesh(person_id)


__all__ = ["router"]
