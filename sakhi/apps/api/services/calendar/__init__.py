"""
Sakhi Calendar Service
----------------------
A calendar that understands you - not just when you're free,
but when you're at your best for different types of activities.

Components:
- events.py: Event CRUD operations
- availability.py: Compute availability windows
- scheduling.py: Conversational scheduling interface
"""

from sakhi.apps.api.services.calendar.events import (
    create_event,
    get_event,
    update_event,
    delete_event,
    get_events_in_range,
    get_events_for_day,
    get_week_summary,
    get_upcoming_events,
    CalendarEvent,
    CreateEventRequest,
    UpdateEventRequest,
)
from sakhi.apps.api.services.calendar.availability import (
    compute_availability,
    get_availability_windows,
    is_time_slot_available,
    find_best_times,
    AvailabilityWindow,
    WindowQuality,
)
from sakhi.apps.api.services.calendar.scheduling import (
    detect_scheduling_intent,
    parse_scheduling_request,
    process_scheduling_request,
    confirm_scheduling_option,
    detect_confirmation,
    save_pending_request,
    get_pending_request,
    execute_pending_confirmation,
    SchedulingIntent,
    ParsedSchedulingRequest,
    SchedulingResponse,
)

__all__ = [
    # Events
    "create_event",
    "get_event",
    "update_event",
    "delete_event",
    "get_events_in_range",
    "get_events_for_day",
    "get_week_summary",
    "get_upcoming_events",
    "CalendarEvent",
    "CreateEventRequest",
    "UpdateEventRequest",
    # Availability
    "compute_availability",
    "get_availability_windows",
    "is_time_slot_available",
    "find_best_times",
    "AvailabilityWindow",
    "WindowQuality",
    # Scheduling
    "detect_scheduling_intent",
    "parse_scheduling_request",
    "process_scheduling_request",
    "confirm_scheduling_option",
    "detect_confirmation",
    "save_pending_request",
    "get_pending_request",
    "execute_pending_confirmation",
    "SchedulingIntent",
    "ParsedSchedulingRequest",
    "SchedulingResponse",
]
