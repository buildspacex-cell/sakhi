"""
Tests for response quality guardrails and prompt architecture.

Ensures:
- Legacy guardrails list still has expected entries
- Adaptive prompt uses 3-block cognitive architecture
- Adaptive prompt contains no Ayurvedic jargon (except the "never say" instruction)
- SAKHI_INSTRUCTIONS contains friction framework, practice rule, examples
- Base prompt voice is aligned with adaptive
"""

import pytest

from sakhi.apps.api.services.response.synthesizer import (
    JARGON_FREE_GUARDRAILS,
    SAKHI_INSTRUCTIONS,
    build_adaptive_prompt,
    SynthesizedContext,
    _is_physical_health_symptom,
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

    def test_has_reasoning_chain(self):
        assert "REASONING CHAIN" in SAKHI_INSTRUCTIONS
        assert "STEP 1" in SAKHI_INSTRUCTIONS
        assert "STEP 5" in SAKHI_INSTRUCTIONS

    def test_has_precision_practice_rule(self):
        assert "PRECISION PRACTICE RULE" in SAKHI_INSTRUCTIONS
        assert "ONE specific practice" in SAKHI_INSTRUCTIONS
        assert "plain English" in SAKHI_INSTRUCTIONS

    def test_has_recommendation_selection_rule(self):
        """Must instruct LLM to pick ONE suggestion, not list everything."""
        assert "Pick ONE suggestion" in SAKHI_INSTRUCTIONS
        assert "Do NOT list everything" in SAKHI_INSTRUCTIONS

    def test_has_behavioral_contract(self):
        assert "Insightful, not informative" in SAKHI_INSTRUCTIONS
        assert "Pattern-aware, not generic" in SAKHI_INSTRUCTIONS

    def test_has_examples(self):
        assert "Example 1" in SAKHI_INSTRUCTIONS
        assert "Example 2" in SAKHI_INSTRUCTIONS
        assert "Example 3" in SAKHI_INSTRUCTIONS
        assert "Example 4" in SAKHI_INSTRUCTIONS

    def test_bans_ayurvedic_jargon(self):
        """Instructions should ban jargon explicitly."""
        assert "Never use words like vata, pitta, kapha, dosha" in SAKHI_INSTRUCTIONS

    def test_tone_and_length(self):
        assert "60-120 words" in SAKHI_INSTRUCTIONS
        assert "No more than 1 question per response" in SAKHI_INSTRUCTIONS

    def test_has_friction_enforcement_rule(self):
        """Friction state must be mandatory, not optional."""
        assert "FRICTION ENFORCEMENT RULE" in SAKHI_INSTRUCTIONS
        assert "You MUST explicitly reference it" in SAKHI_INSTRUCTIONS

    def test_has_no_soft_hedging_rule(self):
        """Must ban hedging language."""
        assert "NO SOFT HEDGING RULE" in SAKHI_INSTRUCTIONS
        assert "It might be" in SAKHI_INSTRUCTIONS

    def test_has_pattern_integration_rule(self):
        """Must require cross-symptom integration."""
        assert "PATTERN INTEGRATION RULE" in SAKHI_INSTRUCTIONS
        assert "ONE systemic explanation" in SAKHI_INSTRUCTIONS

    def test_has_anti_generic_test(self):
        """Must include the 'would this apply to anyone' test."""
        assert "Would this advice apply to ANY person" in SAKHI_INSTRUCTIONS


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


class TestBodyHealthOverride:
    """Verify body-domain physical symptoms get practical health instructions."""

    def _build_body_synth(self, symptom="sore_throat", domain="body") -> SynthesizedContext:
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

    def _build_mind_synth(self) -> SynthesizedContext:
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
        ctx.domain = "mind"
        ctx.symptom = "anxiety"
        ctx.temporal = "recurring"
        ctx.specificity = "medium"
        ctx.tone_guidance = "warm, grounding"
        ctx.guardrails = JARGON_FREE_GUARDRAILS.copy()
        return ctx

    def test_body_symptom_gets_override(self):
        """Physical symptom prompt must contain BODY SYMPTOM MODE override."""
        prompt = build_adaptive_prompt("I have a sore throat", self._build_body_synth())
        assert "BODY SYMPTOM MODE" in prompt
        assert "150-250 words" in prompt

    def test_body_symptom_allows_bullets(self):
        """Override must explicitly allow bullet points."""
        prompt = build_adaptive_prompt("I have a sore throat", self._build_body_synth())
        assert "Bullet points ARE appropriate" in prompt

    def test_body_symptom_mentions_practical_remedies(self):
        """Override must instruct practical remedies."""
        prompt = build_adaptive_prompt("I have a sore throat", self._build_body_synth())
        assert "PRACTICAL REMEDIES" in prompt

    def test_body_symptom_has_timeline_instruction(self):
        """Override must mention timeline."""
        prompt = build_adaptive_prompt("I have a sore throat", self._build_body_synth())
        assert "TIMELINE" in prompt

    def test_body_symptom_has_red_flag_instruction(self):
        """Override must mention when to see a doctor."""
        prompt = build_adaptive_prompt("I have a sore throat", self._build_body_synth())
        assert "RED FLAG" in prompt

    def test_mind_symptom_does_not_get_override(self):
        """Mental/emotional concerns should NOT get body override."""
        prompt = build_adaptive_prompt("I feel anxious", self._build_mind_synth())
        assert "BODY SYMPTOM MODE" not in prompt

    def test_headache_gets_override(self):
        """Headache is a physical symptom."""
        prompt = build_adaptive_prompt("I have a headache", self._build_body_synth(symptom="headache"))
        assert "BODY SYMPTOM MODE" in prompt

    def test_fever_gets_override(self):
        """Fever is a physical symptom."""
        prompt = build_adaptive_prompt("I have a fever", self._build_body_synth(symptom="fever"))
        assert "BODY SYMPTOM MODE" in prompt

    def test_nausea_gets_override(self):
        """Nausea is a physical symptom."""
        prompt = build_adaptive_prompt("I feel nauseous", self._build_body_synth(symptom="nausea"))
        assert "BODY SYMPTOM MODE" in prompt

    def test_sleep_does_not_get_override(self):
        """Sleep is lifestyle, not acute physical illness."""
        prompt = build_adaptive_prompt("I can't sleep", self._build_body_synth(symptom="sleep"))
        assert "BODY SYMPTOM MODE" not in prompt

    def test_energy_does_not_get_override(self):
        """Energy is lifestyle, not acute physical illness."""
        prompt = build_adaptive_prompt("I'm so tired", self._build_body_synth(symptom="energy"))
        assert "BODY SYMPTOM MODE" not in prompt

    def test_life_domain_does_not_get_override(self):
        """Life domain should never get body override."""
        prompt = build_adaptive_prompt("career problems", self._build_body_synth(symptom="work", domain="life"))
        assert "BODY SYMPTOM MODE" not in prompt

    def test_body_override_has_example(self):
        """Override should include a body-specific example."""
        prompt = build_adaptive_prompt("I have a sore throat", self._build_body_synth())
        assert "salt water gargle" in prompt

    def test_friction_still_present_as_context(self):
        """Friction state should still appear, just not as primary frame."""
        prompt = build_adaptive_prompt("I have a sore throat", self._build_body_synth())
        assert "CONTEXT, not the primary frame" in prompt

    def test_body_response_direction_says_practical(self):
        """Response direction for body should say 'practical'."""
        prompt = build_adaptive_prompt("I have a sore throat", self._build_body_synth())
        assert "practical" in prompt.lower()

    def test_is_physical_helper_sore_throat(self):
        """Helper correctly identifies sore_throat as physical."""
        ctx = self._build_body_synth(symptom="sore_throat")
        assert _is_physical_health_symptom(ctx) is True

    def test_is_physical_helper_anxiety(self):
        """Helper correctly excludes anxiety."""
        ctx = self._build_mind_synth()
        assert _is_physical_health_symptom(ctx) is False

    def test_is_physical_helper_sleep(self):
        """Helper correctly excludes sleep (lifestyle, not acute physical)."""
        ctx = self._build_body_synth(symptom="sleep")
        assert _is_physical_health_symptom(ctx) is False
