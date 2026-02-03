"""
Coordination Demo Orchestrator
------------------------------
Orchestrates demos of Sakhi-to-Sakhi mesh coordination.

Two demo scenarios:
1. Personal Mesh: Your Sakhi ↔ Mom's Sakhi (dinner scheduling)
2. Business Mesh: Your Sakhi ↔ Restaurant Sakhi (reservation)

This enables split-screen demos showing both Sakhis coordinating.
"""

from __future__ import annotations

import asyncio
import logging
import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Callable
from enum import Enum

LOGGER = logging.getLogger(__name__)


class CoordinationScenario(str, Enum):
    """Demo scenarios."""
    PERSONAL_DINNER = "personal_dinner"  # Your Sakhi ↔ Mom's Sakhi
    BUSINESS_RESERVATION = "business_reservation"  # Your Sakhi ↔ Restaurant Sakhi
    RESCHEDULING = "rescheduling"  # Rescheduling existing event


@dataclass
class CoordinationDemoConfig:
    """Configuration for coordination demo."""
    scenario: CoordinationScenario = CoordinationScenario.PERSONAL_DINNER
    step_delay_ms: int = 2000  # Delay between steps for visibility
    auto_respond: bool = True  # Auto-respond on recipient side
    on_event: Optional[Callable[[Dict[str, Any]], None]] = None  # Callback per event


@dataclass
class CoordinationEvent:
    """An event in the coordination demo."""
    timestamp: datetime
    actor: str  # "user_sakhi", "mom_sakhi", "restaurant_sakhi", "user", "mom"
    action: str
    message: str
    data: Dict[str, Any] = field(default_factory=dict)


class CoordinationDemoRunner:
    """
    Runs coordination demonstrations.

    For split-screen demos, this generates events from both sides
    that can be displayed in parallel UI panels.
    """

    def __init__(self, config: CoordinationDemoConfig):
        self.config = config
        self.events: List[CoordinationEvent] = []
        self._running = False

    async def run(self) -> List[CoordinationEvent]:
        """Run the coordination demo and return all events."""
        self._running = True
        self.events = []

        LOGGER.info("[coordination_demo] Starting demo: %s", self.config.scenario.value)

        try:
            if self.config.scenario == CoordinationScenario.PERSONAL_DINNER:
                return await self._run_personal_dinner()
            elif self.config.scenario == CoordinationScenario.BUSINESS_RESERVATION:
                return await self._run_business_reservation()
            else:
                return await self._run_rescheduling()
        finally:
            self._running = False

    async def _emit_event(
        self,
        actor: str,
        action: str,
        message: str,
        data: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Emit an event and notify callback."""
        event = CoordinationEvent(
            timestamp=datetime.utcnow(),
            actor=actor,
            action=action,
            message=message,
            data=data or {},
        )
        self.events.append(event)

        LOGGER.info("[coordination_demo] [%s] %s: %s", actor, action, message[:50])

        if self.config.on_event:
            self.config.on_event({
                "timestamp": event.timestamp.isoformat(),
                "actor": event.actor,
                "action": event.action,
                "message": event.message,
                "data": event.data,
            })

        await asyncio.sleep(self.config.step_delay_ms / 1000)

    async def _run_personal_dinner(self) -> List[CoordinationEvent]:
        """
        Demo: Your Sakhi coordinating dinner with Mom's Sakhi.

        Shows:
        - Natural language request
        - Availability checking
        - Time proposal and acceptance
        - Calendar creation on both sides
        """
        now = datetime.utcnow()
        proposed_time = (now + timedelta(days=2)).replace(hour=18, minute=0)

        # User initiates
        await self._emit_event(
            "user",
            "request",
            "Hey Sakhi, can you set up dinner with Mom this week?",
        )

        # Your Sakhi processes
        await self._emit_event(
            "user_sakhi",
            "understanding",
            "I'll coordinate with Mom's Sakhi to find a time that works for both of you.",
            {"intent": "schedule_dinner", "with": "Mom", "timeframe": "this_week"},
        )

        # Your Sakhi checks your calendar
        await self._emit_event(
            "user_sakhi",
            "checking_calendar",
            "Checking your calendar for available times...",
            {"available_slots": 5},
        )

        # Your Sakhi reaches out to Mom's Sakhi
        await self._emit_event(
            "user_sakhi",
            "initiating_coordination",
            "Reaching out to Mom's Sakhi...",
            {"coordination_type": "scheduling"},
        )

        # Mom's Sakhi receives
        await self._emit_event(
            "mom_sakhi",
            "receiving",
            "Received a dinner request from Alex's Sakhi.",
            {"from": "Alex", "request": "dinner", "timeframe": "this_week"},
        )

        # Mom's Sakhi checks Mom's calendar
        await self._emit_event(
            "mom_sakhi",
            "checking_calendar",
            "Checking available times...",
            {"available_slots": 4},
        )

        # Mom's Sakhi finds overlap
        await self._emit_event(
            "mom_sakhi",
            "found_overlap",
            "Found times that work for both!",
            {"overlapping_slots": [
                {"day": "Thursday", "time": "6:00 PM"},
                {"day": "Friday", "time": "7:00 PM"},
            ]},
        )

        # Mom's Sakhi proposes (considering Mom's preferences)
        await self._emit_event(
            "mom_sakhi",
            "proposing",
            "Thursday 6pm works best - Mom prefers earlier dinners.",
            {"proposed_time": proposed_time.isoformat(), "reason": "prefers_earlier"},
        )

        # Your Sakhi receives proposal
        await self._emit_event(
            "user_sakhi",
            "received_proposal",
            "Mom's Sakhi suggests Thursday at 6pm.",
            {"proposed_time": proposed_time.isoformat()},
        )

        # Your Sakhi checks with you
        await self._emit_event(
            "user_sakhi",
            "confirming",
            "Mom's available Thursday at 6pm. That works with your schedule too. Shall I confirm?",
            {"needs_confirmation": True},
        )

        # User confirms
        await self._emit_event(
            "user",
            "confirm",
            "Yes, that works!",
        )

        # Your Sakhi confirms with Mom's Sakhi
        await self._emit_event(
            "user_sakhi",
            "sending_confirmation",
            "Confirming Thursday at 6pm with Mom's Sakhi...",
        )

        # Mom's Sakhi receives confirmation
        await self._emit_event(
            "mom_sakhi",
            "confirmed",
            "Alex confirmed Thursday at 6pm!",
            {"status": "confirmed"},
        )

        # Mom's Sakhi notifies Mom
        await self._emit_event(
            "mom_sakhi",
            "notifying",
            "Telling Mom: 'Dinner with Alex is set for Thursday at 6pm'",
        )

        # Mom's Sakhi creates event
        await self._emit_event(
            "mom_sakhi",
            "creating_event",
            "Adding to Mom's calendar: Dinner with Alex - Thursday 6pm",
            {"event_created": True},
        )

        # Your Sakhi creates event
        await self._emit_event(
            "user_sakhi",
            "creating_event",
            "Adding to your calendar: Dinner with Mom - Thursday 6pm",
            {"event_created": True},
        )

        # Final confirmation
        await self._emit_event(
            "user_sakhi",
            "complete",
            "Done! Dinner with Mom is scheduled for Thursday at 6pm. Both calendars are updated.",
            {"status": "completed", "event_time": proposed_time.isoformat()},
        )

        return self.events

    async def _run_business_reservation(self) -> List[CoordinationEvent]:
        """
        Demo: Your Sakhi making reservation with Restaurant Sakhi.

        Shows:
        - Preference sharing (with consent)
        - Availability checking
        - Special requests based on preferences
        - Confirmation flow
        """
        now = datetime.utcnow()
        reservation_time = (now + timedelta(days=1)).replace(hour=19, minute=30)

        # User initiates
        await self._emit_event(
            "user",
            "request",
            "Book a table at Golden Gate Bistro for tomorrow evening, 2 people",
        )

        # Your Sakhi processes
        await self._emit_event(
            "user_sakhi",
            "understanding",
            "I'll coordinate with the restaurant's Sakhi. Let me check availability and share your relevant preferences.",
            {"restaurant": "Golden Gate Bistro", "party_size": 2, "date": "tomorrow"},
        )

        # Your Sakhi retrieves preferences
        await self._emit_event(
            "user_sakhi",
            "retrieving_preferences",
            "Getting your dining preferences to share with the restaurant...",
            {"preferences": {
                "seating": "booth",
                "noise": "quiet",
                "allergies": ["shellfish"],
            }},
        )

        # Your Sakhi reaches out to Restaurant Sakhi
        await self._emit_event(
            "user_sakhi",
            "initiating_coordination",
            "Connecting with Golden Gate Bistro's Sakhi...",
        )

        # Restaurant Sakhi receives
        await self._emit_event(
            "restaurant_sakhi",
            "receiving",
            "Reservation request received for 2 guests tomorrow evening.",
            {"guest": "Alex", "party_size": 2, "preferences_shared": True},
        )

        # Restaurant Sakhi checks availability
        await self._emit_event(
            "restaurant_sakhi",
            "checking_availability",
            "Checking table availability for tomorrow evening...",
            {"date": "tomorrow", "available_times": ["7:00 PM", "7:30 PM", "8:00 PM"]},
        )

        # Restaurant Sakhi considers preferences
        await self._emit_event(
            "restaurant_sakhi",
            "matching_preferences",
            "Matching guest preferences: booth seating, quiet area...",
            {"has_booth_available": True, "quiet_section": "available"},
        )

        # Restaurant Sakhi notes allergy
        await self._emit_event(
            "restaurant_sakhi",
            "noting_dietary",
            "Noted: Guest has shellfish allergy. Kitchen will be informed.",
            {"allergy_noted": True, "kitchen_alert": "shellfish"},
        )

        # Restaurant Sakhi proposes
        await self._emit_event(
            "restaurant_sakhi",
            "proposing",
            "We can offer a quiet booth at 7:30 PM. Perfect for your preferences!",
            {"time": "7:30 PM", "table": "Booth 7", "section": "Quiet corner"},
        )

        # Your Sakhi receives
        await self._emit_event(
            "user_sakhi",
            "received_proposal",
            "They have a quiet booth available at 7:30 PM - exactly what you like!",
            {"time": reservation_time.isoformat(), "special_arrangements": ["booth", "quiet_section"]},
        )

        # Your Sakhi confirms with user
        await self._emit_event(
            "user_sakhi",
            "confirming",
            "Golden Gate Bistro can seat you at 7:30 PM in a quiet booth. They've also noted your shellfish allergy. Confirm?",
            {"needs_confirmation": True},
        )

        # User confirms
        await self._emit_event(
            "user",
            "confirm",
            "Perfect, book it!",
        )

        # Your Sakhi sends confirmation
        await self._emit_event(
            "user_sakhi",
            "sending_confirmation",
            "Confirming reservation...",
        )

        # Restaurant Sakhi confirms
        await self._emit_event(
            "restaurant_sakhi",
            "confirmed",
            "Reservation confirmed! Booth 7, 7:30 PM. Kitchen alerted about allergy.",
            {"confirmation_number": "GGB-2024-1234", "status": "confirmed"},
        )

        # Restaurant Sakhi sends details
        await self._emit_event(
            "restaurant_sakhi",
            "sending_details",
            "Sending confirmation details to guest's Sakhi...",
            {"address": "2847 California St", "parking": "Valet available"},
        )

        # Your Sakhi creates event
        await self._emit_event(
            "user_sakhi",
            "creating_event",
            "Adding to calendar: Dinner at Golden Gate Bistro - 7:30 PM",
            {"event_created": True},
        )

        # Final summary
        await self._emit_event(
            "user_sakhi",
            "complete",
            "Reserved! Golden Gate Bistro tomorrow at 7:30 PM. Quiet booth, shellfish allergy noted. Confirmation #GGB-2024-1234",
            {
                "status": "completed",
                "confirmation": "GGB-2024-1234",
                "time": reservation_time.isoformat(),
                "special_notes": ["booth seating", "quiet section", "shellfish allergy noted"],
            },
        )

        return self.events

    async def _run_rescheduling(self) -> List[CoordinationEvent]:
        """Demo: Rescheduling an existing event."""
        # Simplified rescheduling flow
        await self._emit_event(
            "user",
            "request",
            "I need to reschedule dinner with Mom - something came up Thursday.",
        )

        await self._emit_event(
            "user_sakhi",
            "understanding",
            "I'll coordinate with Mom's Sakhi to find a new time.",
        )

        await self._emit_event(
            "user_sakhi",
            "initiating_coordination",
            "Sending reschedule request to Mom's Sakhi...",
        )

        await self._emit_event(
            "mom_sakhi",
            "receiving",
            "Alex needs to reschedule Thursday dinner.",
        )

        await self._emit_event(
            "mom_sakhi",
            "checking_calendar",
            "Checking Mom's availability for alternatives...",
        )

        await self._emit_event(
            "mom_sakhi",
            "proposing",
            "Friday at 7pm works for Mom.",
        )

        await self._emit_event(
            "user_sakhi",
            "received_proposal",
            "Mom's free Friday at 7pm instead.",
        )

        await self._emit_event(
            "user_sakhi",
            "confirming",
            "Can you do Friday at 7pm with Mom instead?",
        )

        await self._emit_event(
            "user",
            "confirm",
            "Yes, Friday works.",
        )

        await self._emit_event(
            "user_sakhi",
            "complete",
            "Rescheduled! Dinner with Mom moved to Friday 7pm. Both calendars updated.",
        )

        return self.events

    def stop(self) -> None:
        """Stop the demo."""
        self._running = False


async def run_coordination_demo(
    scenario: CoordinationScenario = CoordinationScenario.PERSONAL_DINNER,
    on_event: Optional[Callable[[Dict[str, Any]], None]] = None,
) -> List[Dict[str, Any]]:
    """
    Convenience function to run a coordination demo.

    Returns list of event dictionaries for easy JSON serialization.
    """
    config = CoordinationDemoConfig(
        scenario=scenario,
        on_event=on_event,
    )

    runner = CoordinationDemoRunner(config)
    events = await runner.run()

    return [
        {
            "timestamp": e.timestamp.isoformat(),
            "actor": e.actor,
            "action": e.action,
            "message": e.message,
            "data": e.data,
        }
        for e in events
    ]


__all__ = [
    "CoordinationDemoConfig",
    "CoordinationDemoRunner",
    "CoordinationEvent",
    "CoordinationScenario",
    "run_coordination_demo",
]
