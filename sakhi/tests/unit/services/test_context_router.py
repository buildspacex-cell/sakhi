"""
Unit tests for context_router — deterministic classifier + module routing.

Tests that the correct context modules are activated based on user message,
intents, time-of-day, and other signals.
"""

import pytest

from sakhi.apps.api.services.context_router import classify_context_needs, CONTEXT_MODULES


# =============================================================================
# Keyword Routing Tests
# =============================================================================


class TestKeywordRouting:
    """Tests for keyword-based module activation."""

    def test_email_keywords(self):
        modules, conf = classify_context_needs("How's my inbox today?")
        assert "email" in modules
        assert conf >= 0.9

    def test_scheduling_keywords(self):
        modules, conf = classify_context_needs("Can you schedule a meeting for tomorrow?")
        assert "scheduling" in modules
        assert conf >= 0.9

    def test_causal_patterns(self):
        modules, conf = classify_context_needs("Why am I feeling so scattered?")
        assert "causal" in modules
        assert conf >= 0.9

    def test_identity_keywords(self):
        modules, conf = classify_context_needs("Who am I becoming?")
        assert "identity" in modules
        assert conf >= 0.8

    def test_emotional_depth_keywords(self):
        modules, conf = classify_context_needs("I'm feeling overwhelmed and scared")
        assert "emotional_depth" in modules
        assert conf >= 0.8

    def test_moment_keywords(self):
        modules, conf = classify_context_needs("Should I take this job offer?")
        assert "moment" in modules
        assert conf >= 0.8

    def test_micro_flow_keywords(self):
        modules, conf = classify_context_needs("Help me focus on my work")
        assert "micro_flow" in modules
        assert conf >= 0.7

    def test_recommendation_keywords(self):
        modules, conf = classify_context_needs("What should I do to feel better?")
        assert "recommendations" in modules
        assert conf >= 0.8

    def test_reflection_keywords(self):
        modules, conf = classify_context_needs("How was my day? Let me reflect")
        assert "reflection" in modules
        assert conf >= 0.8

    def test_agentic_keywords(self):
        modules, conf = classify_context_needs("Can you search for vegan restaurants nearby?")
        assert "agentic" in modules
        assert conf >= 0.8

    def test_body_sleep_keywords(self):
        modules, conf = classify_context_needs("I slept poorly last night")
        assert "body" in modules
        assert conf >= 0.7

    def test_body_energy_keywords(self):
        modules, conf = classify_context_needs("I'm feeling very tired and exhausted")
        assert "body" in modules
        assert conf >= 0.7

    def test_body_heart_rate_keywords(self):
        modules, conf = classify_context_needs("My heart rate has been high lately")
        assert "body" in modules
        assert conf >= 0.7

    def test_body_exercise_keywords(self):
        modules, conf = classify_context_needs("I went for a run and did some exercise")
        assert "body" in modules
        assert conf >= 0.7


# =============================================================================
# Time-Based Routing Tests
# =============================================================================


class TestTimeBasedRouting:
    """Tests for time-of-day module activation."""

    def test_morning_ritual_early(self):
        modules, _ = classify_context_needs("Good morning!", hour=8)
        assert "morning_ritual" in modules

    def test_morning_ritual_boundary(self):
        modules, _ = classify_context_needs("Hello", hour=11)
        assert "morning_ritual" in modules

    def test_no_morning_afternoon(self):
        modules, _ = classify_context_needs("Hello", hour=14)
        assert "morning_ritual" not in modules

    def test_evening_ritual(self):
        modules, _ = classify_context_needs("Good night", hour=21)
        assert "evening_ritual" in modules

    def test_no_evening_afternoon(self):
        modules, _ = classify_context_needs("Hello", hour=15)
        assert "evening_ritual" not in modules


# =============================================================================
# Structural Trigger Tests
# =============================================================================


class TestStructuralTriggers:
    """Tests for image and task-based triggers."""

    def test_vision_with_image(self):
        modules, conf = classify_context_needs("What's this?", has_image=True)
        assert "vision" in modules
        assert conf >= 0.9

    def test_agentic_with_pending_task(self):
        modules, conf = classify_context_needs("Continue with that", has_pending_task=True)
        assert "agentic" in modules
        assert conf >= 0.8


# =============================================================================
# Intent-Based Routing Tests
# =============================================================================


class TestIntentRouting:
    """Tests for intent-based module activation."""

    def test_schedule_intent(self):
        modules, _ = classify_context_needs(
            "Let's do it",
            intents=[{"name": "schedule_meeting"}],
        )
        assert "scheduling" in modules

    def test_email_intent(self):
        modules, _ = classify_context_needs(
            "Show me",
            intents=[{"name": "check_inbox"}],
        )
        assert "email" in modules

    def test_health_intent(self):
        modules, _ = classify_context_needs(
            "Help me",
            intents=[{"name": "ayurvedic_advice"}],
        )
        assert "recommendations" in modules
        assert "causal" in modules

    def test_identity_intent(self):
        modules, _ = classify_context_needs(
            "Tell me more",
            intents=[{"name": "identity_exploration"}],
        )
        assert "identity" in modules


# =============================================================================
# Confidence & Fallback Tests
# =============================================================================


class TestConfidenceFallback:
    """Tests for confidence levels and LLM fallback triggers."""

    def test_short_greeting_high_confidence(self):
        modules, conf = classify_context_needs("Hey")
        assert len(modules) == 0 or all(m in ("morning_ritual", "evening_ritual") for m in modules)
        assert conf >= 0.6  # Time-based modules may be present

    def test_short_greeting_no_keyword_modules(self):
        modules, conf = classify_context_needs("Hey", hour=14)
        assert len(modules) == 0
        assert conf >= 0.8

    def test_ambiguous_long_message_low_confidence(self):
        modules, conf = classify_context_needs(
            "I've been thinking a lot about things lately and I'm not sure what to make of it all"
        )
        assert conf < 0.5  # Should trigger LLM fallback

    def test_empty_text(self):
        modules, conf = classify_context_needs("")
        assert len(modules) == 0
        assert conf >= 0.8


# =============================================================================
# Combined Module Tests
# =============================================================================


class TestCombinedModules:
    """Tests for messages that activate multiple modules."""

    def test_causal_and_recommendations(self):
        modules, _ = classify_context_needs("Why am I feeling off? What should I do?")
        assert "causal" in modules
        assert "recommendations" in modules

    def test_email_and_scheduling(self):
        modules, _ = classify_context_needs("Check my email and schedule a meeting")
        assert "email" in modules
        assert "scheduling" in modules

    def test_morning_and_focus(self):
        modules, _ = classify_context_needs("Help me focus on my work this morning", hour=8)
        assert "micro_flow" in modules
        assert "morning_ritual" in modules

    def test_identity_and_emotional(self):
        modules, _ = classify_context_needs("I feel lost and don't know who I am anymore")
        assert "emotional_depth" in modules
        assert "identity" in modules

    def test_moment_and_identity(self):
        modules, _ = classify_context_needs("Should I change careers? Who am I becoming?")
        assert "moment" in modules
        assert "identity" in modules


# =============================================================================
# Module Registry Test
# =============================================================================


class TestModuleRegistry:
    """Tests for module definitions."""

    def test_all_expected_modules_defined(self):
        expected = {
            "identity", "emotional_depth", "moment", "recommendations",
            "scheduling", "email", "causal", "morning_ritual",
            "evening_ritual", "micro_flow", "reflection", "vision", "agentic",
            "body",
        }
        assert CONTEXT_MODULES == expected

    def test_module_count(self):
        assert len(CONTEXT_MODULES) == 14
