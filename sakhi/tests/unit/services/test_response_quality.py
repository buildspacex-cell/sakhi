"""
Tests for response quality guardrails.

Ensures:
- Help-first guardrail is present
- New vs returning user guardrail is present
- Adaptive prompt contains no Ayurvedic jargon (except the "never say" instruction)
- Base prompt voice is aligned with adaptive
"""

import pytest

from sakhi.apps.api.services.response.synthesizer import (
    JARGON_FREE_GUARDRAILS,
    build_adaptive_prompt,
    SynthesizedContext,
)
from sakhi.apps.api.services.conversation_v2.conversation_reasoner import build_prompt


class TestGuardrails:
    """Verify the guardrail list has the expected entries."""

    def test_help_first_guardrail_present(self):
        """P0 fix: help-first guardrail must be in the list."""
        texts = " ".join(JARGON_FREE_GUARDRAILS).lower()
        assert "help first" in texts or "enough context to help" in texts

    def test_new_vs_returning_user_guardrail_present(self):
        """P0 fix: new vs returning user behavior must be in guardrails."""
        texts = " ".join(JARGON_FREE_GUARDRAILS).lower()
        assert "new user" in texts or "returning user" in texts

    def test_no_ayurvedic_jargon_in_guardrails(self):
        """Guardrails themselves should not use jargon except to say 'never use these'."""
        # The one guardrail that mentions jargon is the "NEVER use" instruction
        for g in JARGON_FREE_GUARDRAILS:
            if "NEVER" in g and "vata" in g.lower():
                continue  # This is the prohibition guardrail — it names them to ban them
            assert "vata" not in g.lower(), f"Jargon found in guardrail: {g}"
            assert "pitta" not in g.lower(), f"Jargon found in guardrail: {g}"
            assert "kapha" not in g.lower(), f"Jargon found in guardrail: {g}"

    def test_guardrail_count(self):
        """Should have 10 guardrails after P0 additions."""
        assert len(JARGON_FREE_GUARDRAILS) == 10


class TestAdaptivePromptJargonFree:
    """Verify the adaptive prompt output is jargon-free."""

    def _build_minimal_synth(self) -> SynthesizedContext:
        from sakhi.apps.api.services.response.translation import build_jargon_free_context
        jf = build_jargon_free_context(
            operating_system="Balanced",
            dosha_baseline={},
            friction_state="balanced",
            drift_percentage=0,
            energy_mode="sattva",
        )
        ctx = SynthesizedContext()
        ctx.jargon_free = jf
        ctx.response_mode = "RESPOND"
        ctx.domain = "body"
        ctx.symptom = "headache"
        ctx.temporal = "acute"
        ctx.specificity = "medium"
        ctx.tone_guidance = "warm, gentle"
        ctx.guardrails = JARGON_FREE_GUARDRAILS.copy()
        return ctx

    def test_adaptive_prompt_says_friend(self):
        prompt = build_adaptive_prompt("my head hurts", self._build_minimal_synth())
        assert "friend" in prompt.lower()

    def test_adaptive_prompt_bans_jargon(self):
        prompt = build_adaptive_prompt("my head hurts", self._build_minimal_synth())
        # "vata, pitta, kapha, dosha" should only appear in the "never say" instruction
        lines = prompt.split("\n")
        for line in lines:
            if "never" in line.lower() and "say" in line.lower():
                continue  # The ban instruction
            if "NEVER" in line and "jargon" in line.lower():
                continue  # Another ban line
            # These should not appear elsewhere
            assert "dosha" not in line.lower() or "never" in line.lower(), f"Jargon leaked: {line}"


class TestBasePromptVoiceAlignment:
    """Verify base prompt voice matches adaptive after P2."""

    def _base_context(self):
        return {
            "short_term": {"texts": ["test"]},
            "themes": [],
            "continuity": {},
            "conversation": {"last_emotion": "neutral", "energy_level": 0.5},
        }

    def _base_tone(self):
        return {
            "style": "warm",
            "pace": "balanced",
            "concise": False,
            "micro": {},
            "mirroring": {},
            "ritual": {},
            "empathy": {},
            "stability": {},
        }

    def test_base_prompt_says_friend(self):
        """Base prompt should say 'friend', not 'clarity companion'."""
        result = build_prompt("hello", self._base_context(), self._base_tone())
        assert "friend" in result.lower()
        assert "clarity companion" not in result.lower()

    def test_base_prompt_bans_jargon(self):
        """Base prompt voice section should ban Ayurvedic jargon."""
        result = build_prompt("hello", self._base_context(), self._base_tone())
        assert "No Ayurvedic jargon" in result or "jargon" in result.lower()

    def test_base_prompt_has_help_first(self):
        """Base prompt should instruct to help first."""
        result = build_prompt("hello", self._base_context(), self._base_tone())
        assert "help" in result.lower()
        assert "Don't ask just to ask" in result or "don't ask just to ask" in result.lower()

    def test_base_prompt_no_persona_mode(self):
        """Persona mode was removed in P2."""
        result = build_prompt("hello", self._base_context(), self._base_tone())
        assert "Persona mode:" not in result
