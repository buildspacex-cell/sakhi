"""
Scheduling Preferences Service
------------------------------
Manage user scheduling preferences.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from sakhi.apps.api.core.db import q, exec, dbfetchrow


async def get_scheduling_preferences(person_id: str) -> Dict[str, Any]:
    """
    Get scheduling preferences for a user.

    Creates default preferences if none exist.
    """
    row = await dbfetchrow(
        """
        SELECT * FROM scheduling_preferences WHERE person_id = $1
        """,
        person_id,
    )

    if row:
        return row

    # Create default preferences
    await exec(
        """
        INSERT INTO scheduling_preferences (person_id)
        VALUES ($1)
        ON CONFLICT (person_id) DO NOTHING
        """,
        person_id,
    )

    return await dbfetchrow(
        """
        SELECT * FROM scheduling_preferences WHERE person_id = $1
        """,
        person_id,
    )


async def update_scheduling_preferences(
    person_id: str,
    preferred_times: Optional[Dict[str, Any]] = None,
    avoid_times: Optional[Dict[str, Any]] = None,
    buffer_minutes: Optional[int] = None,
    max_events_per_day: Optional[int] = None,
    preferred_durations: Optional[Dict[str, int]] = None,
    location_preferences: Optional[Dict[str, Any]] = None,
    dining_preferences: Optional[Dict[str, Any]] = None,
    energy_preferences: Optional[Dict[str, Any]] = None,
    communication_preferences: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Update scheduling preferences.

    Only provided fields are updated; others are merged with existing.
    """
    # Ensure record exists
    await exec(
        """
        INSERT INTO scheduling_preferences (person_id)
        VALUES ($1)
        ON CONFLICT (person_id) DO NOTHING
        """,
        person_id,
    )

    # Build update statement dynamically
    updates = []
    params = [person_id]
    param_idx = 2

    if preferred_times is not None:
        updates.append(f"preferred_times = preferred_times || ${param_idx}::jsonb")
        params.append(json.dumps(preferred_times))
        param_idx += 1

    if avoid_times is not None:
        updates.append(f"avoid_times = avoid_times || ${param_idx}::jsonb")
        params.append(json.dumps(avoid_times))
        param_idx += 1

    if buffer_minutes is not None:
        updates.append(f"buffer_minutes = ${param_idx}")
        params.append(buffer_minutes)
        param_idx += 1

    if max_events_per_day is not None:
        updates.append(f"max_events_per_day = ${param_idx}")
        params.append(max_events_per_day)
        param_idx += 1

    if preferred_durations is not None:
        updates.append(f"preferred_durations = preferred_durations || ${param_idx}::jsonb")
        params.append(json.dumps(preferred_durations))
        param_idx += 1

    if location_preferences is not None:
        updates.append(f"location_preferences = location_preferences || ${param_idx}::jsonb")
        params.append(json.dumps(location_preferences))
        param_idx += 1

    if dining_preferences is not None:
        updates.append(f"dining_preferences = dining_preferences || ${param_idx}::jsonb")
        params.append(json.dumps(dining_preferences))
        param_idx += 1

    if energy_preferences is not None:
        updates.append(f"energy_preferences = energy_preferences || ${param_idx}::jsonb")
        params.append(json.dumps(energy_preferences))
        param_idx += 1

    if communication_preferences is not None:
        updates.append(f"communication_preferences = communication_preferences || ${param_idx}::jsonb")
        params.append(json.dumps(communication_preferences))
        param_idx += 1

    if updates:
        updates.append("updated_at = now()")
        sql = f"""
            UPDATE scheduling_preferences
            SET {', '.join(updates)}
            WHERE person_id = $1
            RETURNING *
        """
        return await dbfetchrow(sql, *params)

    return await get_scheduling_preferences(person_id)


async def update_time_preferences(
    person_id: str,
    preferred: Optional[Dict[str, List[str]]] = None,
    avoid: Optional[Dict[str, List[str]]] = None,
) -> Dict[str, Any]:
    """
    Convenience method to update time preferences specifically.

    Args:
        person_id: User ID
        preferred: Dict like {"weekday": ["evening"], "weekend": ["afternoon"]}
        avoid: Dict like {"always": ["early_morning"], "weekday": ["lunch"]}
    """
    return await update_scheduling_preferences(
        person_id=person_id,
        preferred_times=preferred,
        avoid_times=avoid,
    )


async def update_location_preferences(
    person_id: str,
    default_area: Optional[str] = None,
    max_travel_minutes: Optional[int] = None,
    preferred_spots: Optional[List[Dict[str, Any]]] = None,
    avoid_areas: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Update location preferences.
    """
    location = {}
    if default_area:
        location["default_area"] = default_area
    if max_travel_minutes:
        location["max_travel_minutes"] = max_travel_minutes
    if preferred_spots:
        location["preferred_spots"] = preferred_spots
    if avoid_areas:
        location["avoid_areas"] = avoid_areas

    return await update_scheduling_preferences(
        person_id=person_id,
        location_preferences=location,
    )


async def update_dining_preferences(
    person_id: str,
    likes: Optional[List[str]] = None,
    dislikes: Optional[List[str]] = None,
    dietary: Optional[List[str]] = None,
    favorites: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Update dining preferences.
    """
    dining = {}
    if likes:
        dining["likes"] = likes
    if dislikes:
        dining["dislikes"] = dislikes
    if dietary:
        dining["dietary"] = dietary
    if favorites:
        dining["favorites"] = favorites

    return await update_scheduling_preferences(
        person_id=person_id,
        dining_preferences=dining,
    )


async def is_preferred_time(
    person_id: str,
    day_of_week: str,
    time_slot: str,
) -> bool:
    """
    Check if a specific day/time slot is preferred for the user.

    Args:
        person_id: User ID
        day_of_week: 'monday', 'tuesday', etc.
        time_slot: 'morning', 'afternoon', 'evening', etc.

    Returns:
        True if the time is preferred (or no preferences set)
    """
    row = await dbfetchrow(
        """
        SELECT is_preferred_time($1, $2, $3) as is_preferred
        """,
        person_id,
        day_of_week.lower(),
        time_slot.lower(),
    )

    return row["is_preferred"] if row else True


async def get_preferred_time_slots(
    person_id: str,
    day_of_week: str,
) -> List[str]:
    """
    Get all preferred time slots for a specific day.
    """
    prefs = await get_scheduling_preferences(person_id)

    all_slots = ["early_morning", "morning", "lunch", "afternoon", "evening", "night"]
    preferred = []

    for slot in all_slots:
        if await is_preferred_time(person_id, day_of_week, slot):
            preferred.append(slot)

    return preferred


async def get_dining_context(
    person_id: str,
) -> Dict[str, Any]:
    """
    Get dining preferences formatted for scheduling context.
    """
    prefs = await get_scheduling_preferences(person_id)
    dining = prefs.get("dining_preferences", {})

    if isinstance(dining, str):
        import json
        dining = json.loads(dining)

    return {
        "cuisine_likes": dining.get("likes", []),
        "cuisine_dislikes": dining.get("dislikes", []),
        "dietary_restrictions": dining.get("dietary", []),
        "favorite_restaurants": dining.get("favorites", []),
        "price_range": dining.get("price_range", "any"),
        "ambiance": dining.get("ambiance", []),
    }


async def get_scheduling_context_for_mesh(
    person_id: str,
) -> Dict[str, Any]:
    """
    Get scheduling context formatted for Sakhi-to-Sakhi coordination.

    This is what gets shared with another Sakhi during scheduling.
    Privacy-conscious: only shares necessary scheduling info.
    """
    prefs = await get_scheduling_preferences(person_id)

    return {
        "preferred_times": prefs.get("preferred_times", {}),
        "avoid_times": prefs.get("avoid_times", {}),
        "preferred_durations": prefs.get("preferred_durations", {}),
        "location_preferences": {
            "default_area": (prefs.get("location_preferences") or {}).get("default_area"),
            "max_travel_minutes": (prefs.get("location_preferences") or {}).get("max_travel_minutes"),
        },
        "dining_preferences": {
            "likes": (prefs.get("dining_preferences") or {}).get("likes", []),
            "dislikes": (prefs.get("dining_preferences") or {}).get("dislikes", []),
            "dietary": (prefs.get("dining_preferences") or {}).get("dietary", []),
        },
        "advance_notice_days": (prefs.get("communication_preferences") or {}).get("advance_notice", 1),
    }


__all__ = [
    "get_scheduling_preferences",
    "update_scheduling_preferences",
    "update_time_preferences",
    "update_location_preferences",
    "update_dining_preferences",
    "is_preferred_time",
    "get_preferred_time_slots",
    "get_dining_context",
    "get_scheduling_context_for_mesh",
]
