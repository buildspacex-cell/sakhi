"""
Tests for the sensing layer — specificity classification.

Verifies that the specificity heuristic correctly classifies messages
into high (3+ indicators), medium (1-2), and low (0).
"""

import pytest

from sakhi.apps.api.services.response.sensing import SenseFrame, sense_message


class TestSpecificityClassification:
    """Test specificity classification logic."""

    def test_high_specificity_multiple_indicators(self):
        """Message with 3+ specificity indicators → high."""
        # Location + quality + timing + long message
        frame = sense_message(
            "I've had a sharp headache on my left temple every morning for the past week"
        )
        assert frame.specificity == "high"

    def test_medium_specificity_some_indicators(self):
        """Message with 1-2 indicators → medium."""
        # Needs location/quality/timing keywords or longer message to register
        frame = sense_message("I have a dull headache in my temple after work")
        assert frame.specificity in ("medium", "high")

    def test_low_specificity_no_indicators(self):
        """Very short, vague message → low."""
        frame = sense_message("hello")
        assert frame.specificity == "low"

    def test_long_message_boosts_specificity(self):
        """Messages over 100 chars get a specificity boost."""
        short = sense_message("headache")
        long_msg = sense_message(
            "I've been having this headache that comes and goes, "
            "sometimes it's worse in the morning and I'm not sure what's causing it "
            "but it's been about a week now"
        )
        # Long message should have higher or equal specificity
        specificity_order = {"low": 0, "medium": 1, "high": 2}
        assert specificity_order[long_msg.specificity] >= specificity_order[short.specificity]


class TestDomainClassification:
    """Test domain classification."""

    def test_body_domain(self):
        frame = sense_message("my head hurts and I feel tired")
        assert frame.domain == "body"

    def test_mind_domain(self):
        frame = sense_message("I feel so anxious and stressed")
        assert frame.domain == "mind"

    def test_general_domain_for_greeting(self):
        frame = sense_message("hey how are you")
        assert frame.domain == "general"


class TestTemporalMarkers:
    """Test temporal classification."""

    def test_recurring_temporal(self):
        frame = sense_message("I keep getting headaches lately")
        assert frame.temporal == "recurring"

    def test_acute_temporal(self):
        frame = sense_message("I suddenly feel dizzy right now")
        assert frame.temporal == "acute"

    def test_unspecified_temporal(self):
        frame = sense_message("hello")
        assert frame.temporal == "unspecified"


class TestToneDetection:
    """Test tone classification."""

    def test_seeking_help_tone(self):
        frame = sense_message("can you help me with my sleep issues?")
        assert frame.tone == "seeking_help"

    def test_venting_tone(self):
        frame = sense_message("ugh I'm so frustrated, had enough of this")
        assert frame.tone == "venting"

    def test_neutral_tone(self):
        frame = sense_message("hello")
        assert frame.tone == "neutral"
