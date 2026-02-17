"""
Unit tests for context_router — deterministic classifier + module routing.

Tests that the correct context modules are activated based on user message,
intents, time-of-day, and other signals.
"""

import pytest
from unittest.mock import AsyncMock, patch

from sakhi.apps.api.services.context_router import (
    classify_context_needs,
    route_context,
    CONTEXT_MODULES,
    ALL_MODULES,
    MODULE_REGISTRY,
    INTENT_POLICY,
    map_triage_to_intents,
    load_recent_intent_evolution,
)


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
        """reflect keyword now maps to emotional_depth instead of removed reflection module."""
        modules, conf = classify_context_needs("How was my day? Let me reflect")
        # "reflection" module removed; reflect keyword activates no keyword-based module
        # (the _REFLECTION_KEYWORDS table was removed)
        assert "reflection" not in modules

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
    """Tests for time-of-day module activation (morning/evening rituals removed)."""

    def test_no_morning_ritual(self):
        """morning_ritual module was removed — time-of-day no longer activates it."""
        modules, _ = classify_context_needs("Good morning!", hour=8)
        assert "morning_ritual" not in modules

    def test_no_evening_ritual(self):
        """evening_ritual module was removed — time-of-day no longer activates it."""
        modules, _ = classify_context_needs("Good night", hour=21)
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
        assert len(modules) == 0
        assert conf >= 0.6

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
    """Tests for module definitions and ALL_MODULES."""

    def test_all_expected_modules_defined(self):
        expected = {
            "identity", "emotional_depth", "moment", "recommendations",
            "scheduling", "email", "causal",
            "micro_flow", "vision", "agentic",
            "body",
        }
        assert CONTEXT_MODULES == expected

    def test_module_count(self):
        assert len(CONTEXT_MODULES) == 11

    def test_all_modules_equals_context_modules(self):
        """ALL_MODULES is a frozen copy of CONTEXT_MODULES."""
        assert set(ALL_MODULES) == CONTEXT_MODULES

    def test_all_modules_is_frozenset(self):
        """ALL_MODULES should be immutable."""
        assert isinstance(ALL_MODULES, frozenset)

    def test_registry_keys_match_context_modules(self):
        """MODULE_REGISTRY must define every module in CONTEXT_MODULES."""
        assert set(MODULE_REGISTRY.keys()) == CONTEXT_MODULES

    def test_registry_descriptions_are_nonempty(self):
        """Every module must have a non-empty description."""
        for module, desc in MODULE_REGISTRY.items():
            assert isinstance(desc, str) and len(desc) > 10, (
                f"Module '{module}' has missing or too-short description"
            )

    def test_context_modules_derived_from_registry(self):
        """CONTEXT_MODULES should be derived from MODULE_REGISTRY keys."""
        assert CONTEXT_MODULES == set(MODULE_REGISTRY.keys())


# =============================================================================
# Intent Policy Map Tests
# =============================================================================


class TestIntentPolicyMap:
    """Tests for the declarative INTENT_POLICY dict."""

    def test_policy_keys_all_lowercase(self):
        for key in INTENT_POLICY:
            assert key == key.lower(), f"Policy key '{key}' is not lowercase"

    def test_policy_modules_are_valid(self):
        for key, policy in INTENT_POLICY.items():
            for module in policy["modules"]:
                assert module in CONTEXT_MODULES, (
                    f"Policy '{key}' references unknown module '{module}'"
                )

    def test_body_intent(self):
        modules, _ = classify_context_needs(
            "Tell me more",
            intents=[{"name": "body_check"}],
        )
        assert "body" in modules

    def test_sleep_intent(self):
        modules, _ = classify_context_needs(
            "Help me",
            intents=[{"name": "sleep_quality"}],
        )
        assert "body" in modules

    def test_emotion_intent(self):
        modules, _ = classify_context_needs(
            "Yes",
            intents=[{"name": "emotion_support"}],
        )
        assert "emotional_depth" in modules

    def test_reflect_intent(self):
        modules, _ = classify_context_needs(
            "Let's do it",
            intents=[{"name": "reflect_on_day"}],
        )
        assert "emotional_depth" in modules

    def test_triage_action_intent(self):
        modules, _ = classify_context_needs(
            "Ok",
            intents=[{"name": "action_intent"}],
        )
        assert "micro_flow" in modules

    def test_triage_emotion_reflection_intent(self):
        modules, _ = classify_context_needs(
            "Yes",
            intents=[{"name": "emotion_reflection"}],
        )
        assert "emotional_depth" in modules

    def test_triage_goal_pursuit_intent(self):
        modules, _ = classify_context_needs(
            "Sure",
            intents=[{"name": "goal_pursuit"}],
        )
        assert "micro_flow" in modules
        assert "identity" in modules

    def test_triage_schedule_planning_intent(self):
        modules, _ = classify_context_needs(
            "Do it",
            intents=[{"name": "schedule_planning"}],
        )
        assert "scheduling" in modules

    def test_string_intent_format(self):
        """Intents can be plain strings, not just dicts."""
        modules, _ = classify_context_needs(
            "Sure",
            intents=["schedule_meeting"],
        )
        assert "scheduling" in modules


# =============================================================================
# Triage-to-Intent Mapping Tests
# =============================================================================


class TestTriageToIntents:
    """Tests for map_triage_to_intents()."""

    def test_action_intent_signal(self):
        triage = {"triage": [{"type": "intent_action", "confidence": 0.8}], "slots": {}}
        hints = map_triage_to_intents(triage)
        assert any(h["name"] == "action_intent" for h in hints)

    def test_reflection_signal(self):
        triage = {"triage": [{"type": "reflection_observation", "confidence": 0.7}], "slots": {}}
        hints = map_triage_to_intents(triage)
        assert any(h["name"] == "emotion_reflection" for h in hints)

    def test_finance_signal(self):
        triage = {"triage": [{"type": "finance", "confidence": 0.6}], "slots": {}}
        hints = map_triage_to_intents(triage)
        assert any(h["name"] == "finance_planning" for h in hints)

    def test_goal_slot(self):
        triage = {"triage": [], "slots": {"goal": {"text": "meditation", "confidence": 0.7}}}
        hints = map_triage_to_intents(triage)
        assert any(h["name"] == "goal_pursuit" for h in hints)

    def test_time_window_slot(self):
        triage = {"triage": [], "slots": {"time_window": {"start": "2026-02-17T10:00:00", "confidence": 0.8}}}
        hints = map_triage_to_intents(triage)
        assert any(h["name"] == "schedule_planning" for h in hints)

    def test_mood_affect_slot(self):
        triage = {"triage": [], "slots": {"mood_affect": {"label": "stressed", "score": -0.5}}}
        hints = map_triage_to_intents(triage)
        assert any(h["name"] == "emotion_support" for h in hints)

    def test_empty_triage(self):
        hints = map_triage_to_intents({})
        assert hints == []

    def test_multiple_signals(self):
        triage = {
            "triage": [
                {"type": "intent_action", "confidence": 0.8},
                {"type": "reflection_observation", "confidence": 0.7},
            ],
            "slots": {"mood_affect": {"label": "anxious"}},
        }
        hints = map_triage_to_intents(triage)
        names = {h["name"] for h in hints}
        assert "action_intent" in names
        assert "emotion_reflection" in names
        assert "emotion_support" in names


# =============================================================================
# Intent Evolution Loading Tests
# =============================================================================


class TestIntentEvolutionLoading:
    """Tests for load_recent_intent_evolution()."""

    @pytest.mark.asyncio
    async def test_returns_intents_from_db(self):
        mock_rows = [
            {"intent_name": "meditation", "strength": 0.8, "trend": "up"},
            {"intent_name": "schedule_meeting", "strength": 0.5, "trend": "stable"},
        ]
        with patch("sakhi.apps.api.core.db.q", new_callable=AsyncMock, return_value=mock_rows):
            result = await load_recent_intent_evolution("test-user-id")
        assert len(result) == 2
        assert result[0]["name"] == "meditation"
        assert result[1]["name"] == "schedule_meeting"

    @pytest.mark.asyncio
    async def test_returns_empty_on_db_error(self):
        with patch("sakhi.apps.api.core.db.q", new_callable=AsyncMock, side_effect=Exception("DB error")):
            result = await load_recent_intent_evolution("test-user-id")
        assert result == []

    @pytest.mark.asyncio
    async def test_returns_empty_when_no_rows(self):
        with patch("sakhi.apps.api.core.db.q", new_callable=AsyncMock, return_value=[]):
            result = await load_recent_intent_evolution("test-user-id")
        assert result == []
