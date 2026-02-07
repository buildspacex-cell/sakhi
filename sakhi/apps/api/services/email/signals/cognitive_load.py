"""
Cognitive Load Analyzer
-----------------------
Measures email-related cognitive load by analyzing:
- Active thread count and complexity
- Distribution of attention sinks
- Heavy threads vs background noise

This helps surface:
- Overwhelm risk
- Attention fragmentation
- "Few heavy threads" vs "many light threads" patterns
"""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from sakhi.apps.api.services.email.models import (
    CognitiveLoadSignal,
    EmailDirection,
    EmailEvent,
    EmailThread,
)

LOGGER = logging.getLogger(__name__)

# Thresholds for thread classification
HEAVY_THREAD_MESSAGE_THRESHOLD = 10
HEAVY_THREAD_PARTICIPANT_THRESHOLD = 5
ACTIVE_THREAD_DAYS = 3  # Thread with activity in last N days


class CognitiveLoadAnalyzer:
    """
    Analyzes email patterns to measure cognitive load.

    Key metrics:
    - Total active threads
    - Heavy threads (high message count or participants)
    - Top attention sinks (senders consuming most attention)
    - Load distribution
    """

    def __init__(
        self,
        heavy_message_threshold: int = HEAVY_THREAD_MESSAGE_THRESHOLD,
        heavy_participant_threshold: int = HEAVY_THREAD_PARTICIPANT_THRESHOLD,
        active_days: int = ACTIVE_THREAD_DAYS,
    ):
        self.heavy_message_threshold = heavy_message_threshold
        self.heavy_participant_threshold = heavy_participant_threshold
        self.active_days = active_days

    def analyze(
        self,
        events: List[EmailEvent],
        threads: Optional[List[EmailThread]] = None,
        *,
        period_days: int = 7,
    ) -> CognitiveLoadSignal:
        """
        Analyze cognitive load from email events.

        Args:
            events: List of normalized email events
            threads: Optional pre-computed threads
            period_days: Analysis period

        Returns:
            CognitiveLoadSignal with load metrics
        """
        now = datetime.now(timezone.utc)
        period_start = now - timedelta(days=period_days)
        active_cutoff = now - timedelta(days=self.active_days)

        # Filter to period
        period_events = [e for e in events if e.timestamp >= period_start]

        # Build threads if not provided
        if threads is None:
            threads = self._build_threads(period_events)

        # Classify threads
        active_threads = []
        heavy_threads = []

        for thread in threads:
            # Check if active
            if thread.last_message_at >= active_cutoff:
                active_threads.append(thread)

            # Check if heavy
            if (thread.message_count >= self.heavy_message_threshold or
                thread.participant_count >= self.heavy_participant_threshold):
                heavy_threads.append(thread)

        # Analyze top senders
        top_senders = self._analyze_top_senders(period_events)

        # Categorize threads by age
        thread_by_age = self._categorize_by_age(threads, now)

        # Calculate load score
        load_score = self._calculate_load_score(
            total_threads=len(threads),
            active_threads=len(active_threads),
            heavy_threads=len(heavy_threads),
            period_events=len(period_events),
        )

        # Determine overwhelm risk
        overwhelm_risk = self._assess_overwhelm_risk(
            load_score=load_score,
            active_count=len(active_threads),
            heavy_count=len(heavy_threads),
        )

        return CognitiveLoadSignal(
            period_start=period_start,
            period_end=now,
            total_threads=len(threads),
            active_threads=len(active_threads),
            heavy_threads=len(heavy_threads),
            top_senders=top_senders[:5],
            thread_by_age=thread_by_age,
            load_score=load_score,
            overwhelm_risk=overwhelm_risk,
            confidence=0.8 if len(period_events) >= 20 else 0.5,
        )

    def _build_threads(self, events: List[EmailEvent]) -> List[EmailThread]:
        """Build lightweight thread objects from events."""
        # Group by thread
        by_thread: Dict[str, List[EmailEvent]] = defaultdict(list)
        for event in events:
            by_thread[event.thread_id].append(event)

        threads = []
        for thread_id, thread_events in by_thread.items():
            if not thread_events:
                continue

            sorted_events = sorted(thread_events, key=lambda e: e.timestamp)

            # Collect participants
            participants = {}
            for event in thread_events:
                participants[event.sender.email] = event.sender
                for r in event.recipients:
                    participants[r.email] = r

            # Count directions
            incoming = sum(1 for e in thread_events if e.direction == EmailDirection.INCOMING)
            outgoing = len(thread_events) - incoming

            threads.append(EmailThread(
                thread_id=thread_id,
                provider=sorted_events[0].provider,
                subject=sorted_events[0].subject,
                participant_count=len(participants),
                participants=list(participants.values()),
                first_message_at=sorted_events[0].timestamp,
                last_message_at=sorted_events[-1].timestamp,
                message_count=len(thread_events),
                incoming_count=incoming,
                outgoing_count=outgoing,
                last_direction=sorted_events[-1].direction,
            ))

        return threads

    def _analyze_top_senders(
        self,
        events: List[EmailEvent],
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Identify top senders by email volume."""
        sender_counts: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            "email": "",
            "name": None,
            "domain": "",
            "count": 0,
            "thread_ids": set(),
        })

        for event in events:
            if event.direction != EmailDirection.INCOMING:
                continue

            key = event.sender.email.lower()
            sender_counts[key]["email"] = event.sender.email
            sender_counts[key]["name"] = event.sender.name or sender_counts[key]["name"]
            sender_counts[key]["domain"] = event.sender.domain
            sender_counts[key]["count"] += 1
            sender_counts[key]["thread_ids"].add(event.thread_id)

        # Sort by count
        sorted_senders = sorted(
            sender_counts.values(),
            key=lambda x: x["count"],
            reverse=True,
        )

        # Convert sets to counts
        result = []
        for sender in sorted_senders[:limit]:
            result.append({
                "email": sender["email"],
                "name": sender["name"],
                "domain": sender["domain"],
                "email_count": sender["count"],
                "thread_count": len(sender["thread_ids"]),
            })

        return result

    def _categorize_by_age(
        self,
        threads: List[EmailThread],
        now: datetime,
    ) -> Dict[str, int]:
        """Categorize threads by age of last activity."""
        categories = {
            "today": 0,
            "this_week": 0,
            "older": 0,
        }

        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = today_start - timedelta(days=7)

        for thread in threads:
            if thread.last_message_at >= today_start:
                categories["today"] += 1
            elif thread.last_message_at >= week_start:
                categories["this_week"] += 1
            else:
                categories["older"] += 1

        return categories

    def _calculate_load_score(
        self,
        total_threads: int,
        active_threads: int,
        heavy_threads: int,
        period_events: int,
    ) -> float:
        """
        Calculate cognitive load score (0-1).

        Factors:
        - Active thread count (demand on attention)
        - Heavy thread ratio (complexity)
        - Overall volume
        """
        if total_threads == 0:
            return 0.0

        # Normalize metrics
        active_factor = min(1.0, active_threads / 20)  # 20+ active = max
        heavy_factor = min(1.0, heavy_threads / 5)     # 5+ heavy = max
        volume_factor = min(1.0, period_events / 200)  # 200+ events = max

        # Weighted combination
        score = (
            active_factor * 0.4 +
            heavy_factor * 0.4 +
            volume_factor * 0.2
        )

        return round(min(1.0, score), 3)

    def _assess_overwhelm_risk(
        self,
        load_score: float,
        active_count: int,
        heavy_count: int,
    ) -> str:
        """Assess risk of overwhelm based on load metrics."""
        if load_score >= 0.7 or heavy_count >= 5:
            return "high"
        elif load_score >= 0.4 or heavy_count >= 3 or active_count >= 15:
            return "moderate"
        else:
            return "low"


async def compute_cognitive_load(
    events: List[EmailEvent],
    *,
    period_days: int = 7,
    threads: Optional[List[EmailThread]] = None,
) -> CognitiveLoadSignal:
    """
    Compute cognitive load signal from email events.

    Args:
        events: List of normalized email events
        period_days: Analysis period
        threads: Optional pre-computed threads

    Returns:
        CognitiveLoadSignal with load metrics
    """
    analyzer = CognitiveLoadAnalyzer()
    return analyzer.analyze(events, threads=threads, period_days=period_days)


__all__ = ["compute_cognitive_load", "CognitiveLoadAnalyzer"]
