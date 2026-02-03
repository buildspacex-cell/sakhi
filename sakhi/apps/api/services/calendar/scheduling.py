"""
Conversational Scheduling Service
---------------------------------
Natural language scheduling that understands:
- "Schedule dinner with Alex this week"
- "Block Thursday evening"
- "What does my week look like?"
- "Move my Friday meeting to next week"

Components:
1. Intent Recognition - Detect scheduling intents
2. Slot Filling - Extract who, when, what, where
3. Availability Check - Find suitable times
4. Confirmation Flow - Present options, confirm
5. Calendar Update - Create/modify events
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum

from pydantic import BaseModel

from sakhi.apps.api.core.llm import call_llm
from sakhi.apps.api.core.db import q as dbfetch
from sakhi.apps.api.services.calendar.events import (
    create_event,
    get_events_for_week,
    get_upcoming_events,
    get_week_summary,
    CreateEventRequest,
)
from sakhi.apps.api.services.calendar.availability import (
    find_best_times,
    is_time_slot_available,
)

LOGGER = logging.getLogger(__name__)


# =============================================================================
# Models
# =============================================================================

class SchedulingIntent(str, Enum):
    """Types of scheduling intents."""
    CREATE = "create"           # Schedule something new
    BLOCK = "block"            # Block time
    QUERY = "query"            # What's my schedule?
    MODIFY = "modify"          # Move/reschedule
    CANCEL = "cancel"          # Cancel event
    FIND_TIME = "find_time"    # When am I free?


class ParsedSchedulingRequest(BaseModel):
    """Parsed scheduling request from natural language."""
    intent: SchedulingIntent
    raw_text: str

    # What
    event_type: Optional[str] = None  # 'dinner', 'meeting', 'coffee', etc.
    title: Optional[str] = None
    description: Optional[str] = None

    # Who
    participants: List[str] = []  # Names or IDs of people
    participant_ids: List[str] = []  # Resolved person IDs

    # When
    timeframe: Optional[str] = None  # 'this week', 'tomorrow', 'next Tuesday'
    specific_date: Optional[datetime] = None
    specific_time: Optional[str] = None
    duration_minutes: int = 60

    # Where
    location: Optional[str] = None
    location_preference: Optional[str] = None  # 'their place', 'somewhere new'

    # Confidence
    confidence: float = 0.0
    missing_slots: List[str] = []


class SchedulingResponse(BaseModel):
    """Response from scheduling service."""
    status: str  # 'needs_info', 'options_ready', 'confirmed', 'failed'
    message: str
    options: Optional[List[Dict[str, Any]]] = None
    created_event: Optional[Dict[str, Any]] = None
    missing_slots: Optional[List[str]] = None
    follow_up_question: Optional[str] = None


# =============================================================================
# Intent Recognition
# =============================================================================

INTENT_PATTERNS = {
    SchedulingIntent.CREATE: [
        r"schedule\s+(?:a\s+)?(.+?)\s+with",
        r"set up\s+(?:a\s+)?(.+?)\s+with",
        r"plan\s+(?:a\s+)?(.+?)\s+with",
        r"let'?s\s+(?:have\s+)?(.+?)\s+with",
        r"i want to\s+(?:have\s+)?(.+?)\s+with",
        r"can you schedule",
        r"book\s+(?:a\s+)?",
    ],
    SchedulingIntent.BLOCK: [
        r"block\s+(?:off\s+)?(.+)",
        r"reserve\s+(.+)",
        r"keep\s+(.+?)\s+free",
        r"don'?t schedule anything",
        r"i need time",
    ],
    SchedulingIntent.QUERY: [
        r"what(?:'s| is| does) my (?:week|schedule|calendar)",
        r"what do i have",
        r"am i free",
        r"do i have anything",
        r"what'?s (?:on|happening)",
        r"show (?:me )?my",
    ],
    SchedulingIntent.MODIFY: [
        r"move\s+(?:my\s+)?(.+)",
        r"reschedule\s+(?:my\s+)?(.+)",
        r"change\s+(?:the\s+)?(.+)",
        r"push\s+(?:back\s+)?(.+)",
    ],
    SchedulingIntent.CANCEL: [
        r"cancel\s+(?:my\s+)?(.+)",
        r"delete\s+(?:my\s+)?(.+)",
        r"remove\s+(?:my\s+)?(.+)",
        r"i can'?t make",
    ],
    SchedulingIntent.FIND_TIME: [
        r"when (?:am i|are we) free",
        r"find (?:a )?time",
        r"what times? (?:work|are good)",
        r"when can (?:i|we)",
    ],
}


def detect_scheduling_intent(text: str) -> Optional[Tuple[SchedulingIntent, float]]:
    """
    Detect if text contains a scheduling intent.

    Returns:
        Tuple of (intent, confidence) or None if no scheduling intent
    """
    text_lower = text.lower().strip()

    for intent, patterns in INTENT_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, text_lower):
                # Higher confidence for more specific patterns
                confidence = 0.8 if len(pattern) > 20 else 0.6
                return intent, confidence

    return None


# =============================================================================
# Slot Filling
# =============================================================================

EVENT_TYPE_KEYWORDS = {
    "dinner": ["dinner", "eat", "restaurant", "food"],
    "coffee": ["coffee", "cafe", "chat"],
    "meeting": ["meeting", "meet", "discuss", "talk about"],
    "call": ["call", "phone", "video"],
    "lunch": ["lunch", "midday"],
    "drinks": ["drinks", "bar", "happy hour"],
    "workout": ["workout", "gym", "exercise", "run"],
}

TIMEFRAME_PATTERNS = {
    "today": r"\btoday\b",
    "tomorrow": r"\btomorrow\b",
    "this_week": r"\bthis week\b",
    "next_week": r"\bnext week\b",
    "this_weekend": r"\bthis weekend\b",
    "monday": r"\bmonday\b",
    "tuesday": r"\btuesday\b",
    "wednesday": r"\bwednesday\b",
    "thursday": r"\bthursday\b",
    "friday": r"\bfriday\b",
    "saturday": r"\bsaturday\b",
    "sunday": r"\bsunday\b",
}


async def parse_scheduling_request(
    person_id: str,
    text: str,
    intent: SchedulingIntent,
) -> ParsedSchedulingRequest:
    """
    Parse natural language into structured scheduling request.

    Uses pattern matching for common cases, falls back to LLM for complex ones.
    """
    text_lower = text.lower()
    result = ParsedSchedulingRequest(
        intent=intent,
        raw_text=text,
        confidence=0.5,
    )

    # Extract event type
    for event_type, keywords in EVENT_TYPE_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            result.event_type = event_type
            result.confidence += 0.1
            break

    # Extract timeframe
    for timeframe, pattern in TIMEFRAME_PATTERNS.items():
        if re.search(pattern, text_lower):
            result.timeframe = timeframe
            result.specific_date = _resolve_timeframe(timeframe)
            result.confidence += 0.1
            break

    # Extract participants (names after "with")
    with_match = re.search(r"with\s+([A-Z][a-z]+(?:\s+and\s+[A-Z][a-z]+)*)", text)
    if with_match:
        names = re.split(r"\s+and\s+", with_match.group(1))
        result.participants = [n.strip() for n in names]
        result.confidence += 0.15

    # Resolve participant IDs from relationships
    if result.participants:
        result.participant_ids = await _resolve_participants(
            person_id, result.participants
        )

    # Extract duration hints
    duration_match = re.search(r"(\d+)\s*(?:hour|hr|minute|min)", text_lower)
    if duration_match:
        num = int(duration_match.group(1))
        if "hour" in text_lower or "hr" in text_lower:
            result.duration_minutes = num * 60
        else:
            result.duration_minutes = num

    # Extract location
    location_patterns = [
        r"at\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)",
        r"(?:at|in)\s+(?:the\s+)?(\w+\s*\w*)",
    ]
    for pattern in location_patterns:
        loc_match = re.search(pattern, text)
        if loc_match:
            result.location = loc_match.group(1)
            break

    # Determine missing slots
    result.missing_slots = _identify_missing_slots(result)

    # Generate title if not set
    if not result.title and result.event_type:
        if result.participants:
            result.title = f"{result.event_type.title()} with {', '.join(result.participants)}"
        else:
            result.title = result.event_type.title()

    return result


def _resolve_timeframe(timeframe: str) -> Optional[datetime]:
    """Convert timeframe string to approximate datetime."""
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)

    if timeframe == "today":
        return today
    elif timeframe == "tomorrow":
        return today + timedelta(days=1)
    elif timeframe == "this_week":
        return today  # Start from today
    elif timeframe == "next_week":
        days_until_monday = (7 - today.weekday()) % 7 or 7
        return today + timedelta(days=days_until_monday)
    elif timeframe == "this_weekend":
        days_until_saturday = (5 - today.weekday()) % 7
        return today + timedelta(days=days_until_saturday)
    elif timeframe in ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]:
        day_map = {
            "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
            "friday": 4, "saturday": 5, "sunday": 6
        }
        target_day = day_map[timeframe]
        days_ahead = (target_day - today.weekday()) % 7
        if days_ahead == 0:
            days_ahead = 7  # Next occurrence
        return today + timedelta(days=days_ahead)

    return None


async def _resolve_participants(
    person_id: str,
    names: List[str],
) -> List[str]:
    """Resolve participant names to relationship IDs."""
    resolved = []

    for name in names:
        # Check relationships table
        row = await dbfetch(
            """
            SELECT id FROM relationships
            WHERE person_id = $1
              AND LOWER(name) LIKE LOWER($2)
            LIMIT 1
            """,
            person_id,
            f"%{name}%",
            one=True,
        )

        if row:
            resolved.append(str(row["id"]))

    return resolved


def _identify_missing_slots(request: ParsedSchedulingRequest) -> List[str]:
    """Identify which required information is missing."""
    missing = []

    if request.intent == SchedulingIntent.CREATE:
        if not request.event_type:
            missing.append("event_type")
        if not request.participants and request.event_type in ["dinner", "coffee", "meeting", "call"]:
            missing.append("participants")
        if not request.timeframe and not request.specific_date:
            missing.append("when")

    elif request.intent == SchedulingIntent.BLOCK:
        if not request.timeframe and not request.specific_date:
            missing.append("when")

    return missing


# =============================================================================
# Scheduling Actions
# =============================================================================

async def process_scheduling_request(
    person_id: str,
    text: str,
) -> SchedulingResponse:
    """
    Process a natural language scheduling request end-to-end.

    Returns response with either:
    - Follow-up question (if info missing)
    - Options to choose from
    - Confirmation of created event
    """
    # Detect intent
    intent_result = detect_scheduling_intent(text)
    if not intent_result:
        return SchedulingResponse(
            status="failed",
            message="I'm not sure what you'd like to schedule. Could you be more specific?",
        )

    intent, confidence = intent_result

    # Handle query intents immediately
    if intent == SchedulingIntent.QUERY:
        return await _handle_query(person_id, text)

    if intent == SchedulingIntent.FIND_TIME:
        return await _handle_find_time(person_id, text)

    # Parse the request
    parsed = await parse_scheduling_request(person_id, text, intent)

    # Check for missing information
    if parsed.missing_slots:
        return _generate_follow_up(parsed)

    # Handle by intent type
    if intent == SchedulingIntent.CREATE:
        return await _handle_create(person_id, parsed)
    elif intent == SchedulingIntent.BLOCK:
        return await _handle_block(person_id, parsed)
    elif intent == SchedulingIntent.MODIFY:
        return await _handle_modify(person_id, parsed)
    elif intent == SchedulingIntent.CANCEL:
        return await _handle_cancel(person_id, parsed)

    return SchedulingResponse(
        status="failed",
        message="I couldn't process that scheduling request.",
    )


async def _handle_query(person_id: str, text: str) -> SchedulingResponse:
    """Handle schedule query requests."""
    text_lower = text.lower()

    if "week" in text_lower:
        events = await get_events_for_week(person_id)
        summary = await get_week_summary(person_id)

        if not events:
            return SchedulingResponse(
                status="confirmed",
                message="Your week is clear! No events scheduled yet.",
            )

        event_summaries = [
            f"• {e.title} on {e.start_time.strftime('%A at %I:%M %p')}"
            for e in events[:5]
        ]

        message = f"Here's your week:\n" + "\n".join(event_summaries)
        if len(events) > 5:
            message += f"\n...and {len(events) - 5} more events."

        return SchedulingResponse(
            status="confirmed",
            message=message,
            options=[{"events": [e.model_dump() for e in events]}],
        )

    else:
        # Today or upcoming
        events = await get_upcoming_events(person_id, limit=5)

        if not events:
            return SchedulingResponse(
                status="confirmed",
                message="Nothing coming up! Your schedule is free.",
            )

        event_summaries = [
            f"• {e.title} - {e.start_time.strftime('%A, %b %d at %I:%M %p')}"
            for e in events
        ]

        return SchedulingResponse(
            status="confirmed",
            message="Upcoming:\n" + "\n".join(event_summaries),
        )


async def _handle_find_time(person_id: str, text: str) -> SchedulingResponse:
    """Handle find time requests."""
    # Default to next 7 days
    start = datetime.now()
    end = start + timedelta(days=7)

    # Detect event type from context
    event_type = "meeting"
    for etype, keywords in EVENT_TYPE_KEYWORDS.items():
        if any(kw in text.lower() for kw in keywords):
            event_type = etype
            break

    suggestions = await find_best_times(
        person_id,
        duration_minutes=60,
        event_type=event_type,
        start_date=start,
        end_date=end,
        limit=5,
    )

    if not suggestions:
        return SchedulingResponse(
            status="confirmed",
            message="I couldn't find any good times in the next week. Would you like to look further out?",
        )

    time_summaries = [
        f"• {s['start'].strftime('%A %I:%M %p')} ({s['quality']})"
        for s in suggestions
    ]

    return SchedulingResponse(
        status="options_ready",
        message=f"Here are some good times for a {event_type}:\n" + "\n".join(time_summaries),
        options=suggestions,
    )


async def _handle_create(
    person_id: str,
    parsed: ParsedSchedulingRequest,
) -> SchedulingResponse:
    """Handle event creation."""
    # Find best times
    start_date = parsed.specific_date or datetime.now()
    end_date = start_date + timedelta(days=7)

    suggestions = await find_best_times(
        person_id,
        duration_minutes=parsed.duration_minutes,
        event_type=parsed.event_type or "meeting",
        start_date=start_date,
        end_date=end_date,
        limit=3,
    )

    if not suggestions:
        return SchedulingResponse(
            status="failed",
            message=f"I couldn't find any good times for {parsed.title}. Would you like to try a different timeframe?",
        )

    # Return options for user to choose
    time_options = [
        {
            "option_number": i + 1,
            "start": s["start"].isoformat(),
            "end": s["end"].isoformat(),
            "display": s["start"].strftime("%A, %B %d at %I:%M %p"),
            "quality": s["quality"],
            "reasoning": s["reasoning"],
        }
        for i, s in enumerate(suggestions)
    ]

    participants_str = (
        f" with {', '.join(parsed.participants)}" if parsed.participants else ""
    )

    return SchedulingResponse(
        status="options_ready",
        message=f"Here are some options for {parsed.title}{participants_str}:",
        options=time_options,
        follow_up_question="Which time works best? (Reply with the number)",
    )


async def _handle_block(
    person_id: str,
    parsed: ParsedSchedulingRequest,
) -> SchedulingResponse:
    """Handle blocking time."""
    if not parsed.specific_date:
        return SchedulingResponse(
            status="needs_info",
            message="When would you like to block time?",
            missing_slots=["when"],
        )

    # Default to blocking 2 hours in the evening
    start_time = parsed.specific_date.replace(hour=18, minute=0)
    end_time = start_time + timedelta(hours=2)

    request = CreateEventRequest(
        title=parsed.title or "Blocked Time",
        start_time=start_time,
        end_time=end_time,
        event_type="blocked",
        created_by="user",
    )

    event = await create_event(person_id, request)

    return SchedulingResponse(
        status="confirmed",
        message=f"Done! I've blocked {start_time.strftime('%A, %B %d')} from {start_time.strftime('%I:%M %p')} to {end_time.strftime('%I:%M %p')}.",
        created_event=event.model_dump(),
    )


async def _handle_modify(
    person_id: str,
    parsed: ParsedSchedulingRequest,
) -> SchedulingResponse:
    """Handle event modification."""
    # This would need to find the event first
    return SchedulingResponse(
        status="needs_info",
        message="Which event would you like to modify? I'll need a bit more detail.",
    )


async def _handle_cancel(
    person_id: str,
    parsed: ParsedSchedulingRequest,
) -> SchedulingResponse:
    """Handle event cancellation."""
    return SchedulingResponse(
        status="needs_info",
        message="Which event would you like to cancel?",
    )


def _generate_follow_up(parsed: ParsedSchedulingRequest) -> SchedulingResponse:
    """Generate follow-up question for missing slots."""
    if "participants" in parsed.missing_slots:
        return SchedulingResponse(
            status="needs_info",
            message=f"Who would you like to {parsed.event_type or 'meet'} with?",
            missing_slots=parsed.missing_slots,
        )

    if "when" in parsed.missing_slots:
        return SchedulingResponse(
            status="needs_info",
            message="When were you thinking? This week, next week, or a specific day?",
            missing_slots=parsed.missing_slots,
        )

    if "event_type" in parsed.missing_slots:
        return SchedulingResponse(
            status="needs_info",
            message="What kind of event is this? Dinner, coffee, meeting, or something else?",
            missing_slots=parsed.missing_slots,
        )

    return SchedulingResponse(
        status="needs_info",
        message="I need a bit more information. Could you tell me more about what you'd like to schedule?",
        missing_slots=parsed.missing_slots,
    )


# =============================================================================
# Confirm and Create
# =============================================================================

async def confirm_scheduling_option(
    person_id: str,
    option: Dict[str, Any],
    parsed: ParsedSchedulingRequest,
) -> SchedulingResponse:
    """
    Confirm and create an event from a selected option.

    Called after user selects from options.
    """
    start_time = datetime.fromisoformat(option["start"])
    end_time = datetime.fromisoformat(option["end"])

    # Check availability one more time
    is_available, reason = await is_time_slot_available(person_id, start_time, end_time)
    if not is_available:
        return SchedulingResponse(
            status="failed",
            message=f"That time is no longer available: {reason}. Would you like to try another time?",
        )

    # Create the event
    request = CreateEventRequest(
        title=parsed.title or f"{parsed.event_type.title() if parsed.event_type else 'Event'}",
        description=parsed.description,
        start_time=start_time,
        end_time=end_time,
        location=parsed.location,
        event_type=parsed.event_type or "personal",
        related_person_ids=parsed.participant_ids or None,
        conversation_context=parsed.raw_text,
        created_by="sakhi_suggestion",
    )

    event = await create_event(person_id, request)

    participants_str = f" with {', '.join(parsed.participants)}" if parsed.participants else ""

    return SchedulingResponse(
        status="confirmed",
        message=f"Done! {parsed.title}{participants_str} is scheduled for {start_time.strftime('%A, %B %d at %I:%M %p')}.",
        created_event=event.model_dump(),
    )


# =============================================================================
# Pending Request Management
# =============================================================================

CONFIRMATION_PATTERNS = [
    r"^yes\b",
    r"^yeah\b",
    r"^yep\b",
    r"^confirm\b",
    r"^do it\b",
    r"^book it\b",
    r"^sounds good\b",
    r"^let'?s do it\b",
    r"^that works\b",
    r"^perfect\b",
    r"^go ahead\b",
    r"^please\s+(?:do|book|schedule)",
    r"^(?:the\s+)?(?:first|second|third|1st|2nd|3rd|option\s*)?(?:one|1|2|3)\b",
]


def detect_confirmation(text: str) -> Optional[Tuple[bool, Optional[int]]]:
    """
    Detect if user is confirming a pending scheduling request.

    Returns:
        Tuple of (is_confirmation, option_number) where option_number is
        the selected option (1, 2, 3) or None if just a general yes.
    """
    text_lower = text.lower().strip()

    # Check for confirmation patterns
    for pattern in CONFIRMATION_PATTERNS:
        if re.search(pattern, text_lower):
            # Check for option number
            option_match = re.search(r"(?:option\s*)?(\d+)", text_lower)
            if option_match:
                return True, int(option_match.group(1))

            # Check for ordinal
            ordinal_map = {"first": 1, "second": 2, "third": 3, "1st": 1, "2nd": 2, "3rd": 3}
            for word, num in ordinal_map.items():
                if word in text_lower:
                    return True, num

            return True, 1  # Default to first option

    return None


async def save_pending_request(
    person_id: str,
    original_request: str,
    parsed: ParsedSchedulingRequest,
    proposed_times: List[Dict[str, Any]],
) -> str:
    """
    Save a pending scheduling request to the database.

    Returns the request ID.
    """
    from sakhi.apps.api.core.db import exec as dbexec
    import json

    parsed_intent = {
        "intent": parsed.intent.value,
        "event_type": parsed.event_type,
        "title": parsed.title,
        "participants": parsed.participants,
        "participant_ids": parsed.participant_ids,
        "timeframe": parsed.timeframe,
        "duration_minutes": parsed.duration_minutes,
        "location": parsed.location,
    }

    # Serialize proposed times
    proposed_times_json = [
        {
            "start": t.get("start").isoformat() if hasattr(t.get("start"), "isoformat") else t.get("start"),
            "end": t.get("end").isoformat() if hasattr(t.get("end"), "isoformat") else t.get("end"),
            "quality": t.get("quality"),
            "reasoning": t.get("reasoning", t.get("quality_reason", "")),
        }
        for t in proposed_times
    ]

    row = await dbfetch(
        """
        INSERT INTO scheduling_requests (
            person_id, original_request, parsed_intent,
            related_person_ids, proposed_times, status
        )
        VALUES ($1, $2, $3::jsonb, $4, $5::jsonb, 'options_presented')
        RETURNING id
        """,
        person_id,
        original_request,
        json.dumps(parsed_intent),
        parsed.participant_ids or [],
        json.dumps(proposed_times_json),
        one=True,
    )

    return str(row["id"]) if row else None


async def get_pending_request(person_id: str) -> Optional[Dict[str, Any]]:
    """
    Get the most recent pending scheduling request for a user.

    Only returns requests that are still pending (not confirmed/cancelled)
    and were created within the last hour.
    """
    row = await dbfetch(
        """
        SELECT id, original_request, parsed_intent, proposed_times,
               related_person_ids, created_at
        FROM scheduling_requests
        WHERE person_id = $1
          AND status = 'options_presented'
          AND created_at > NOW() - INTERVAL '1 hour'
        ORDER BY created_at DESC
        LIMIT 1
        """,
        person_id,
        one=True,
    )

    return dict(row) if row else None


async def execute_pending_confirmation(
    person_id: str,
    request_id: str,
    option_number: int = 1,
) -> SchedulingResponse:
    """
    Execute a pending scheduling confirmation.

    Creates the calendar event and updates the request status.
    """
    from sakhi.apps.api.core.db import exec as dbexec
    import json

    # Get the pending request
    row = await dbfetch(
        """
        SELECT id, original_request, parsed_intent, proposed_times
        FROM scheduling_requests
        WHERE id = $1 AND person_id = $2
        """,
        request_id,
        person_id,
        one=True,
    )

    if not row:
        return SchedulingResponse(
            status="failed",
            message="I couldn't find that scheduling request. Could you tell me again what you'd like to schedule?",
        )

    parsed_intent = row["parsed_intent"]
    proposed_times = row["proposed_times"]

    if isinstance(parsed_intent, str):
        parsed_intent = json.loads(parsed_intent)
    if isinstance(proposed_times, str):
        proposed_times = json.loads(proposed_times)

    # Get the selected option (1-indexed)
    if option_number < 1 or option_number > len(proposed_times):
        option_number = 1

    selected = proposed_times[option_number - 1]

    # Parse times
    start_time = datetime.fromisoformat(selected["start"].replace("Z", "+00:00"))
    end_time = datetime.fromisoformat(selected["end"].replace("Z", "+00:00"))

    # Check availability one more time
    is_available, reason = await is_time_slot_available(person_id, start_time, end_time)
    if not is_available:
        return SchedulingResponse(
            status="failed",
            message=f"That time is no longer available: {reason}. Would you like to try another time?",
        )

    # Build title
    title = parsed_intent.get("title")
    if not title:
        event_type = parsed_intent.get("event_type", "Event")
        participants = parsed_intent.get("participants", [])
        if participants:
            title = f"{event_type.title()} with {', '.join(participants)}"
        else:
            title = event_type.title()

    # Create the event
    request = CreateEventRequest(
        title=title,
        start_time=start_time,
        end_time=end_time,
        location=parsed_intent.get("location"),
        event_type=parsed_intent.get("event_type") or "personal",
        related_person_ids=parsed_intent.get("participant_ids") or None,
        conversation_context=row["original_request"],
        created_by="sakhi_suggestion",
    )

    event = await create_event(person_id, request)

    # Update the request status
    await dbexec(
        """
        UPDATE scheduling_requests
        SET status = 'confirmed',
            selected_option = $3,
            resulting_event_id = $4,
            resolved_at = NOW()
        WHERE id = $1 AND person_id = $2
        """,
        request_id,
        person_id,
        option_number,
        event.id,
    )

    participants = parsed_intent.get("participants", [])
    participants_str = f" with {', '.join(participants)}" if participants else ""

    return SchedulingResponse(
        status="confirmed",
        message=f"Done! {title}{participants_str} is now on your calendar for {start_time.strftime('%A, %B %d at %I:%M %p')}.",
        created_event=event.model_dump(),
    )


__all__ = [
    "SchedulingIntent",
    "ParsedSchedulingRequest",
    "SchedulingResponse",
    "detect_scheduling_intent",
    "parse_scheduling_request",
    "process_scheduling_request",
    "confirm_scheduling_option",
    # Pending request management
    "detect_confirmation",
    "save_pending_request",
    "get_pending_request",
    "execute_pending_confirmation",
]
