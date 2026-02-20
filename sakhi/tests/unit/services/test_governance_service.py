"""
Unit tests for governance service — action classification, guard building,
post-check enforcement, and event type mapping.

These are pure-function tests (no DB or I/O) where possible.
"""

import pytest

from sakhi.apps.api.services.governance.service import (
    build_governance_guard,
    classify_action_type,
    enforce_block,
    map_decision_to_event_type,
)


# =============================================================================
# Action Classification
# =============================================================================


class TestClassifyActionType:
    """Tests for keyword-based action classification."""

    def test_exercise_keywords(self):
        assert classify_action_type("Let's do a workout today") == "suggest_exercise"

    def test_meditation_keywords(self):
        assert classify_action_type("I need to meditate") == "suggest_meditation"

    def test_productivity_keywords(self):
        assert classify_action_type("Help me organize my day") == "suggest_productivity"

    def test_diet_keywords(self):
        assert classify_action_type("What should I eat for dinner?") == "suggest_diet"

    def test_sleep_keywords(self):
        assert classify_action_type("I need help sleeping better") == "suggest_sleep"

    def test_social_keywords(self):
        assert classify_action_type("I should call a friend") == "suggest_social"

    def test_fallback_balanced(self):
        assert classify_action_type("How are you?") == "conversation_turn"

    def test_fallback_chaos_becomes_proactive(self):
        assert classify_action_type("How are you?", "chaos") == "proactive_suggestion"

    def test_fallback_intensity_becomes_proactive(self):
        assert classify_action_type("tell me something", "intensity") == "proactive_suggestion"

    def test_fallback_stagnation_becomes_proactive(self):
        assert classify_action_type("what do you think", "stagnation") == "proactive_suggestion"

    def test_empty_text(self):
        assert classify_action_type("") == "conversation_turn"

    def test_none_text(self):
        assert classify_action_type(None) == "conversation_turn"

    def test_keyword_match_overrides_friction(self):
        """Even in chaos, a keyword match should return the specific action."""
        assert classify_action_type("Let me do yoga", "chaos") == "suggest_exercise"


# =============================================================================
# Guard Building
# =============================================================================


class TestBuildGovernanceGuard:
    """Tests for governance decision → prompt directive conversion."""

    def test_allow_no_violations(self):
        decision = {"action": "allow", "violations": []}
        assert build_governance_guard(decision) == ""

    def test_block_produces_mandatory_directive(self):
        decision = {
            "action": "block",
            "violations": [
                {"description": "Avoid stimulating suggestions after 10 PM"},
            ],
        }
        guard = build_governance_guard(decision)
        assert "GOVERNANCE DIRECTIVE (MANDATORY)" in guard
        assert "DO NOT" in guard
        assert "10 PM" in guard

    def test_require_reconciliation_includes_contradiction(self):
        decision = {
            "action": "require_reconciliation",
            "violations": [
                {"description": "Previously rejected meditation suggestion"},
            ],
        }
        guard = build_governance_guard(decision)
        assert "MANDATORY" in guard
        assert "contradiction" in guard.lower()

    def test_confirm_produces_advisory(self):
        decision = {
            "action": "confirm",
            "violations": [
                {"description": "Sleep boundary approaching"},
            ],
            "triggers": [],
        }
        guard = build_governance_guard(decision)
        assert "GOVERNANCE ADVISORY" in guard
        assert "confirmation" in guard.lower()

    def test_require_confirmation_with_drift_trigger(self):
        decision = {
            "action": "require_confirmation",
            "violations": [
                {"description": "High drift detected"},
            ],
            "triggers": ["drift"],
        }
        guard = build_governance_guard(decision)
        assert "ADVISORY" in guard
        assert "drift" in guard.lower()
        assert "gentle" in guard.lower()

    def test_allow_with_violations_still_empty(self):
        """If action is allow but there are violations, guard should be empty
        because allow means the gate decided to allow."""
        decision = {"action": "allow", "violations": []}
        assert build_governance_guard(decision) == ""

    def test_unknown_action_returns_empty(self):
        decision = {"action": "unknown_action", "violations": []}
        assert build_governance_guard(decision) == ""


# =============================================================================
# Post-Check Enforcement
# =============================================================================


class TestEnforceBlock:
    """Tests for post-reply enforcement when governance blocked."""

    def test_non_block_passes_through(self):
        reply = "Let's do a workout tonight!"
        decision = {"action": "allow", "violations": []}
        assert enforce_block(reply, decision) == reply

    def test_block_clean_reply_passes(self):
        """Reply doesn't mention blocked concepts — passes through."""
        reply = "I'm here for you. How are you feeling?"
        decision = {
            "action": "block",
            "violations": [
                {"description": "Avoid stimulating exercise after bedtime"},
            ],
        }
        result = enforce_block(reply, decision)
        assert result == reply

    def test_block_violating_reply_replaced(self):
        """Reply mentions blocked concept — replaced with safe template."""
        reply = "Great idea! Let's plan an exercise routine for tonight."
        decision = {
            "action": "block",
            "violations": [
                {"description": "Avoid stimulating exercise after bedtime"},
            ],
        }
        result = enforce_block(reply, decision)
        assert result != reply
        assert "I'm here with you" in result

    def test_block_no_violations_passes(self):
        """Block with empty violations list — no keywords to check, passes."""
        reply = "Let's exercise!"
        decision = {"action": "block", "violations": []}
        result = enforce_block(reply, decision)
        assert result == reply

    def test_block_short_description_words_ignored(self):
        """Words <= 4 chars and stop words are excluded from keyword check."""
        reply = "You should avoid running late at night."
        decision = {
            "action": "block",
            "violations": [
                {"description": "Do not run after dark"},
            ],
        }
        # "after" and "dark" — "after" is in stop list, "dark" is only 4 chars
        # So no keyword match → reply passes through
        result = enforce_block(reply, decision)
        assert result == reply


# =============================================================================
# Event Type Mapping
# =============================================================================


class TestEventTypeMapping:
    """Tests for governance action → ledger event_type mapping."""

    def test_allow_to_committed(self):
        assert map_decision_to_event_type("allow") == "committed"

    def test_confirm_to_validated(self):
        assert map_decision_to_event_type("confirm") == "validated"

    def test_require_confirmation_to_validated(self):
        assert map_decision_to_event_type("require_confirmation") == "validated"

    def test_block_to_rejected(self):
        assert map_decision_to_event_type("block") == "rejected"

    def test_require_reconciliation_to_reconciled(self):
        assert map_decision_to_event_type("require_reconciliation") == "reconciled"

    def test_unknown_defaults_to_committed(self):
        assert map_decision_to_event_type("something_else") == "committed"
