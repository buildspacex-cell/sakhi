"""
Avoidance / Postponement Detector
---------------------------------
Detects threads where the user is avoiding a reply.

Signals:
- Long gaps without outgoing reply
- Repeated follow-ups from sender
- Thread reopens without action

This is valuable for surfacing "mental load" items
that the user might be putting off.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime, timezone
from typing import Dict, List, Optional

from sakhi.apps.api.services.email.models import (
    AvoidanceSignal,
    EmailDirection,
    EmailEvent,
    EmailThread,
)

LOGGER = logging.getLogger(__name__)

# Thresholds for avoidance detection
MIN_GAP_DAYS_MILD = 7
MIN_GAP_DAYS_MODERATE = 14
MIN_GAP_DAYS_SIGNIFICANT = 21

# Exclude automated/newsletter emails from avoidance detection
EXCLUDE_DOMAINS = {
    "noreply", "no-reply", "donotreply", "mailer-daemon",
    "notifications", "updates", "news", "newsletter",
}


class AvoidanceDetector:
    """
    Analyzes email threads to detect avoidance patterns.

    Key indicators:
    1. Time since last incoming without reply
    2. Number of follow-ups from sender
    3. Thread length and engagement
    """

    def __init__(
        self,
        min_gap_days: int = 7,
        exclude_automated: bool = True,
        exclude_newsletters: bool = True,
    ):
        self.min_gap_days = min_gap_days
        self.exclude_automated = exclude_automated
        self.exclude_newsletters = exclude_newsletters

    def detect(
        self,
        events: List[EmailEvent],
        user_email: str,
    ) -> List[AvoidanceSignal]:
        """
        Detect avoidance patterns from email events.

        Args:
            events: List of normalized email events
            user_email: The user's email address

        Returns:
            List of detected avoidance signals
        """
        if not events:
            return []

        # Update direction based on user email
        for event in events:
            if user_email.lower() in event.sender.email.lower():
                event.direction = EmailDirection.OUTGOING
            else:
                event.direction = EmailDirection.INCOMING

        # Group by thread
        by_thread: Dict[str, List[EmailEvent]] = defaultdict(list)
        for event in events:
            by_thread[event.thread_id].append(event)

        signals = []

        for thread_id, thread_events in by_thread.items():
            signal = self._analyze_thread(thread_id, thread_events)
            if signal:
                signals.append(signal)

        # Sort by severity (duration_days) descending
        signals.sort(key=lambda s: s.duration_days, reverse=True)

        LOGGER.info("[AvoidanceDetector] Found %d avoidance patterns", len(signals))
        return signals

    def detect_from_threads(
        self,
        threads: List[EmailThread],
    ) -> List[AvoidanceSignal]:
        """
        Detect avoidance from pre-computed EmailThread objects.

        More efficient when threads are already built.
        """
        signals = []

        for thread in threads:
            signal = self._analyze_precomputed_thread(thread)
            if signal:
                signals.append(signal)

        signals.sort(key=lambda s: s.duration_days, reverse=True)
        return signals

    def _analyze_thread(
        self,
        thread_id: str,
        events: List[EmailEvent],
    ) -> Optional[AvoidanceSignal]:
        """Analyze a single thread for avoidance patterns."""
        if not events:
            return None

        # Sort by timestamp
        sorted_events = sorted(events, key=lambda e: e.timestamp)

        # For single-message threads, only check if it's an incoming message awaiting reply
        if len(sorted_events) == 1:
            event = sorted_events[0]
            if event.direction != EmailDirection.INCOMING:
                return None
            # Check exclusions for single message
            if self.exclude_automated and event.is_automated:
                return None
            if self.exclude_newsletters and event.is_newsletter:
                return None
            sender_parts = event.sender.email.lower().split("@")
            if sender_parts and any(ex in sender_parts[0] for ex in EXCLUDE_DOMAINS):
                return None

            # Calculate gap
            now = datetime.now(timezone.utc)
            gap_days = (now - event.timestamp).days
            if gap_days < self.min_gap_days:
                return None

            # Determine severity for single-message thread
            if gap_days >= MIN_GAP_DAYS_SIGNIFICANT:
                severity = "significant"
            elif gap_days >= MIN_GAP_DAYS_MODERATE:
                severity = "moderate"
            else:
                severity = "mild"

            suggested_action = self._suggest_action(gap_days, 0, severity)

            return AvoidanceSignal(
                thread_id=thread_id,
                subject=event.subject,
                sender_email=event.sender.email,
                sender_name=event.sender.name,
                duration_days=gap_days,
                follow_up_count=0,
                last_incoming_at=event.timestamp,
                severity=severity,
                confidence=0.5,
                suggested_action=suggested_action,
            )

        # Check exclusions
        latest_incoming = None
        for event in reversed(sorted_events):
            if event.direction == EmailDirection.INCOMING:
                # Check if automated/newsletter
                if self.exclude_automated and event.is_automated:
                    return None
                if self.exclude_newsletters and event.is_newsletter:
                    return None
                # Check domain exclusions
                sender_parts = event.sender.email.lower().split("@")
                if sender_parts and any(ex in sender_parts[0] for ex in EXCLUDE_DOMAINS):
                    return None

                latest_incoming = event
                break

        if not latest_incoming:
            return None

        # Find last outgoing
        latest_outgoing = None
        for event in reversed(sorted_events):
            if event.direction == EmailDirection.OUTGOING:
                latest_outgoing = event
                break

        # Check if awaiting reply
        if latest_outgoing and latest_outgoing.timestamp > latest_incoming.timestamp:
            # We replied after their last message - no avoidance
            return None

        # Calculate gap
        now = datetime.now(timezone.utc)
        gap_days = (now - latest_incoming.timestamp).days

        if gap_days < self.min_gap_days:
            return None

        # Count follow-ups (incoming messages without reply)
        follow_up_count = 0
        last_outgoing_time = latest_outgoing.timestamp if latest_outgoing else None

        for event in sorted_events:
            if event.direction == EmailDirection.INCOMING:
                if last_outgoing_time is None or event.timestamp > last_outgoing_time:
                    follow_up_count += 1
            else:
                last_outgoing_time = event.timestamp

        # Subtract 1 because the first message isn't a "follow-up"
        follow_up_count = max(0, follow_up_count - 1)

        # Determine severity
        if gap_days >= MIN_GAP_DAYS_SIGNIFICANT or follow_up_count >= 3:
            severity = "significant"
        elif gap_days >= MIN_GAP_DAYS_MODERATE or follow_up_count >= 2:
            severity = "moderate"
        else:
            severity = "mild"

        # Compute confidence
        confidence = 0.5
        if follow_up_count > 0:
            confidence += 0.1 * min(follow_up_count, 3)
        if gap_days > MIN_GAP_DAYS_MODERATE:
            confidence += 0.1
        if gap_days > MIN_GAP_DAYS_SIGNIFICANT:
            confidence += 0.1

        # Generate suggested action
        suggested_action = self._suggest_action(gap_days, follow_up_count, severity)

        return AvoidanceSignal(
            thread_id=thread_id,
            subject=sorted_events[0].subject,
            sender_email=latest_incoming.sender.email,
            sender_name=latest_incoming.sender.name,
            duration_days=gap_days,
            follow_up_count=follow_up_count,
            last_incoming_at=latest_incoming.timestamp,
            severity=severity,
            confidence=min(0.95, confidence),
            suggested_action=suggested_action,
        )

    def _analyze_precomputed_thread(
        self,
        thread: EmailThread,
    ) -> Optional[AvoidanceSignal]:
        """Analyze a pre-computed EmailThread for avoidance."""
        # Must be awaiting reply
        if not thread.awaiting_reply:
            return None

        # Must have a gap
        if not thread.reply_gap_hours:
            return None

        gap_days = int(thread.reply_gap_hours / 24)

        if gap_days < self.min_gap_days:
            return None

        # Determine severity
        if gap_days >= MIN_GAP_DAYS_SIGNIFICANT or thread.follow_up_count >= 3:
            severity = "significant"
        elif gap_days >= MIN_GAP_DAYS_MODERATE or thread.follow_up_count >= 2:
            severity = "moderate"
        else:
            severity = "mild"

        # Compute confidence
        confidence = 0.5
        if thread.follow_up_count > 0:
            confidence += 0.1 * min(thread.follow_up_count, 3)
        if gap_days > MIN_GAP_DAYS_MODERATE:
            confidence += 0.1
        if gap_days > MIN_GAP_DAYS_SIGNIFICANT:
            confidence += 0.1

        # Get sender from participants (first non-user)
        sender_email = ""
        sender_name = None
        for p in thread.participants:
            if thread.last_incoming_at:
                sender_email = p.email
                sender_name = p.name
                break

        suggested_action = self._suggest_action(gap_days, thread.follow_up_count, severity)

        return AvoidanceSignal(
            thread_id=thread.thread_id,
            subject=thread.subject,
            sender_email=sender_email,
            sender_name=sender_name,
            duration_days=gap_days,
            follow_up_count=thread.follow_up_count,
            last_incoming_at=thread.last_incoming_at or datetime.now(timezone.utc),
            severity=severity,
            confidence=min(0.95, confidence),
            suggested_action=suggested_action,
        )

    def _suggest_action(
        self,
        gap_days: int,
        follow_up_count: int,
        severity: str,
    ) -> str:
        """Generate a suggested action based on avoidance pattern."""
        if follow_up_count >= 2:
            return "They've followed up multiple times. A quick reply would help."
        elif severity == "significant":
            return "This has been sitting for a while. Even a brief response could help."
        elif gap_days > 14:
            return "You might want to address this soon."
        else:
            return "Consider replying when you have a moment."


async def detect_avoidance(
    events: List[EmailEvent],
    user_email: str,
    *,
    min_gap_days: int = 7,
    exclude_automated: bool = True,
) -> List[AvoidanceSignal]:
    """
    Detect avoidance patterns from email events.

    Args:
        events: List of normalized email events
        user_email: The user's email address
        min_gap_days: Minimum days without reply to flag
        exclude_automated: Skip automated/newsletter emails

    Returns:
        List of detected avoidance signals
    """
    detector = AvoidanceDetector(
        min_gap_days=min_gap_days,
        exclude_automated=exclude_automated,
    )
    return detector.detect(events, user_email)


__all__ = ["detect_avoidance", "AvoidanceDetector"]
