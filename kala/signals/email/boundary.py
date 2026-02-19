"""
Boundary & Rhythm Signal Detector
---------------------------------
Detects boundary erosion patterns from email timing.

Signals:
- After-hours email activity
- Weekend email volume
- Late-night spikes
- Trend analysis (improving/worsening)

Maps to friction framework:
- High after-hours activity -> Chaos Friction (Vata)
- Sustained boundary erosion -> Energy depletion
"""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime, time, timedelta, timezone
from typing import Any

from kala.signals.email.models import (
    BoundarySignal,
    EmailEvent,
)

LOGGER = logging.getLogger(__name__)

# Time boundaries (configurable per user in future)
DEFAULT_WORK_START = time(9, 0)   # 9 AM
DEFAULT_WORK_END = time(18, 0)    # 6 PM
LATE_NIGHT_START = time(22, 0)   # 10 PM

# Weekend days (0 = Monday, 6 = Sunday)
WEEKEND_DAYS = {5, 6}  # Saturday, Sunday

# Thresholds for friction mapping
EROSION_THRESHOLD_LOW = 0.15
EROSION_THRESHOLD_MODERATE = 0.30
EROSION_THRESHOLD_HIGH = 0.50


class BoundaryDetector:
    """
    Analyzes email timing patterns to detect boundary erosion.

    This helps surface:
    - Work bleeding into personal time
    - Recovery disruption
    - Rhythm irregularity
    """

    def __init__(
        self,
        work_start: time = DEFAULT_WORK_START,
        work_end: time = DEFAULT_WORK_END,
        user_timezone: timezone | None = None,
    ) -> None:
        self.work_start = work_start
        self.work_end = work_end
        self.user_timezone = user_timezone or timezone.utc

    def detect(
        self,
        events: list[EmailEvent],
        *,
        period_days: int = 7,
        compare_previous: bool = True,
    ) -> BoundarySignal:
        """
        Detect boundary patterns from email events.

        Args:
            events: List of normalized email events
            period_days: Analysis period in days
            compare_previous: Compare to previous period for trend

        Returns:
            BoundarySignal with metrics and trend
        """
        now = datetime.now(timezone.utc)
        period_start = now - timedelta(days=period_days)

        # Filter to period
        period_events = [
            e for e in events
            if e.timestamp >= period_start
        ]

        # Calculate metrics for current period
        metrics = self._calculate_metrics(period_events)

        # Calculate trend if requested
        trend = "stable"
        previous_after_hours_pct = None

        if compare_previous:
            prev_start = period_start - timedelta(days=period_days)
            prev_events = [
                e for e in events
                if prev_start <= e.timestamp < period_start
            ]

            if prev_events:
                prev_metrics = self._calculate_metrics(prev_events)
                previous_after_hours_pct = prev_metrics["after_hours_pct"]

                # Determine trend
                diff = metrics["after_hours_pct"] - prev_metrics["after_hours_pct"]
                if diff > 0.1:
                    trend = "worsening"
                elif diff < -0.1:
                    trend = "improving"

        # Calculate erosion score (0-1)
        erosion_score = self._calculate_erosion_score(metrics)

        # Map to friction impact
        friction_impact = self._map_to_friction(erosion_score, metrics)

        return BoundarySignal(
            period_start=period_start,
            period_end=now,
            total_emails=metrics["total"],
            after_hours_count=metrics["after_hours"],
            after_hours_pct=metrics["after_hours_pct"],
            weekend_count=metrics["weekend"],
            weekend_pct=metrics["weekend_pct"],
            late_night_count=metrics["late_night"],
            trend=trend,
            previous_after_hours_pct=previous_after_hours_pct,
            erosion_score=erosion_score,
            friction_impact=friction_impact,
            confidence=0.8 if metrics["total"] >= 10 else 0.5,
        )

    def detect_daily_patterns(
        self,
        events: list[EmailEvent],
        *,
        lookback_days: int = 30,
    ) -> list[dict[str, Any]]:
        """
        Analyze daily patterns for rhythm insights.

        Returns per-day breakdown useful for:
        - Identifying problematic days
        - Showing weekly patterns
        """
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(days=lookback_days)

        # Filter and group by date
        by_date: dict[str, list[EmailEvent]] = defaultdict(list)
        for event in events:
            if event.timestamp >= cutoff:
                date_key = event.timestamp.date().isoformat()
                by_date[date_key].append(event)

        patterns = []
        for date_str, day_events in sorted(by_date.items()):
            date = datetime.fromisoformat(date_str).date()
            metrics = self._calculate_metrics(day_events)

            patterns.append({
                "date": date_str,
                "day_of_week": date.strftime("%A"),
                "is_weekend": date.weekday() in WEEKEND_DAYS,
                "total": metrics["total"],
                "after_hours": metrics["after_hours"],
                "after_hours_pct": metrics["after_hours_pct"],
                "late_night": metrics["late_night"],
                "first_email_time": min(e.timestamp for e in day_events).strftime("%H:%M") if day_events else None,
                "last_email_time": max(e.timestamp for e in day_events).strftime("%H:%M") if day_events else None,
            })

        return patterns

    def _calculate_metrics(
        self,
        events: list[EmailEvent],
    ) -> dict[str, Any]:
        """Calculate boundary metrics for a set of events."""
        if not events:
            return {
                "total": 0,
                "after_hours": 0,
                "after_hours_pct": 0.0,
                "weekend": 0,
                "weekend_pct": 0.0,
                "late_night": 0,
                "late_night_pct": 0.0,
            }

        total = len(events)
        after_hours = 0
        weekend = 0
        late_night = 0

        for event in events:
            # Convert to user timezone
            event_time = event.timestamp.astimezone(self.user_timezone)
            event_time_only = event_time.time()
            event_weekday = event_time.weekday()

            # Check if outside work hours
            if event_time_only < self.work_start or event_time_only >= self.work_end:
                after_hours += 1

            # Check if weekend
            if event_weekday in WEEKEND_DAYS:
                weekend += 1

            # Check if late night
            if event_time_only >= LATE_NIGHT_START:
                late_night += 1

        return {
            "total": total,
            "after_hours": after_hours,
            "after_hours_pct": round(after_hours / total, 3) if total > 0 else 0.0,
            "weekend": weekend,
            "weekend_pct": round(weekend / total, 3) if total > 0 else 0.0,
            "late_night": late_night,
            "late_night_pct": round(late_night / total, 3) if total > 0 else 0.0,
        }

    def _calculate_erosion_score(self, metrics: dict[str, Any]) -> float:
        """
        Calculate overall boundary erosion score (0-1).

        Weighted combination of:
        - After-hours activity (50%)
        - Weekend activity (30%)
        - Late-night activity (20%)
        """
        if metrics["total"] == 0:
            return 0.0

        score = (
            metrics["after_hours_pct"] * 0.5
            + metrics["weekend_pct"] * 0.3
            + metrics["late_night_pct"] * 0.2
        )

        return round(min(1.0, score), 3)

    def _map_to_friction(
        self,
        erosion_score: float,
        metrics: dict[str, Any],
    ) -> str | None:
        """
        Map erosion patterns to friction framework.

        High boundary erosion typically indicates:
        - Vata imbalance (scattered energy, anxiety)
        - Pitta imbalance (overwork, burnout) if sustained
        """
        if erosion_score < EROSION_THRESHOLD_LOW:
            return None  # Healthy boundaries

        # Late night specifically suggests Vata disturbance
        if metrics["late_night_pct"] > 0.15:
            return "chaos_friction"  # Vata - scattered, anxious

        if erosion_score >= EROSION_THRESHOLD_HIGH:
            # Sustained high activity suggests Pitta burnout
            return "intensity_friction"  # Pitta - overwork, burnout

        if erosion_score >= EROSION_THRESHOLD_MODERATE:
            return "chaos_friction"  # Vata - boundary dissolution

        return None


async def detect_boundary_patterns(
    events: list[EmailEvent],
    *,
    period_days: int = 7,
    work_start: time = DEFAULT_WORK_START,
    work_end: time = DEFAULT_WORK_END,
) -> BoundarySignal:
    """
    Detect boundary erosion patterns from email events.

    Args:
        events: List of normalized email events
        period_days: Analysis period
        work_start: Start of work hours
        work_end: End of work hours

    Returns:
        BoundarySignal with erosion metrics and friction mapping
    """
    detector = BoundaryDetector(
        work_start=work_start,
        work_end=work_end,
    )
    return detector.detect(events, period_days=period_days)


__all__ = ["detect_boundary_patterns", "BoundaryDetector"]
