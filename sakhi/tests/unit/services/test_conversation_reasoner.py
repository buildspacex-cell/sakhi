"""
Unit tests for conversation_reasoner — build_prompt() MVP prompt structure.

Tests that the stripped-down MVP prompt contains only:
Voice, lean response guidance, hidden continuity context, governance, and user message.
"""

import pytest

from sakhi.apps.api.services.conversation_v2.conversation_reasoner import (
    build_prompt,
    build_context_scan,
)


# =============================================================================
# Helpers
# =============================================================================


def _base_context():
    return {
        "short_term": {"texts": ["I'm feeling scattered today"]},
        "themes": [{"theme": "stress"}],
        "continuity": {"clarity_level": 0.5},
        "conversation": {"last_emotion": "anxious", "energy_level": 0.4},
        "persona_mode": "Reflective",
    }


def _base_tone():
    return {
        "style": "warm and reflective",
        "pace": "balanced",
        "concise": False,
        "micro": {},
        "mirroring": {},
        "ritual": {},
        "empathy": {},
        "stability": {},
    }


# =============================================================================
# Base Prompt Structure
# =============================================================================


class TestBasePromptStructure:
    """Tests that MVP prompt structure is correct."""

    def test_prompt_contains_persona(self):
        result = build_prompt("Hello", _base_context(), _base_tone())
        assert "Sakhi" in result
        assert "thinking partner" in result

    def test_prompt_contains_user_message(self):
        result = build_prompt("How are you?", _base_context(), _base_tone())
        assert "How are you?" in result

    def test_prompt_contains_emotion_state(self):
        result = build_prompt("Hello", _base_context(), _base_tone())
        assert "anxious" in result

    def test_prompt_uses_response_contract(self):
        result = build_prompt("Need help prioritizing work this week.", _base_context(), _base_tone())
        assert "40-80 words" in result
        assert "Lead with the thing that matters." in result
        assert "Max 1 question." in result

    def test_prompt_contains_voice_directive(self):
        result = build_prompt("Hello", _base_context(), _base_tone())
        assert "Never use Ayurvedic jargon" in result

    def test_prompt_contains_internal_reasoning_block(self):
        result = build_prompt("Hello", _base_context(), _base_tone())
        assert "[INTERNAL REASONING — DO NOT OUTPUT]" in result
        assert "Do NOT reveal this reasoning." in result

    def test_prompt_contains_response_modes(self):
        result = build_prompt("Hello", _base_context(), _base_tone())
        assert "[RESPONSE MODE — INTERNAL ONLY]" in result
        assert "Default to resolve or confront" in result
        assert "Never ask more than 1 question" in result

    def test_cut_blocks_absent(self):
        """Blocks cut in MVP should NOT appear in prompt."""
        metadata = {
            "email_context": "Email patterns: 3 threads pending",
            "causal_explanation": {"dosha_context": "Vata elevated", "explanation_text": "Test"},
            "personalized_recommendations": {"foods": [{"name": "ginger"}]},
            "recommendation_trigger": "reactive",
            "scheduling_context": {"intent": "query"},
            "operating_system": "Conservation",
            "active_modules": ["identity", "emotional_depth"],
            "narrative_trace": {"dominant_theme": "career"},
            "vision_context": {"current_image": {"description": "test image"}},
        }
        result = build_prompt("Hello", _base_context(), _base_tone(), metadata=metadata)
        assert "EMAIL INTELLIGENCE" not in result
        assert "WHY YOU MIGHT BE FEELING THIS WAY" not in result
        assert "Personalized Recommendations" not in result
        assert "SCHEDULING" not in result
        assert "Operating System" not in result
        assert "IDENTITY & GROWTH" not in result
        assert "EMOTIONAL ATTUNEMENT" not in result
        assert "VISUAL CONTEXT" not in result
        assert "Additional context:" not in result
        assert "Behavior cues:" not in result

    def test_governance_section_present_when_provided(self):
        metadata = {"governance_guard": "[GOVERNANCE] Do not suggest supplements."}
        result = build_prompt("Hello", _base_context(), _base_tone(), metadata=metadata)
        assert "GOVERNANCE" in result
        assert "Do not suggest supplements" in result

    def test_governance_absent_when_empty(self):
        result = build_prompt("Hello", _base_context(), _base_tone(), metadata={})
        assert "GOVERNANCE" not in result


class TestContinuityContextSection:
    """Tests for hidden continuity context injection."""

    def test_continuity_pack_adds_hidden_context(self):
        metadata = {
            "continuity_pack": {
                "topic_key": "sakhi",
                "topic_label": "Sakhi",
                "arc_compact": {
                    "start_signal": "started around ayurveda engine",
                    "pivots_signal": "2 pivots reorganized the thread",
                    "current_signal": "currently centered on product shape",
                    "disclaimer": "Direction is consistency over time, not success.",
                },
                "history_compact": {
                    "span_days": 98.4,
                    "element_count": 30,
                    "phase_count": 3,
                    "qualitative_arc_summary": (
                        "It started around ayurveda engine, moved through two pivots, "
                        "and is now centered on deterministic core."
                    ),
                    "phase_path": [
                        "2025-11-26->2026-01-08: ayurveda engine (10 moments)",
                        "2026-01-11->2026-03-02: validation (10 moments)",
                        "2026-03-03->2026-03-05: deterministic core (10 moments)",
                    ],
                    "anchor_points": [
                        {"ts": "2025-11-26T08:00:00+00:00", "snippet": "Started with ayurveda intent."},
                        {"ts": "2026-01-19T08:00:00+00:00", "snippet": "Moved from validation to building."},
                        {"ts": "2026-03-05T08:00:00+00:00", "snippet": "Centered on deterministic core."},
                    ],
                    "decision_ledger": [
                        {
                            "ts": "2026-01-19T08:00:00+00:00",
                            "status": "resolved",
                            "source": "user_journal",
                            "decision": "resolved direction",
                        },
                    ],
                },
                "evidence": [
                    {"ts": "2026-01-01T08:00:00+00:00", "snippet": "Ayurveda still feels central."},
                    {"ts": "2026-02-01T08:00:00+00:00", "snippet": "The prototype still feels reactive."},
                ],
            }
        }

        result = build_prompt("Does this still make sense?", _base_context(), _base_tone(), metadata=metadata)

        assert "LONGITUDINAL CONTINUITY" in result
        assert "Topic: Sakhi" in result
        assert "Where it began: started around ayurveda engine" in result
        assert "Decision ledger:" in result
        assert "Story flow:" in result
        assert "First: ayurveda engine" in result
        assert "Now: deterministic core" in result
        assert "2025-11-26->2026-01-08" not in result
        assert "Anchor moments:" in result
        assert "Does this still make sense?" in result
        assert "Use history as grounding, not as a detour." not in result

    def test_no_continuity_when_absent(self):
        result = build_prompt("Hello", _base_context(), _base_tone(), metadata={})
        assert "LONGITUDINAL CONTINUITY" not in result


# =============================================================================
# Context Scan (MVP: emotion + friction only)
# =============================================================================


class TestContextScan:
    """Tests for the MVP context scan (emotion + friction only)."""

    def test_scan_with_emotional_data(self):
        metadata = {
            "empathy_state": {"pattern": "mirror-first"},
            "microreg_state": {"shift": "grounding", "amplitude": 0.6, "risk": "low"},
        }
        scan = build_context_scan(metadata)
        assert "Emotional:" in scan
        assert "empathy=mirror-first" in scan
        assert "microreg=grounding" in scan

    def test_scan_with_friction_data(self):
        metadata = {
            "friction_state": {"state": "Mild Friction", "drift_percentage": 18.5},
        }
        scan = build_context_scan(metadata)
        assert "Friction: Mild Friction" in scan
        assert "drift=18%" in scan

    def test_scan_empty_metadata(self):
        scan = build_context_scan({})
        assert scan == ""

    def test_cut_modules_absent_from_scan(self):
        """Identity, Moment, Micro, Body should NOT appear in MVP scan."""
        metadata = {
            "identity_momentum_frame": {"momentum_direction": "building", "momentum_score": 0.7},
            "moment_model": {"recommended_companion_mode": "supportive"},
            "focus_path": {"anchor_step": "review"},
            "body_state": {"sleep": {"quality": "good", "duration_hours": 7.2}},
        }
        scan = build_context_scan(metadata)
        assert "Identity:" not in scan
        assert "Moment:" not in scan
        assert "Micro:" not in scan
        assert "Body:" not in scan
        assert scan == ""  # None of the MVP modules have data

    def test_scan_in_build_prompt(self):
        metadata = {
            "empathy_state": {"pattern": "mirror-first"},
            "friction_state": {"state": "Balanced", "drift_percentage": 5},
        }
        result = build_prompt("Hello", _base_context(), _base_tone(), metadata=metadata)
        assert "CONTEXT — background intelligence" not in result
        assert "empathy=mirror-first" not in result
        assert "Friction: Balanced" not in result


# =============================================================================
# Conversation Context
# =============================================================================


class TestConversationContext:
    """Tests that build_prompt stays focused on the base system prompt only."""

    def test_short_term_texts_do_not_appear(self):
        ctx = _base_context()
        ctx["short_term"] = {"texts": ["First message", "Second message", "Third message"]}
        result = build_prompt("Hello", ctx, _base_tone())
        assert "Recent conversation:" not in result
        assert "First message" not in result
        assert "Third message" not in result

    def test_prompt_ends_with_user_message(self):
        result = build_prompt("Hello", _base_context(), _base_tone())
        assert "User message:\nHello" in result


# =============================================================================
# Session Anchor (first-message behavior)
# =============================================================================


class TestSessionAnchor:
    """Tests for first-message anchoring — new user vs returning user."""

    def test_no_anchor_mid_conversation(self):
        metadata = {
            "conversation_history": [{"role": "user", "text": "previous message"}],
            "total_turns": 1,
        }
        result = build_prompt("Hello", _base_context(), _base_tone(), metadata=metadata)
        assert "FIRST MESSAGE" not in result

    def test_new_user_anchor_when_no_history_no_continuity(self):
        metadata = {"conversation_history": [], "total_turns": 0}
        result = build_prompt("Hello", _base_context(), _base_tone(), metadata=metadata)
        assert "FIRST MESSAGE — NEW USER" in result
        assert "What are you trying to work out" in result

    def test_returning_user_anchor_when_open_decisions_present(self):
        metadata = {
            "conversation_history": [],
            "total_turns": 0,
            "continuity_pack": {
                "topic_key": "career",
                "topic_label": "Career",
                "history_compact": {
                    "decision_ledger": [
                        {"decision": "whether to take the new role", "status": "open", "source": "user"},
                    ],
                },
            },
        }
        result = build_prompt("Hello", _base_context(), _base_tone(), metadata=metadata)
        assert "FIRST MESSAGE — RETURNING USER" in result
        assert "whether to take the new role" in result

    def test_returning_user_skips_resolved_decisions(self):
        metadata = {
            "conversation_history": [],
            "total_turns": 0,
            "continuity_pack": {
                "topic_key": "career",
                "history_compact": {
                    "decision_ledger": [
                        {"decision": "took the role", "status": "resolved", "source": "user"},
                    ],
                },
            },
        }
        result = build_prompt("Hello", _base_context(), _base_tone(), metadata=metadata)
        # All decisions resolved → treated as new user
        assert "FIRST MESSAGE — NEW USER" in result

    def test_no_anchor_when_total_turns_nonzero(self):
        metadata = {
            "conversation_history": [],
            "total_turns": 3,
        }
        result = build_prompt("Hello", _base_context(), _base_tone(), metadata=metadata)
        assert "FIRST MESSAGE" not in result
