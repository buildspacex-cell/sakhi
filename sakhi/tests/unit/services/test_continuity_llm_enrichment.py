"""Unit tests for continuity/llm_enrichment.py and continuity/personal_taxonomy.py."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sakhi.apps.api.services.continuity import llm_enrichment, personal_taxonomy


# ── personal_taxonomy helpers ─────────────────────────────────────────────────

class TestCanonicaliseAnchor:
    def test_lowercases(self):
        assert personal_taxonomy.canonicalise_anchor("JobSearch") == "jobsearch"

    def test_strips_whitespace(self):
        assert personal_taxonomy.canonicalise_anchor("  job search  ") == "job_search"

    def test_collapses_spaces(self):
        assert personal_taxonomy.canonicalise_anchor("my  career   goal") == "my_career_goal"

    def test_truncates_to_64(self):
        long_anchor = "a" * 80
        assert len(personal_taxonomy.canonicalise_anchor(long_anchor)) == 64

    def test_empty_returns_empty(self):
        assert personal_taxonomy.canonicalise_anchor("") == ""

    def test_already_canonical(self):
        assert personal_taxonomy.canonicalise_anchor("job_search") == "job_search"


# ── affective scalar ──────────────────────────────────────────────────────────

class TestComputeAffectiveScalar:
    @pytest.mark.parametrize("emotion,expected", [
        ("happy", 0.8),
        ("calm", 0.5),
        ("neutral", 0.0),
        ("confused", -0.2),
        ("anxious", -0.5),
        ("overwhelmed", -0.8),
    ])
    def test_known_emotions(self, emotion, expected):
        with patch.object(llm_enrichment, "_compute_affective_scalar") as mock:
            # Call the real function by importing the dep directly
            pass
        # Test the scalar map directly
        scalar = llm_enrichment._AFFECTIVE_SCALAR_MAP.get(emotion)
        assert scalar == expected

    def test_unknown_emotion_defaults_to_zero(self):
        with patch("sakhi.apps.api.services.continuity.llm_enrichment.extract_emotion", return_value="unknown_emotion"):
            scalar = llm_enrichment._compute_affective_scalar("some text")
        assert scalar == 0.0


# ── _llm_infer_anchor ─────────────────────────────────────────────────────────

class TestLlmInferAnchor:
    @pytest.mark.asyncio
    async def test_returns_canonicalised_anchor(self):
        # LLM prompt asks for snake_case — model returns single snake_case token
        with patch("sakhi.apps.api.services.continuity.llm_enrichment.call_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = "job_search\n"
            result = await llm_enrichment._llm_infer_anchor("I've been applying for jobs this week")
        assert result == "job_search"

    @pytest.mark.asyncio
    async def test_returns_none_for_unknown(self):
        with patch("sakhi.apps.api.services.continuity.llm_enrichment.call_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = "unknown"
            result = await llm_enrichment._llm_infer_anchor("text")
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_on_llm_failure(self):
        with patch("sakhi.apps.api.services.continuity.llm_enrichment.call_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.side_effect = RuntimeError("timeout")
            result = await llm_enrichment._llm_infer_anchor("text")
        assert result is None


# ── _llm_infer_decision_state ─────────────────────────────────────────────────

class TestLlmInferDecisionState:
    @pytest.mark.asyncio
    async def test_valid_state_returned(self):
        with patch("sakhi.apps.api.services.continuity.llm_enrichment.call_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = "leaning_yes"
            result = await llm_enrichment._llm_infer_decision_state("I think I'll take the job")
        assert result == "leaning_yes"

    @pytest.mark.asyncio
    async def test_invalid_state_returns_none(self):
        with patch("sakhi.apps.api.services.continuity.llm_enrichment.call_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = "maybe"
            result = await llm_enrichment._llm_infer_decision_state("text")
        assert result is None

    @pytest.mark.asyncio
    async def test_llm_failure_returns_none(self):
        with patch("sakhi.apps.api.services.continuity.llm_enrichment.call_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.side_effect = Exception("API error")
            result = await llm_enrichment._llm_infer_decision_state("text")
        assert result is None

    @pytest.mark.parametrize("state", ["questioning", "leaning_yes", "leaning_no", "committed", "deferred", "reversed", "resolved"])
    @pytest.mark.asyncio
    async def test_all_valid_states_accepted(self, state):
        with patch("sakhi.apps.api.services.continuity.llm_enrichment.call_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = state
            result = await llm_enrichment._llm_infer_decision_state("text")
        assert result == state


# ── _llm_infer_epistemic_state ────────────────────────────────────────────────

class TestLlmInferEpistemicState:
    @pytest.mark.asyncio
    async def test_valid_state_returned(self):
        with patch("sakhi.apps.api.services.continuity.llm_enrichment.call_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = "updating"
            result = await llm_enrichment._llm_infer_epistemic_state("I used to think X, but now I see Y")
        assert result == "updating"

    @pytest.mark.asyncio
    async def test_invalid_state_returns_none(self):
        with patch("sakhi.apps.api.services.continuity.llm_enrichment.call_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = "confused"  # not in valid set
            result = await llm_enrichment._llm_infer_epistemic_state("text")
        assert result is None

    @pytest.mark.parametrize("state", ["certain", "uncertain", "updating", "contradicting", "resolved"])
    @pytest.mark.asyncio
    async def test_all_valid_states_accepted(self, state):
        with patch("sakhi.apps.api.services.continuity.llm_enrichment.call_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = state
            result = await llm_enrichment._llm_infer_epistemic_state("text")
        assert result == state


# ── enrich_entry_continuity integration ──────────────────────────────────────

class TestEnrichEntryContinuity:
    @pytest.mark.asyncio
    async def test_empty_text_returns_empty(self):
        result = await llm_enrichment.enrich_entry_continuity("person-1", "entry-1", "")
        assert result == {}

    @pytest.mark.asyncio
    async def test_unknown_anchor_triggers_anchor_inference(self):
        """When anchor is unknown, should infer anchor, upsert taxonomy, update label, return early."""
        with (
            patch("sakhi.apps.api.services.continuity.llm_enrichment.extract_emotion", return_value="neutral"),
            patch("sakhi.apps.api.services.continuity.llm_enrichment._llm_infer_anchor", new_callable=AsyncMock, return_value="job_search") as mock_anchor,
            patch("sakhi.apps.api.services.continuity.llm_enrichment.upsert_personal_taxonomy", new_callable=AsyncMock) as mock_upsert,
            patch("sakhi.apps.api.services.continuity.llm_enrichment.update_continuity_label_anchor", new_callable=AsyncMock) as mock_update,
        ):
            result = await llm_enrichment.enrich_entry_continuity(
                "person-1", "entry-1", "Applied for three jobs today", current_anchor="unknown"
            )

        mock_anchor.assert_awaited_once()
        mock_upsert.assert_awaited_once_with("person-1", "job_search", "Job Search")
        mock_update.assert_awaited_once()
        assert result["inferred_anchor"] == "job_search"
        assert "affective_scalar" in result
        # Should return early — decision/epistemic not in result
        assert "decision_state" not in result

    @pytest.mark.asyncio
    async def test_known_anchor_runs_full_enrichment(self):
        with (
            patch("sakhi.apps.api.services.continuity.llm_enrichment.extract_emotion", return_value="anxious"),
            patch("sakhi.apps.api.services.continuity.llm_enrichment._llm_infer_decision_state", new_callable=AsyncMock, return_value="questioning"),
            patch("sakhi.apps.api.services.continuity.llm_enrichment._llm_infer_epistemic_state", new_callable=AsyncMock, return_value="uncertain"),
            patch("sakhi.apps.api.services.continuity.llm_enrichment.upsert_continuity_label_enrichment", new_callable=AsyncMock) as mock_upsert,
        ):
            result = await llm_enrichment.enrich_entry_continuity(
                "person-1", "entry-1", "Not sure if I should quit", current_anchor="career"
            )

        assert result["decision_state"] == "questioning"
        assert result["epistemic_state"] == "uncertain"
        assert result["affective_scalar"] == -0.5  # anxious
        mock_upsert.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_no_anchor_argument_treated_as_unknown(self):
        """None anchor should trigger anchor inference path."""
        with (
            patch("sakhi.apps.api.services.continuity.llm_enrichment.extract_emotion", return_value="neutral"),
            patch("sakhi.apps.api.services.continuity.llm_enrichment._llm_infer_anchor", new_callable=AsyncMock, return_value=None),
            patch("sakhi.apps.api.services.continuity.llm_enrichment._llm_infer_decision_state", new_callable=AsyncMock, return_value=None),
            patch("sakhi.apps.api.services.continuity.llm_enrichment._llm_infer_epistemic_state", new_callable=AsyncMock, return_value=None),
            patch("sakhi.apps.api.services.continuity.llm_enrichment.upsert_personal_taxonomy", new_callable=AsyncMock),
            patch("sakhi.apps.api.services.continuity.llm_enrichment.update_continuity_label_anchor", new_callable=AsyncMock),
            patch("sakhi.apps.api.services.continuity.llm_enrichment.upsert_continuity_label_enrichment", new_callable=AsyncMock),
        ):
            result = await llm_enrichment.enrich_entry_continuity("person-1", "entry-1", "Some journal text")
        # anchor inferred as None → no inferred_anchor key
        assert "inferred_anchor" not in result


# ── _anchor_to_label ──────────────────────────────────────────────────────────

class TestAnchorToLabel:
    def test_converts_snake_to_title(self):
        assert llm_enrichment._anchor_to_label("job_search") == "Job Search"

    def test_single_word(self):
        assert llm_enrichment._anchor_to_label("career") == "Career"
