"""
Tests for response strategy selection.

Covers:
- Decision tree: RESPOND / CONNECT_AND_INQUIRE / INQUIRE mode selection
- P0 fix: medium specificity + strong knowledge → RESPOND
- Urgency escalation adjustments
- Tone adjustments
"""

import pytest

from sakhi.apps.api.services.response.knowledge_gap import (
    ConstitutionContext,
    DiagnosticQuestion,
    Inference,
    KnowledgeGap,
    KnownFact,
)
from sakhi.apps.api.services.response.sensing import SenseFrame
from sakhi.apps.api.services.response.strategy import (
    ResponseMode,
    ResponseStrategy,
    adjust_strategy_for_tone,
    adjust_strategy_for_urgency,
    select_response_strategy,
)


# =============================================================================
# Helpers
# =============================================================================

def _sense(specificity="low", urgency="low", tone="neutral", domain="body") -> SenseFrame:
    return SenseFrame(
        domain=domain,
        specificity=specificity,
        urgency=urgency,
        tone=tone,
        raw_text="test message",
    )


def _known(topic: str = "sleep", value: str = "sleeps late") -> KnownFact:
    return KnownFact(
        topic=topic, value=value, source="episodic", recency="recent", confidence=0.8,
    )


def _inference(topic: str = "stress", statement: str = "likely stressed") -> Inference:
    return Inference(
        topic=topic, statement=statement, basis="state_vector", confidence=0.7,
    )


def _question(priority: str = "high", qid: str = "q1") -> DiagnosticQuestion:
    return DiagnosticQuestion(
        id=qid, question="How long?", priority=priority,
        dosha_relevance="vata", why="duration matters",
    )


def _gap(
    known_count: int = 0,
    inference_count: int = 0,
    unknown_high: int = 0,
    unknown_medium: int = 0,
) -> KnowledgeGap:
    known = {f"topic_{i}": _known(f"topic_{i}", f"value_{i}") for i in range(known_count)}
    inferred = {f"inf_{i}": _inference(f"inf_{i}", f"statement_{i}") for i in range(inference_count)}
    unknown = (
        [_question("high", f"hq_{i}") for i in range(unknown_high)]
        + [_question("medium", f"mq_{i}") for i in range(unknown_medium)]
    )
    return KnowledgeGap(
        known=known,
        inferred=inferred,
        unknown=unknown,
        constitution=ConstitutionContext(dominant_dosha="vata"),
    )


# =============================================================================
# Case 1: High specificity + no critical unknowns → RESPOND
# =============================================================================

class TestHighSpecificityRespond:
    def test_high_specificity_no_unknowns(self):
        strategy = select_response_strategy(_sense(specificity="high"), _gap())
        assert strategy.mode == ResponseMode.RESPOND

    def test_high_specificity_with_critical_unknowns_does_not_respond(self):
        strategy = select_response_strategy(
            _sense(specificity="high"),
            _gap(unknown_high=1),
        )
        assert strategy.mode != ResponseMode.RESPOND

    def test_respond_mode_has_no_questions(self):
        strategy = select_response_strategy(_sense(specificity="high"), _gap())
        assert strategy.questions_to_ask == []


# =============================================================================
# Case 1b (P0 fix): Medium specificity + strong knowledge → RESPOND
# =============================================================================

class TestMediumSpecificityStrongKnowledge:
    def test_medium_specificity_2_known_yields_respond(self):
        strategy = select_response_strategy(
            _sense(specificity="medium"),
            _gap(known_count=2),
        )
        assert strategy.mode == ResponseMode.RESPOND

    def test_medium_specificity_2_inferences_yields_respond(self):
        strategy = select_response_strategy(
            _sense(specificity="medium"),
            _gap(inference_count=2),
        )
        assert strategy.mode == ResponseMode.RESPOND

    def test_medium_specificity_3_known_yields_respond(self):
        strategy = select_response_strategy(
            _sense(specificity="medium"),
            _gap(known_count=3),
        )
        assert strategy.mode == ResponseMode.RESPOND

    def test_medium_specificity_1_known_does_not_respond(self):
        """1 known + 0 inferred is not enough for Case 1b — falls to CONNECT_AND_INQUIRE."""
        strategy = select_response_strategy(
            _sense(specificity="medium"),
            _gap(known_count=1),
        )
        assert strategy.mode == ResponseMode.CONNECT_AND_INQUIRE

    def test_medium_specificity_with_critical_unknowns_does_not_respond(self):
        """Even with strong knowledge, critical unknowns block Case 1b."""
        strategy = select_response_strategy(
            _sense(specificity="medium"),
            _gap(known_count=3, unknown_high=1),
        )
        assert strategy.mode != ResponseMode.RESPOND

    def test_new_user_no_knowledge_does_not_respond(self):
        """New users (no known, no inferred) should NOT get RESPOND — they need assessment."""
        strategy = select_response_strategy(
            _sense(specificity="medium"),
            _gap(known_count=0, inference_count=0),
        )
        assert strategy.mode != ResponseMode.RESPOND

    def test_reasoning_mentions_medium_detail(self):
        strategy = select_response_strategy(
            _sense(specificity="medium"),
            _gap(known_count=2),
        )
        assert "Medium detail" in strategy.reasoning


# =============================================================================
# Case 2: Known facts → CONNECT_AND_INQUIRE
# =============================================================================

class TestConnectAndInquire:
    def test_known_facts_trigger_connect(self):
        strategy = select_response_strategy(
            _sense(specificity="low"),
            _gap(known_count=1),
        )
        assert strategy.mode == ResponseMode.CONNECT_AND_INQUIRE

    def test_inferences_trigger_connect(self):
        strategy = select_response_strategy(
            _sense(specificity="low"),
            _gap(inference_count=1),
        )
        assert strategy.mode == ResponseMode.CONNECT_AND_INQUIRE

    def test_connect_includes_questions(self):
        strategy = select_response_strategy(
            _sense(specificity="low"),
            _gap(known_count=1, unknown_medium=2),
        )
        assert strategy.mode == ResponseMode.CONNECT_AND_INQUIRE
        assert len(strategy.questions_to_ask) <= 2


# =============================================================================
# Case 3: No knowledge → INQUIRE
# =============================================================================

class TestInquire:
    def test_no_knowledge_triggers_inquire(self):
        strategy = select_response_strategy(
            _sense(specificity="low"),
            _gap(),
        )
        assert strategy.mode == ResponseMode.INQUIRE

    def test_inquire_includes_questions(self):
        strategy = select_response_strategy(
            _sense(specificity="low"),
            _gap(unknown_high=2),
        )
        assert strategy.mode == ResponseMode.INQUIRE
        assert len(strategy.questions_to_ask) <= 2


# =============================================================================
# Urgency escalation
# =============================================================================

class TestUrgencyEscalation:
    def test_high_urgency_escalates_inquire_to_connect(self):
        strategy = select_response_strategy(
            _sense(specificity="low", urgency="high"),
            _gap(unknown_high=1),
        )
        assert strategy.mode == ResponseMode.INQUIRE
        strategy = adjust_strategy_for_urgency(strategy, _sense(urgency="high"))
        assert strategy.mode == ResponseMode.CONNECT_AND_INQUIRE

    def test_high_urgency_escalates_connect_to_respond(self):
        """When we have facts and urgency is high, escalate to RESPOND."""
        strategy = select_response_strategy(
            _sense(specificity="low", urgency="high"),
            _gap(known_count=1, unknown_medium=1),
        )
        assert strategy.mode == ResponseMode.CONNECT_AND_INQUIRE
        strategy = adjust_strategy_for_urgency(strategy, _sense(urgency="high"))
        assert strategy.mode == ResponseMode.RESPOND

    def test_low_urgency_does_not_escalate(self):
        strategy = select_response_strategy(
            _sense(specificity="low"),
            _gap(),
        )
        original_mode = strategy.mode
        strategy = adjust_strategy_for_urgency(strategy, _sense(urgency="low"))
        assert strategy.mode == original_mode

    def test_urgency_reasoning_appended(self):
        strategy = select_response_strategy(
            _sense(specificity="low"),
            _gap(unknown_high=1),
        )
        strategy = adjust_strategy_for_urgency(strategy, _sense(urgency="high"))
        assert "urgency" in strategy.reasoning.lower()


# =============================================================================
# Tone adjustments
# =============================================================================

class TestToneAdjustments:
    def test_venting_reduces_questions(self):
        strategy = select_response_strategy(
            _sense(specificity="low"),
            _gap(known_count=1, unknown_high=2),
        )
        assert len(strategy.questions_to_ask) == 2
        strategy = adjust_strategy_for_tone(strategy, _sense(tone="venting"))
        assert len(strategy.questions_to_ask) <= 1

    def test_exploring_reduces_questions(self):
        strategy = select_response_strategy(
            _sense(specificity="low"),
            _gap(known_count=1, unknown_high=2),
        )
        strategy = adjust_strategy_for_tone(strategy, _sense(tone="exploring"))
        assert len(strategy.questions_to_ask) <= 1

    def test_seeking_help_keeps_questions(self):
        strategy = select_response_strategy(
            _sense(specificity="low"),
            _gap(known_count=1, unknown_high=2),
        )
        original_count = len(strategy.questions_to_ask)
        strategy = adjust_strategy_for_tone(strategy, _sense(tone="seeking_help"))
        assert len(strategy.questions_to_ask) == original_count


# =============================================================================
# Question selection
# =============================================================================

class TestQuestionSelection:
    def test_max_2_questions(self):
        strategy = select_response_strategy(
            _sense(specificity="low"),
            _gap(known_count=1, unknown_high=3, unknown_medium=3),
        )
        assert len(strategy.questions_to_ask) <= 2

    def test_high_priority_selected_first(self):
        strategy = select_response_strategy(
            _sense(specificity="low"),
            _gap(known_count=1, unknown_high=1, unknown_medium=2),
        )
        if strategy.questions_to_ask:
            assert strategy.questions_to_ask[0].priority == "high"
