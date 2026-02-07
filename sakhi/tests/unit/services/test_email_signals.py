"""
Unit tests for email signal extractors.

Tests the deterministic pattern detection algorithms.
"""

from datetime import datetime, timedelta, timezone

from sakhi.apps.api.services.email.models import (
    EmailDirection,
    EmailEvent,
    EmailHeaders,
    EmailProvider,
    EmailSender,
)
from sakhi.apps.api.services.email.signals.avoidance import AvoidanceDetector
from sakhi.apps.api.services.email.signals.boundary import BoundaryDetector
from sakhi.apps.api.services.email.signals.cognitive_load import CognitiveLoadAnalyzer
from sakhi.apps.api.services.email.signals.subscription import SubscriptionDetector

# =============================================================================
# Test Fixtures
# =============================================================================

def make_event(
    sender_email: str,
    direction: EmailDirection = EmailDirection.INCOMING,
    timestamp: datetime = None,
    thread_id: str = "thread-1",
    has_unsubscribe: bool = False,
    is_newsletter: bool = False,
    subject: str = "Test Subject",
) -> EmailEvent:
    """Create a test email event."""
    if timestamp is None:
        timestamp = datetime.now(timezone.utc)

    domain = sender_email.split("@")[1] if "@" in sender_email else "example.com"

    msg_id = f"msg-{hash(sender_email + str(timestamp))}"

    # Create headers with list_unsubscribe if has_unsubscribe is True
    headers = EmailHeaders(
        list_unsubscribe=f"<mailto:unsubscribe@{domain}>" if has_unsubscribe else None
    )

    return EmailEvent(
        message_id=msg_id,
        provider_message_id=msg_id,
        thread_id=thread_id,
        provider=EmailProvider.GMAIL,
        timestamp=timestamp,
        direction=direction,
        sender=EmailSender(
            email=sender_email,
            name=sender_email.split("@")[0],
            domain=domain,
        ),
        recipients=[],
        subject=subject,
        is_newsletter=is_newsletter,
        headers=headers,
    )


def make_events_from_sender(
    sender_email: str,
    count: int,
    days_apart: int = 7,
    has_unsubscribe: bool = True,
) -> list:
    """Create multiple events from same sender over time."""
    now = datetime.now(timezone.utc)
    events = []
    for i in range(count):
        events.append(make_event(
            sender_email=sender_email,
            timestamp=now - timedelta(days=i * days_apart),
            thread_id=f"thread-{sender_email}-{i}",
            has_unsubscribe=has_unsubscribe,
        ))
    return events


# =============================================================================
# Subscription Detector Tests
# =============================================================================

class TestSubscriptionDetector:
    """Tests for subscription/newsletter detection."""

    def test_detects_recurring_sender(self):
        """Should detect sender with regular emails as subscription."""
        detector = SubscriptionDetector()
        events = make_events_from_sender(
            "newsletter@example.com",
            count=5,
            days_apart=7,
            has_unsubscribe=True,
        )

        subscriptions = detector.detect(events)

        assert len(subscriptions) >= 1
        assert any(s.sender_email == "newsletter@example.com" for s in subscriptions)

    def test_ignores_infrequent_sender(self):
        """Should not flag one-time senders as subscriptions."""
        detector = SubscriptionDetector()
        events = [make_event("onetime@example.com")]

        subscriptions = detector.detect(events)

        assert len(subscriptions) == 0

    def test_detects_unsubscribe_header(self):
        """Emails with List-Unsubscribe header are likely newsletters."""
        detector = SubscriptionDetector()
        events = make_events_from_sender(
            "promo@store.com",
            count=3,
            has_unsubscribe=True,
        )

        subscriptions = detector.detect(events)

        matching = [s for s in subscriptions if s.sender_email == "promo@store.com"]
        assert len(matching) >= 1
        if matching:
            assert matching[0].has_unsubscribe is True

    def test_categorizes_known_domains(self):
        """Should categorize emails from known newsletter domains."""
        detector = SubscriptionDetector()
        events = make_events_from_sender(
            "digest@substack.com",
            count=4,
        )

        subscriptions = detector.detect(events)

        # Substack is a known newsletter platform
        matching = [s for s in subscriptions if "substack" in s.sender_email]
        assert len(matching) >= 1


# =============================================================================
# Avoidance Detector Tests
# =============================================================================

class TestAvoidanceDetector:
    """Tests for email avoidance pattern detection."""

    def test_detects_unreplied_thread(self):
        """Should detect threads awaiting reply."""
        detector = AvoidanceDetector()
        user_email = "user@example.com"
        now = datetime.now(timezone.utc)

        # Thread with incoming email 10 days ago, no reply
        events = [
            make_event(
                sender_email="colleague@work.com",
                direction=EmailDirection.INCOMING,
                timestamp=now - timedelta(days=10),
                thread_id="awaiting-reply",
                subject="Need your input",
            ),
        ]

        avoidance = detector.detect(events, user_email)

        assert len(avoidance) >= 1
        assert avoidance[0].thread_id == "awaiting-reply"
        assert avoidance[0].duration_days >= 7

    def test_ignores_replied_thread(self):
        """Should not flag threads that have been replied to."""
        detector = AvoidanceDetector()
        user_email = "user@example.com"
        now = datetime.now(timezone.utc)

        events = [
            make_event(
                sender_email="colleague@work.com",
                direction=EmailDirection.INCOMING,
                timestamp=now - timedelta(days=10),
                thread_id="replied",
            ),
            make_event(
                sender_email=user_email,
                direction=EmailDirection.OUTGOING,
                timestamp=now - timedelta(days=9),
                thread_id="replied",
            ),
        ]

        avoidance = detector.detect(events, user_email)

        replied_threads = [a for a in avoidance if a.thread_id == "replied"]
        assert len(replied_threads) == 0

    def test_severity_increases_with_duration(self):
        """Longer avoidance should have higher severity."""
        detector = AvoidanceDetector()
        user_email = "user@example.com"
        now = datetime.now(timezone.utc)

        events = [
            make_event(
                sender_email="boss@work.com",
                direction=EmailDirection.INCOMING,
                timestamp=now - timedelta(days=25),
                thread_id="long-wait",
            ),
        ]

        avoidance = detector.detect(events, user_email)

        assert len(avoidance) >= 1
        assert avoidance[0].severity in ("moderate", "significant")


# =============================================================================
# Boundary Detector Tests
# =============================================================================

class TestBoundaryDetector:
    """Tests for work/life boundary erosion detection."""

    def test_detects_after_hours_activity(self):
        """Should detect high after-hours email activity."""
        detector = BoundaryDetector()
        now = datetime.now(timezone.utc)

        # Create events mostly after 6 PM
        events = []
        for i in range(10):
            late_time = now.replace(hour=21, minute=0) - timedelta(days=i)
            events.append(make_event(
                sender_email="work@company.com",
                timestamp=late_time,
                direction=EmailDirection.OUTGOING,
            ))

        signal = detector.detect(events)

        assert signal.after_hours_pct > 0.5
        assert signal.erosion_score > 0

    def test_low_erosion_for_business_hours(self):
        """Normal business hours should have low erosion score."""
        detector = BoundaryDetector()
        now = datetime.now(timezone.utc)

        # Events during business hours (10 AM)
        events = []
        for i in range(10):
            work_time = now.replace(hour=10, minute=0) - timedelta(days=i)
            # Skip weekends
            if work_time.weekday() < 5:
                events.append(make_event(
                    sender_email="work@company.com",
                    timestamp=work_time,
                    direction=EmailDirection.OUTGOING,
                ))

        signal = detector.detect(events)

        assert signal.erosion_score < 0.3

    def test_maps_to_friction_framework(self):
        """High late-night activity should map to chaos friction."""
        detector = BoundaryDetector()
        now = datetime.now(timezone.utc)

        # Create late-night events (after 11 PM)
        events = []
        for i in range(10):
            late_time = now.replace(hour=23, minute=30) - timedelta(days=i)
            events.append(make_event(
                sender_email="work@company.com",
                timestamp=late_time,
                direction=EmailDirection.OUTGOING,
            ))

        signal = detector.detect(events)

        # Late night activity should map to chaos friction (Vata)
        if signal.erosion_score > 0.3:
            assert signal.friction_impact in ("chaos_friction", "intensity_friction")


# =============================================================================
# Cognitive Load Analyzer Tests
# =============================================================================

class TestCognitiveLoadAnalyzer:
    """Tests for cognitive load measurement."""

    def test_counts_active_threads(self):
        """Should count threads with recent activity."""
        analyzer = CognitiveLoadAnalyzer()
        now = datetime.now(timezone.utc)

        events = []
        for i in range(5):
            events.append(make_event(
                sender_email=f"sender{i}@example.com",
                timestamp=now - timedelta(days=1),
                thread_id=f"thread-{i}",
            ))

        signal = analyzer.analyze(events)

        assert signal.active_threads >= 5

    def test_identifies_heavy_threads(self):
        """Should identify threads with many messages."""
        analyzer = CognitiveLoadAnalyzer()
        now = datetime.now(timezone.utc)

        # Create a heavy thread with 15 messages
        events = []
        for i in range(15):
            events.append(make_event(
                sender_email="team@work.com",
                timestamp=now - timedelta(hours=i),
                thread_id="heavy-thread",
            ))

        signal = analyzer.analyze(events)

        assert signal.heavy_threads >= 1

    def test_overwhelm_risk_increases_with_load(self):
        """High load should increase overwhelm risk."""
        analyzer = CognitiveLoadAnalyzer()
        now = datetime.now(timezone.utc)

        # Create many active threads
        events = []
        for i in range(30):
            events.append(make_event(
                sender_email=f"sender{i}@example.com",
                timestamp=now - timedelta(hours=i % 24),
                thread_id=f"thread-{i}",
            ))

        signal = analyzer.analyze(events)

        assert signal.overwhelm_risk in ("moderate", "high")

    def test_low_risk_for_few_threads(self):
        """Few threads should have low overwhelm risk."""
        analyzer = CognitiveLoadAnalyzer()
        now = datetime.now(timezone.utc)

        events = [
            make_event(
                sender_email="friend@example.com",
                timestamp=now - timedelta(days=1),
            ),
        ]

        signal = analyzer.analyze(events)

        assert signal.overwhelm_risk == "low"


# =============================================================================
# Edge Cases
# =============================================================================

class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_events_list(self):
        """All detectors should handle empty event lists."""
        sub_detector = SubscriptionDetector()
        avoid_detector = AvoidanceDetector()
        boundary_detector = BoundaryDetector()
        load_analyzer = CognitiveLoadAnalyzer()

        assert sub_detector.detect([]) == []
        assert avoid_detector.detect([], "user@example.com") == []

        boundary_signal = boundary_detector.detect([])
        assert boundary_signal.erosion_score == 0

        load_signal = load_analyzer.analyze([])
        assert load_signal.active_threads == 0

    def test_handles_missing_fields(self):
        """Should handle events with minimal fields."""
        detector = SubscriptionDetector()

        event = EmailEvent(
            message_id="minimal",
            provider_message_id="minimal",
            thread_id="thread",
            provider=EmailProvider.GMAIL,
            timestamp=datetime.now(timezone.utc),
            direction=EmailDirection.INCOMING,
            sender=EmailSender(email="test@example.com", domain="example.com"),
            recipients=[],
        )

        # Should not raise
        subscriptions = detector.detect([event])
        assert isinstance(subscriptions, list)
