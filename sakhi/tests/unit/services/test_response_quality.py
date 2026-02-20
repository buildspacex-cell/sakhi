"""
Tests for response quality guardrails and prompt architecture.

Ensures:
- Legacy guardrails list still has expected entries
- Adaptive prompt uses 3-block cognitive architecture
- Adaptive prompt contains no Ayurvedic jargon (except the "never say" instruction)
- SAKHI_INSTRUCTIONS contains friction framework, response calibration, examples
- Base prompt voice is aligned with adaptive
"""

import pytest

from sakhi.apps.api.services.response.synthesizer import (
    JARGON_FREE_GUARDRAILS,
    SAKHI_INSTRUCTIONS,
    build_adaptive_prompt,
    SynthesizedContext,
)
from sakhi.apps.api.services.conversation_v2.conversation_reasoner import build_prompt


class TestGuardrails:
    """Verify the legacy guardrail list has the expected entries."""

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
        for g in JARGON_FREE_GUARDRAILS:
            if "NEVER" in g and "vata" in g.lower():
                continue  # This is the prohibition guardrail — it names them to ban them
            assert "vata" not in g.lower(), f"Jargon found in guardrail: {g}"
            assert "pitta" not in g.lower(), f"Jargon found in guardrail: {g}"
            assert "kapha" not in g.lower(), f"Jargon found in guardrail: {g}"

    def test_guardrail_count(self):
        """Should have 10 guardrails."""
        assert len(JARGON_FREE_GUARDRAILS) == 10


class TestSakhiInstructions:
    """Verify the static SAKHI_INSTRUCTIONS block contains all required sections."""

    def test_has_identity(self):
        assert "Sakhi" in SAKHI_INSTRUCTIONS
        assert "Personal Clarity and Rhythm Companion" in SAKHI_INSTRUCTIONS

    def test_has_friction_framework(self):
        assert "FRICTION FRAMEWORK" in SAKHI_INSTRUCTIONS
        assert "Running Hot" in SAKHI_INSTRUCTIONS
        assert "All Over the Place" in SAKHI_INSTRUCTIONS
        assert "Stuck" in SAKHI_INSTRUCTIONS
        assert "Good" in SAKHI_INSTRUCTIONS

    def test_friction_has_action_vectors(self):
        """Each friction state must have a response direction."""
        assert "cool, slow, ease intensity" in SAKHI_INSTRUCTIONS
        assert "ground, simplify, steady" in SAKHI_INSTRUCTIONS
        assert "gently mobilize and lighten" in SAKHI_INSTRUCTIONS
        assert "affirm and maintain" in SAKHI_INSTRUCTIONS

    def test_friction_is_for_understanding(self):
        """Friction framework should be framed as thinking model, not mandatory framing."""
        assert "How You Think" in SAKHI_INSTRUCTIONS
        assert "UNDERSTAND" in SAKHI_INSTRUCTIONS

    def test_has_reasoning_chain(self):
        assert "REASONING CHAIN" in SAKHI_INSTRUCTIONS
        assert "STEP 1" in SAKHI_INSTRUCTIONS
        assert "STEP 5" in SAKHI_INSTRUCTIONS

    def test_reasoning_chain_determines_needs(self):
        """Reasoning chain must determine what the person needs before responding."""
        assert "Determine what they need" in SAKHI_INSTRUCTIONS
        assert "Practical help" in SAKHI_INSTRUCTIONS
        assert "Response Calibration" in SAKHI_INSTRUCTIONS

    def test_has_response_calibration(self):
        """Must have Response Calibration section with per-type guidance."""
        assert "RESPONSE CALIBRATION" in SAKHI_INSTRUCTIONS
        assert "How to Respond" in SAKHI_INSTRUCTIONS

    def test_response_calibration_has_physical_symptom(self):
        """Physical symptom guidance must exist in calibration."""
        assert "PHYSICAL SYMPTOM" in SAKHI_INSTRUCTIONS
        assert "practical remedies" in SAKHI_INSTRUCTIONS
        assert "Bullet points OK" in SAKHI_INSTRUCTIONS
        assert "100-250 words" in SAKHI_INSTRUCTIONS

    def test_response_calibration_has_emotional_friction(self):
        """Emotional friction guidance must exist in calibration."""
        assert "EMOTIONAL / MENTAL FRICTION" in SAKHI_INSTRUCTIONS
        assert "pattern insight" in SAKHI_INSTRUCTIONS
        assert "ONE specific shift" in SAKHI_INSTRUCTIONS
        assert "60-150 words" in SAKHI_INSTRUCTIONS

    def test_response_calibration_has_celebration(self):
        """Celebration/casual guidance must exist in calibration."""
        assert "CELEBRATION / CASUAL CHECK-IN" in SAKHI_INSTRUCTIONS
        assert "40-100 words" in SAKHI_INSTRUCTIONS

    def test_response_calibration_has_multi_symptom(self):
        """Multi-symptom pattern guidance must exist."""
        assert "MULTI-SYMPTOM PATTERN" in SAKHI_INSTRUCTIONS
        assert "ONE systemic explanation" in SAKHI_INSTRUCTIONS

    def test_has_behavioral_contract(self):
        assert "Insightful, not informative" in SAKHI_INSTRUCTIONS
        assert "Pattern-aware, not generic" in SAKHI_INSTRUCTIONS
        assert "Practical when they need practical" in SAKHI_INSTRUCTIONS
        assert "Reflective when they need reflection" in SAKHI_INSTRUCTIONS

    def test_has_examples(self):
        assert "Example 1" in SAKHI_INSTRUCTIONS
        assert "Example 2" in SAKHI_INSTRUCTIONS
        assert "Example 3" in SAKHI_INSTRUCTIONS
        assert "Example 4" in SAKHI_INSTRUCTIONS

    def test_bans_ayurvedic_jargon(self):
        """Instructions should ban jargon explicitly."""
        assert "Never use words like vata, pitta, kapha, dosha" in SAKHI_INSTRUCTIONS

    def test_has_quality_rules(self):
        """Must have consolidated quality rules section."""
        assert "QUALITY RULES" in SAKHI_INSTRUCTIONS

    def test_has_no_soft_hedging_rule(self):
        """Must ban hedging language."""
        assert "NO SOFT HEDGING RULE" in SAKHI_INSTRUCTIONS
        assert "It might be" in SAKHI_INSTRUCTIONS

    def test_has_pattern_integration_rule(self):
        """Must require cross-symptom integration."""
        assert "PATTERN INTEGRATION RULE" in SAKHI_INSTRUCTIONS

    def test_has_anti_generic_test(self):
        """Must include the 'would this apply to anyone' test."""
        assert "Would this advice apply to ANY person" in SAKHI_INSTRUCTIONS

    def test_has_always_rules(self):
        """Must have universal rules."""
        assert "No more than 1 question per response" in SAKHI_INSTRUCTIONS
        assert "No medical diagnosis language" in SAKHI_INSTRUCTIONS

    def test_no_rigid_word_count(self):
        """Instructions should NOT have a single rigid word count for all responses."""
        # The old "60-120 words" was too rigid. Now each calibration type has its own range.
        # Check that we DON'T have the old blanket rule.
        assert "60-120 words unless they ask for depth" not in SAKHI_INSTRUCTIONS

    def test_no_friction_enforcement_rule(self):
        """Friction should not be mandatory in every response (old FRICTION ENFORCEMENT RULE removed)."""
        assert "FRICTION ENFORCEMENT RULE" not in SAKHI_INSTRUCTIONS
        assert "You MUST explicitly reference it" not in SAKHI_INSTRUCTIONS

    def test_examples_include_practical_body(self):
        """At least one example must show practical health advice with bullets."""
        assert "salt water gargle" in SAKHI_INSTRUCTIONS

    def test_examples_include_emotional_pattern(self):
        """At least one example must show emotional friction with pattern insight."""
        assert "Irritation is usually the first signal" in SAKHI_INSTRUCTIONS


class TestAdaptivePromptArchitecture:
    """Verify the adaptive prompt uses the 3-block cognitive architecture."""

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

    def test_has_three_blocks(self):
        """Prompt must have SAKHI INSTRUCTIONS, THIS PERSON, THIS CONVERSATION blocks."""
        prompt = build_adaptive_prompt("my head hurts", self._build_minimal_synth())
        assert "FRICTION FRAMEWORK" in prompt
        assert "THIS PERSON" in prompt
        assert "THIS CONVERSATION" in prompt

    def test_person_block_has_who_they_are(self):
        prompt = build_adaptive_prompt("my head hurts", self._build_minimal_synth())
        assert "WHO THEY ARE" in prompt

    def test_person_block_has_right_now(self):
        prompt = build_adaptive_prompt("my head hurts", self._build_minimal_synth())
        assert "RIGHT NOW" in prompt
        assert "Friction:" in prompt

    def test_conversation_block_has_response_direction(self):
        prompt = build_adaptive_prompt("my head hurts", self._build_minimal_synth())
        assert "Response direction:" in prompt

    def test_prompt_bans_jargon(self):
        prompt = build_adaptive_prompt("my head hurts", self._build_minimal_synth())
        lines = prompt.split("\n")
        for line in lines:
            if "never" in line.lower() and ("use" in line.lower() or "say" in line.lower()):
                continue
            if "NEVER" in line and "jargon" in line.lower():
                continue
            assert "dosha" not in line.lower() or "never" in line.lower(), f"Jargon leaked: {line}"

    def test_prompt_ends_with_user_message(self):
        prompt = build_adaptive_prompt("my head hurts", self._build_minimal_synth())
        assert "THEY SAID: my head hurts" in prompt

    def test_session_summary_included_when_present(self):
        ctx = self._build_minimal_synth()
        ctx.session_summary = "User mentioned headaches last week"
        prompt = build_adaptive_prompt("my head hurts", ctx)
        assert "EARLIER IN CONVERSATION" in prompt
        assert "headaches last week" in prompt

    def test_session_summary_absent_when_empty(self):
        ctx = self._build_minimal_synth()
        ctx.session_summary = ""
        prompt = build_adaptive_prompt("my head hurts", ctx)
        # The phrase appears in SAKHI_INSTRUCTIONS (Pattern Integration Rule),
        # but should NOT appear in the THIS PERSON data block
        person_block = prompt.split("THIS PERSON")[1].split("THIS CONVERSATION")[0]
        assert "EARLIER IN CONVERSATION" not in person_block

    def test_known_facts_displayed(self):
        ctx = self._build_minimal_synth()
        ctx.known_facts = ["Recently mentioned: sleeping 5 hours"]
        prompt = build_adaptive_prompt("my head hurts", ctx)
        assert "sleeping 5 hours" in prompt
        assert "WHAT WE KNOW" in prompt

    def test_connections_shown_when_present(self):
        ctx = self._build_minimal_synth()
        ctx.related_context = ["Connection: meditation supports sleep"]
        prompt = build_adaptive_prompt("my head hurts", ctx)
        assert "CONNECTIONS" in prompt
        assert "meditation supports sleep" in prompt


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


class TestResponseCalibration:
    """Verify response calibration works for all domain types without overrides.

    The base SAKHI_INSTRUCTIONS should be flexible enough to handle ANY
    conversation type (body, mind, life, celebration) without domain-specific
    override blocks being injected into the prompt.
    """

    def _build_synth(self, symptom="sore_throat", domain="body") -> SynthesizedContext:
        from sakhi.apps.api.services.response.translation import build_jargon_free_context
        jf = build_jargon_free_context(
            operating_system="Adaptive-Performance",
            dosha_baseline={"vata": 0.30, "pitta": 0.45, "kapha": 0.25},
            friction_state="intensity",
            drift_percentage=20,
            energy_mode="rajas",
        )
        ctx = SynthesizedContext()
        ctx.jargon_free = jf
        ctx.response_mode = "RESPOND"
        ctx.domain = domain
        ctx.symptom = symptom
        ctx.temporal = "acute"
        ctx.specificity = "medium"
        ctx.tone_guidance = "cooling, soothing"
        ctx.guardrails = JARGON_FREE_GUARDRAILS.copy()
        ctx.known_facts = ["Recently mentioned: daughter had cold last week"]
        return ctx

    def test_no_domain_specific_override_injected(self):
        """No domain-specific override block should be injected into ANY prompt."""
        body_prompt = build_adaptive_prompt("sore throat", self._build_synth())
        mind_prompt = build_adaptive_prompt("anxious", self._build_synth(symptom="anxiety", domain="mind"))
        life_prompt = build_adaptive_prompt("work stress", self._build_synth(symptom="work", domain="life"))

        for prompt in [body_prompt, mind_prompt, life_prompt]:
            assert "BODY SYMPTOM MODE" not in prompt
            assert "OVERRIDE" not in prompt

    def test_all_prompts_share_same_base_instructions(self):
        """Body, mind, and life prompts should all start with the same SAKHI_INSTRUCTIONS."""
        body_prompt = build_adaptive_prompt("sore throat", self._build_synth())
        mind_prompt = build_adaptive_prompt("anxious", self._build_synth(symptom="anxiety", domain="mind"))

        # Both should contain the RESPONSE CALIBRATION section
        assert "RESPONSE CALIBRATION" in body_prompt
        assert "RESPONSE CALIBRATION" in mind_prompt

        # Both should contain physical AND emotional guidance
        assert "PHYSICAL SYMPTOM" in body_prompt
        assert "PHYSICAL SYMPTOM" in mind_prompt
        assert "EMOTIONAL / MENTAL FRICTION" in body_prompt
        assert "EMOTIONAL / MENTAL FRICTION" in mind_prompt

    def test_instructions_have_practical_remedy_guidance(self):
        """Base instructions must guide practical remedies for physical symptoms."""
        assert "practical remedies" in SAKHI_INSTRUCTIONS
        assert "Bullet points OK" in SAKHI_INSTRUCTIONS
        assert "diagnostic question" in SAKHI_INSTRUCTIONS

    def test_instructions_have_emotional_pattern_guidance(self):
        """Base instructions must guide pattern insight for emotional friction."""
        assert "pattern insight" in SAKHI_INSTRUCTIONS
        assert "ONE specific shift" in SAKHI_INSTRUCTIONS

    def test_instructions_have_flexible_word_counts(self):
        """Each conversation type should have its own word count range."""
        assert "100-250 words" in SAKHI_INSTRUCTIONS   # physical
        assert "60-150 words" in SAKHI_INSTRUCTIONS     # emotional
        assert "80-150 words" in SAKHI_INSTRUCTIONS     # decision/multi-symptom
        assert "40-100 words" in SAKHI_INSTRUCTIONS     # celebration/casual

    def test_friction_as_background_for_physical(self):
        """For physical symptoms, friction should be background context."""
        assert "Friction state is background context" in SAKHI_INSTRUCTIONS

    def test_friction_as_causal_for_emotional(self):
        """For emotional friction, friction should be the causal framework."""
        assert "it's the causal framework here" in SAKHI_INSTRUCTIONS

    def test_body_prompt_includes_domain_in_direction(self):
        """Response direction should include domain for calibration lookup."""
        prompt = build_adaptive_prompt("sore throat", self._build_synth())
        assert "body" in prompt.lower()  # domain appears in conversation block

    def test_mind_prompt_includes_domain_in_direction(self):
        """Response direction should include domain for calibration lookup."""
        prompt = build_adaptive_prompt("anxious", self._build_synth(symptom="anxiety", domain="mind"))
        assert "mind" in prompt.lower()

    def test_examples_show_practical_body_response(self):
        """Examples must demonstrate practical body symptom response with bullets."""
        assert "salt water gargle" in SAKHI_INSTRUCTIONS
        assert "What helps:" in SAKHI_INSTRUCTIONS
        # The example uses bullet points for remedies
        assert "Honey in warm water" in SAKHI_INSTRUCTIONS

    def test_examples_show_emotional_pattern_response(self):
        """Examples must demonstrate emotional friction with pattern insight."""
        assert "Irritation is usually the first signal" in SAKHI_INSTRUCTIONS
        assert "pause before reacting" in SAKHI_INSTRUCTIONS

    def test_recommendation_guidance_varies_by_type(self):
        """Recommendation usage should differ for physical vs emotional."""
        assert "For physical symptoms: combine relevant suggestions" in SAKHI_INSTRUCTIONS
        assert "For emotional/mental: pick ONE" in SAKHI_INSTRUCTIONS

    def test_response_direction_mentions_calibration(self):
        """Response direction should reference Response Calibration."""
        prompt = build_adaptive_prompt("sore throat", self._build_synth())
        assert "Response Calibration" in prompt
