"""
Unit tests for conversation_reasoner — build_prompt() context injection.

Tests that email context, causal reasoning, contact preferences,
360° context scan, and tier 2 deep sections
are correctly composed into the LLM prompt.
"""

import pytest

from sakhi.apps.api.services.conversation_v2.conversation_reasoner import (
    build_prompt,
    build_context_scan,
    build_tier2_section,
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
# Email Context Section
# =============================================================================


class TestEmailContextSection:
    """Tests for email intelligence injection into prompt."""

    def test_email_context_appears_when_present(self):
        metadata = {
            "email_context": "Email patterns:\n- 3 email thread(s) awaiting reply\n- Email cognitive load: moderate (15 active threads)",
        }
        result = build_prompt("How's my inbox?", _base_context(), _base_tone(), metadata=metadata)
        assert "EMAIL INTELLIGENCE" in result
        assert "3 email thread(s) awaiting reply" in result
        assert "cognitive load" in result

    def test_no_email_section_when_absent(self):
        metadata = {}
        result = build_prompt("Hello", _base_context(), _base_tone(), metadata=metadata)
        assert "EMAIL INTELLIGENCE" not in result

    def test_contact_preferences_appear_when_present(self):
        metadata = {
            "contact_preferences": (
                "The user has set these contact preferences:\n"
                "- sarah@acme.com: BOSS at \"Acme Corp\" (priority: CRITICAL) — \"Always reply same day\""
            ),
        }
        result = build_prompt("Should I reply to Sarah?", _base_context(), _base_tone(), metadata=metadata)
        assert "sarah@acme.com" in result
        assert "BOSS" in result
        assert "CRITICAL" in result
        assert "Always reply same day" in result

    def test_email_context_and_prefs_combined(self):
        metadata = {
            "email_context": "Email patterns:\n- Email boundary erosion: 40% after-hours (trend: worsening)",
            "contact_preferences": "The user has set these contact preferences:\n- boss@co.com: (priority: CRITICAL)",
        }
        result = build_prompt("How's my email?", _base_context(), _base_tone(), metadata=metadata)
        assert "EMAIL INTELLIGENCE" in result
        assert "boundary erosion" in result
        assert "boss@co.com" in result


# =============================================================================
# Causal Reasoning Section
# =============================================================================


class TestCausalReasoningSection:
    """Tests for Ayurvedic causal reasoning injection."""

    def test_causal_explanation_appears_when_present(self):
        metadata = {
            "causal_explanation": {
                "symptom": "scattered",
                "dosha_context": "Scattered is a classic sign of elevated Vata (air/space).",
                "explanation_text": "Based on your patterns: late dinners tend to cause this.",
                "primary_causes": [],
                "contributing_factors": [],
                "seasonal_influence": None,
            },
        }
        result = build_prompt("Why am I feeling scattered?", _base_context(), _base_tone(), metadata=metadata)
        assert "WHY YOU MIGHT BE FEELING THIS WAY" in result
        assert "elevated Vata" in result
        assert "late dinners" in result

    def test_no_causal_section_when_absent(self):
        metadata = {}
        result = build_prompt("Hello", _base_context(), _base_tone(), metadata=metadata)
        assert "WHY YOU MIGHT BE FEELING THIS WAY" not in result

    def test_causal_section_guidance_present(self):
        metadata = {
            "causal_explanation": {
                "dosha_context": "Test dosha context",
                "explanation_text": "Test explanation",
            },
        }
        result = build_prompt("Why do I feel this way?", _base_context(), _base_tone(), metadata=metadata)
        assert "not to lecture" in result
        assert "grounded and practical" in result


# =============================================================================
# Base Prompt Structure
# =============================================================================


class TestBasePromptStructure:
    """Tests that existing prompt structure is preserved."""

    def test_prompt_contains_persona(self):
        result = build_prompt("Hello", _base_context(), _base_tone())
        assert "Sakhi" in result
        assert "friend" in result

    def test_prompt_contains_user_message(self):
        result = build_prompt("How are you?", _base_context(), _base_tone())
        assert "How are you?" in result

    def test_prompt_contains_emotion_state(self):
        result = build_prompt("Hello", _base_context(), _base_tone())
        assert "anxious" in result

    def test_all_sections_coexist(self):
        """All context sections should appear together without conflict."""
        metadata = {
            "email_context": "Email patterns:\n- 2 threads awaiting reply",
            "contact_preferences": "The user has set these contact preferences:\n- x@y.com: (priority: HIGH)",
            "causal_explanation": {
                "dosha_context": "Vata elevated",
                "explanation_text": "Contributing: email load",
            },
        }
        result = build_prompt("Why is everything piling up?", _base_context(), _base_tone(), metadata=metadata)
        assert "EMAIL INTELLIGENCE" in result
        assert "WHY YOU MIGHT BE FEELING THIS WAY" in result
        assert "x@y.com" in result
        assert "Vata elevated" in result
        assert "User message:" in result
        assert "Why is everything piling up?" in result


# =============================================================================
# Tier 1: 360° Context Scan
# =============================================================================


class TestContextScan:
    """Tests for the always-present 360° context scan."""

    def test_scan_with_identity_data(self):
        metadata = {
            "identity_momentum_frame": {"momentum_direction": "building", "momentum_score": 0.7},
            "alignment_frame": {"alignment_score": 0.8},
            "identity_timeline_frame": {"current_phase": "integration"},
            "narrative_trace": {"dominant_theme": "career transition"},
        }
        scan = build_context_scan(metadata)
        assert "CONTEXT SCAN" in scan
        assert "momentum=building" in scan
        assert "alignment=0.8" in scan
        assert "phase=integration" in scan
        assert "narrative=career transition" in scan

    def test_scan_with_emotional_data(self):
        metadata = {
            "empathy_state": {"pattern": "mirror-first"},
            "microreg_state": {"shift": "grounding", "amplitude": 0.6, "risk": "low"},
        }
        scan = build_context_scan(metadata)
        assert "Emotional:" in scan
        assert "empathy=mirror-first" in scan
        assert "microreg=grounding" in scan

    def test_scan_with_moment_data(self):
        metadata = {
            "moment_model": {
                "recommended_companion_mode": "supportive",
                "cognitive_load": "low",
                "energy_state": "moderate",
                "dominant_need": "connection",
            },
        }
        scan = build_context_scan(metadata)
        assert "Moment:" in scan
        assert "mode=supportive" in scan
        assert "load=low" in scan
        assert "need=connection" in scan

    def test_scan_with_friction_data(self):
        metadata = {
            "friction_state": {"state": "Mild Friction", "drift_percentage": 18.5},
        }
        scan = build_context_scan(metadata)
        assert "Friction: Mild Friction" in scan
        assert "drift=18%" in scan

    def test_scan_with_micro_flow_data(self):
        metadata = {
            "focus_path": {"anchor_step": "review"},
            "mini_flow": {"warmup_step": "breathe"},
        }
        scan = build_context_scan(metadata)
        assert "Micro:" in scan
        assert "focus_path=ready" in scan
        assert "mini_flow=ready" in scan

    def test_scan_empty_metadata(self):
        scan = build_context_scan({})
        assert scan == ""

    def test_scan_omits_empty_modules(self):
        metadata = {
            "moment_model": {},
            "empathy_state": {},
            "narrative_trace": {},
        }
        scan = build_context_scan(metadata)
        assert scan == ""

    def test_scan_in_build_prompt(self):
        metadata = {
            "moment_model": {"recommended_companion_mode": "reflective", "dominant_need": "clarity"},
        }
        result = build_prompt("Hello", _base_context(), _base_tone(), metadata=metadata)
        assert "CONTEXT SCAN" in result
        assert "mode=reflective" in result


# =============================================================================
# Tier 2: Deep Context Sections
# =============================================================================


class TestTier2IdentitySection:
    """Tests for identity & growth deep context."""

    def test_identity_section_appears(self):
        metadata = {
            "narrative_trace": {"dominant_theme": "career change", "emotional_trend": "cautiously hopeful", "shadow_pressure": "fear of failure"},
            "alignment_frame": {"alignment_score": 0.6, "conflict_zones": "work-life balance"},
            "identity_momentum_frame": {"momentum_score": 0.7, "momentum_direction": "building", "emotional_drag": "none"},
            "identity_timeline_frame": {"current_phase": "transition", "phase_intensity": "high", "emerging_signal": "entrepreneurial urge"},
        }
        section = build_tier2_section("identity", metadata)
        assert "IDENTITY & GROWTH" in section
        assert "career change" in section
        assert "alignment_score" not in section or "0.6" in section
        assert "building" in section
        assert "transition" in section

    def test_identity_section_absent_without_data(self):
        section = build_tier2_section("identity", {})
        assert section == ""

    def test_identity_in_prompt_when_active(self):
        metadata = {
            "active_modules": ["identity"],
            "narrative_trace": {"dominant_theme": "self-discovery"},
            "alignment_frame": {"alignment_score": 0.9},
        }
        result = build_prompt("Who am I?", _base_context(), _base_tone(), metadata=metadata)
        assert "IDENTITY & GROWTH" in result


class TestTier2EmotionalSection:
    """Tests for emotional attunement deep context."""

    def test_emotional_section_appears(self):
        metadata = {
            "inner_dialogue": {"guidance_intention": "hold space for sadness", "tone": "gentle", "reflections": ["deep breath", "you are not alone"]},
            "empathy_state": {"pattern": "mirror-first", "instruction": "match their tone before guiding"},
            "microreg_state": {"pattern": "grounding", "shift": "slow", "amplitude": 0.5},
        }
        section = build_tier2_section("emotional_depth", metadata)
        assert "EMOTIONAL ATTUNEMENT" in section
        assert "hold space for sadness" in section
        assert "mirror-first" in section
        assert "grounding" in section

    def test_emotional_section_absent_without_data(self):
        section = build_tier2_section("emotional_depth", {})
        assert section == ""


class TestTier2MomentSection:
    """Tests for moment intelligence deep context."""

    def test_moment_section_appears(self):
        metadata = {
            "moment_model": {
                "recommended_companion_mode": "coach",
                "emotional_intensity": 0.7,
                "stability": 0.5,
                "cognitive_load": "high",
                "energy_state": "low",
                "dominant_need": "clarity",
            },
            "evidence_pack": {
                "anchors": [
                    {"summary": "Last time you felt this way, journaling helped"},
                    {"summary": "You thrive when you break things into small steps"},
                ],
            },
            "deliberation_scaffold": {
                "current_tension": "stay vs leave",
                "decision_domain": "career",
                "options": ["stay and negotiate", "leave for new role"],
            },
        }
        section = build_tier2_section("moment", metadata)
        assert "MOMENT INTELLIGENCE" in section
        assert "coach" in section
        assert "journaling helped" in section
        assert "stay vs leave" in section

    def test_moment_section_absent_without_data(self):
        section = build_tier2_section("moment", {})
        assert section == ""


class TestTier2MicroFlowSection:
    """Tests for micro flow deep context."""

    def test_micro_flow_section_with_focus_path(self):
        metadata = {
            "focus_path": {"anchor_step": "review notes", "progress_step": "write summary", "closure_step": "share draft"},
        }
        section = build_tier2_section("micro_flow", metadata)
        assert "MICRO FLOW" in section
        assert "review notes" in section
        assert "write summary" in section

    def test_micro_flow_section_with_mini_flow(self):
        metadata = {
            "mini_flow": {"warmup_step": "breathe", "focus_block_step": "write", "closure_step": "review"},
        }
        section = build_tier2_section("micro_flow", metadata)
        assert "MICRO FLOW" in section
        assert "breathe" in section

    def test_micro_flow_section_absent_without_data(self):
        section = build_tier2_section("micro_flow", {})
        assert section == ""


# =============================================================================
# Full Integration: Scan + Tier 2 + Existing Sections Coexist
# =============================================================================


class TestFullIntegration:
    """Tests that all tiers and sections work together in build_prompt."""

    def test_all_tiers_coexist(self):
        """Context scan + tier 2 sections + email + causal all appear together."""
        metadata = {
            "active_modules": ["identity", "emotional_depth", "moment"],
            # Tier 1 scan data
            "moment_model": {"recommended_companion_mode": "coach", "dominant_need": "clarity"},
            "empathy_state": {"pattern": "mirror"},
            "microreg_state": {"shift": "activation", "amplitude": 0.7},
            "friction_state": {"state": "Moderate Friction", "drift_percentage": 22},
            # Tier 2 identity
            "narrative_trace": {"dominant_theme": "career pivoting"},
            "alignment_frame": {"alignment_score": 0.6},
            # Tier 2 emotional
            "inner_dialogue": {"guidance_intention": "validate feelings", "tone": "warm"},
            # Tier 2 moment
            "evidence_pack": {"anchors": [{"summary": "past experience anchor"}]},
            "deliberation_scaffold": {"current_tension": "stay vs go"},
            # Existing sections
            "email_context": "3 threads pending",
            "causal_explanation": {"dosha_context": "Vata rising", "explanation_text": "late nights"},
        }
        result = build_prompt("What should I do?", _base_context(), _base_tone(), metadata=metadata)

        # Tier 1 scan
        assert "CONTEXT SCAN" in result
        assert "mode=coach" in result

        # Tier 2 sections
        assert "IDENTITY & GROWTH" in result
        assert "EMOTIONAL ATTUNEMENT" in result
        assert "MOMENT INTELLIGENCE" in result

        # Existing sections
        assert "EMAIL INTELLIGENCE" in result
        assert "WHY YOU MIGHT BE FEELING THIS WAY" in result

        # User message preserved
        assert "What should I do?" in result

    def test_no_tier2_when_no_active_modules(self):
        """Without active_modules, only scan appears (no tier 2 sections)."""
        metadata = {
            "moment_model": {"recommended_companion_mode": "reflective", "dominant_need": "rest"},
            "narrative_trace": {"dominant_theme": "burnout"},
        }
        result = build_prompt("Hey", _base_context(), _base_tone(), metadata=metadata)
        assert "CONTEXT SCAN" in result
        assert "IDENTITY & GROWTH" not in result
        assert "MOMENT INTELLIGENCE" not in result

    def test_unknown_module_ignored(self):
        """Unknown module names don't cause errors."""
        metadata = {
            "active_modules": ["nonexistent_module"],
        }
        result = build_prompt("Hello", _base_context(), _base_tone(), metadata=metadata)
        assert "User message:" in result
