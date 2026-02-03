"""
Scheduling Service
------------------
Manages scheduling preferences and availability computation.

This service provides:
- Scheduling preference management
- Availability computation
- Energy-aware scheduling recommendations
"""

from sakhi.apps.api.services.scheduling.preferences import (
    get_scheduling_preferences,
    update_scheduling_preferences,
    update_time_preferences,
    update_location_preferences,
    update_dining_preferences,
    is_preferred_time,
)

__all__ = [
    "get_scheduling_preferences",
    "update_scheduling_preferences",
    "update_time_preferences",
    "update_location_preferences",
    "update_dining_preferences",
    "is_preferred_time",
]
