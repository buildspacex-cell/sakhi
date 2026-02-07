"""
Subscription & Recurrence Detector
----------------------------------
Detects recurring emails, newsletters, and subscriptions
using deterministic rules on email metadata.

Signals:
- List-Unsubscribe header presence
- Repeated sender domain patterns
- Regular cadence (daily/weekly/monthly)
- Billing/transactional keywords
"""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

from sakhi.apps.api.services.email.models import (
    EmailEvent,
    SubscriptionSignal,
)

LOGGER = logging.getLogger(__name__)

# Domain categories for classification
DOMAIN_CATEGORIES = {
    # Entertainment
    "netflix.com": "entertainment",
    "spotify.com": "entertainment",
    "hulu.com": "entertainment",
    "disneyplus.com": "entertainment",
    "hbomax.com": "entertainment",
    "apple.com": "entertainment",  # Apple TV+
    "primevideo.com": "entertainment",
    "youtube.com": "entertainment",

    # Finance
    "paypal.com": "finance",
    "venmo.com": "finance",
    "chase.com": "finance",
    "bankofamerica.com": "finance",
    "wellsfargo.com": "finance",
    "americanexpress.com": "finance",
    "discover.com": "finance",
    "capitalone.com": "finance",
    "mint.com": "finance",

    # Shopping
    "amazon.com": "shopping",
    "ebay.com": "shopping",
    "etsy.com": "shopping",
    "shopify.com": "shopping",
    "target.com": "shopping",
    "walmart.com": "shopping",

    # Tech/SaaS
    "github.com": "tech",
    "gitlab.com": "tech",
    "atlassian.com": "tech",
    "slack.com": "tech",
    "notion.so": "tech",
    "figma.com": "tech",
    "dropbox.com": "tech",
    "google.com": "tech",
    "microsoft.com": "tech",

    # News
    "nytimes.com": "news",
    "wsj.com": "news",
    "washingtonpost.com": "news",
    "medium.com": "news",
    "substack.com": "news",

    # Health
    "headspace.com": "health",
    "calm.com": "health",
    "peloton.com": "health",
    "myfitnesspal.com": "health",
}

# Keywords indicating transactional emails
TRANSACTIONAL_KEYWORDS = {
    "receipt", "invoice", "order confirmation", "shipping", "delivered",
    "payment", "charged", "subscription", "renewal", "billing",
    "your order", "order status", "tracking", "shipment",
}

# Keywords indicating marketing emails
MARKETING_KEYWORDS = {
    "sale", "discount", "offer", "deal", "promo", "limited time",
    "don't miss", "exclusive", "save", "off", "free", "new arrival",
    "flash sale", "clearance",
}


class SubscriptionDetector:
    """
    Analyzes email patterns to detect subscriptions and recurring emails.

    Uses multiple signals:
    1. List-Unsubscribe header (strongest signal)
    2. Sender frequency and regularity
    3. Subject pattern matching
    4. Domain classification
    """

    def __init__(self, min_occurrences: int = 2, lookback_days: int = 90):
        self.min_occurrences = min_occurrences
        self.lookback_days = lookback_days

    def detect(self, events: List[EmailEvent]) -> List[SubscriptionSignal]:
        """
        Detect subscriptions from email events.

        Args:
            events: List of normalized email events

        Returns:
            List of detected subscription signals
        """
        if not events:
            return []

        # Filter to lookback period
        cutoff = datetime.now(timezone.utc) - timedelta(days=self.lookback_days)
        recent_events = [e for e in events if e.timestamp >= cutoff]

        # Group by sender domain
        by_domain: Dict[str, List[EmailEvent]] = defaultdict(list)
        for event in recent_events:
            domain = event.sender.domain.lower()
            if domain:
                by_domain[domain].append(event)

        signals = []

        for domain, domain_events in by_domain.items():
            # Skip if too few emails
            if len(domain_events) < self.min_occurrences:
                continue

            # Analyze this sender
            signal = self._analyze_sender(domain, domain_events)
            if signal:
                signals.append(signal)

        # Sort by confidence
        signals.sort(key=lambda s: s.confidence, reverse=True)

        LOGGER.info("[SubscriptionDetector] Found %d subscriptions", len(signals))
        return signals

    def _analyze_sender(
        self,
        domain: str,
        events: List[EmailEvent],
    ) -> Optional[SubscriptionSignal]:
        """Analyze emails from a single sender domain."""
        if not events:
            return None

        # Check for List-Unsubscribe (strongest signal)
        has_unsubscribe = any(e.headers.list_unsubscribe for e in events)
        unsubscribe_link = None
        for e in events:
            if e.headers.list_unsubscribe:
                unsubscribe_link = e.headers.list_unsubscribe
                break

        # Check for automated headers
        is_automated = any(e.is_automated or e.is_newsletter for e in events)

        # Compute confidence
        confidence = 0.3  # Base confidence

        if has_unsubscribe:
            confidence += 0.4  # Strong signal
        if is_automated:
            confidence += 0.2

        # Detect cadence
        cadence, cadence_confidence = self._detect_cadence(events)
        if cadence:
            confidence += 0.1

        # Classify as transactional or marketing
        is_transactional = self._is_transactional(events)
        is_marketing = self._is_marketing(events)

        # Get category from domain
        category = DOMAIN_CATEGORIES.get(domain)

        # Skip if confidence too low
        if confidence < 0.4 and not has_unsubscribe:
            return None

        # Get sender info from most recent event
        latest = max(events, key=lambda e: e.timestamp)

        return SubscriptionSignal(
            domain=domain,
            sender_email=latest.sender.email,
            sender_name=latest.sender.name,
            cadence=cadence,
            cadence_confidence=cadence_confidence,
            category=category,
            is_transactional=is_transactional,
            is_marketing=is_marketing,
            total_received=len(events),
            has_unsubscribe=has_unsubscribe,
            unsubscribe_link=unsubscribe_link,
            confidence=min(0.99, confidence),
        )

    def _detect_cadence(
        self,
        events: List[EmailEvent],
    ) -> tuple[Optional[str], float]:
        """
        Detect the cadence/frequency of emails.

        Returns:
            Tuple of (cadence_name, confidence)
        """
        if len(events) < 3:
            return None, 0.0

        # Sort by timestamp
        sorted_events = sorted(events, key=lambda e: e.timestamp)

        # Calculate gaps between emails
        gaps_days = []
        for i in range(1, len(sorted_events)):
            gap = (sorted_events[i].timestamp - sorted_events[i-1].timestamp).days
            gaps_days.append(gap)

        if not gaps_days:
            return None, 0.0

        avg_gap = sum(gaps_days) / len(gaps_days)
        variance = sum((g - avg_gap) ** 2 for g in gaps_days) / len(gaps_days)
        std_dev = variance ** 0.5

        # Coefficient of variation (lower = more regular)
        cv = std_dev / avg_gap if avg_gap > 0 else float("inf")

        # Determine cadence
        if avg_gap <= 1.5:
            cadence = "daily"
        elif avg_gap <= 8:
            cadence = "weekly"
        elif avg_gap <= 16:
            cadence = "biweekly"
        elif avg_gap <= 35:
            cadence = "monthly"
        elif avg_gap <= 100:
            cadence = "quarterly"
        elif avg_gap <= 400:
            cadence = "yearly"
        else:
            cadence = "irregular"

        # Confidence based on regularity
        if cv < 0.3:
            confidence = 0.9
        elif cv < 0.5:
            confidence = 0.7
        elif cv < 1.0:
            confidence = 0.5
        else:
            confidence = 0.3
            cadence = "irregular"

        return cadence, confidence

    def _is_transactional(self, events: List[EmailEvent]) -> bool:
        """Check if emails are transactional (receipts, shipping, etc.)."""
        transactional_count = 0

        for event in events[:10]:  # Check recent emails
            subject_lower = event.subject.lower()
            if any(kw in subject_lower for kw in TRANSACTIONAL_KEYWORDS):
                transactional_count += 1

        return transactional_count > len(events[:10]) * 0.5

    def _is_marketing(self, events: List[EmailEvent]) -> bool:
        """Check if emails are marketing/promotional."""
        marketing_count = 0

        for event in events[:10]:  # Check recent emails
            subject_lower = event.subject.lower()
            if any(kw in subject_lower for kw in MARKETING_KEYWORDS):
                marketing_count += 1

        return marketing_count > len(events[:10]) * 0.3


async def detect_subscriptions(
    events: List[EmailEvent],
    *,
    min_occurrences: int = 2,
    lookback_days: int = 90,
) -> List[SubscriptionSignal]:
    """
    Detect subscriptions from email events.

    Args:
        events: List of normalized email events
        min_occurrences: Minimum emails to consider a subscription
        lookback_days: How far back to analyze

    Returns:
        List of detected subscription signals
    """
    detector = SubscriptionDetector(
        min_occurrences=min_occurrences,
        lookback_days=lookback_days,
    )
    return detector.detect(events)


__all__ = ["detect_subscriptions", "SubscriptionDetector"]
