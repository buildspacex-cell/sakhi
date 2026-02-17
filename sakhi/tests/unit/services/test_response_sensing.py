"""
Tests for the sensing layer — specificity classification and data pipeline correctness.

Verifies:
- Specificity heuristic correctly classifies messages
- Symptom classification routes to correct diagnostic paths (not fallbacks)
- Symptom aliases resolve for all supported conditions
- Diagnostic paths have complete dosha coverage
- Topic keywords cover key body sub-domains
- Memory queries use correct column names
- End-to-end symptom → protocol path works
- Personalized question generation via LLM uses personal context
- SYMPTOM_DOSHA_MAP used as fallback for symptom routing
"""

import json
from unittest.mock import AsyncMock, patch

import pytest

from sakhi.apps.api.services.response.sensing import SenseFrame, sense_message
from sakhi.apps.api.services.response.diagnostic_kb import (
    DIAGNOSTIC_PATHS,
    get_symptom_from_sense,
    match_symptom,
    get_symptom_insight,
)
from sakhi.apps.api.services.response.knowledge_gap import (
    TOPIC_KEYWORDS,
    ConstitutionContext,
    DiagnosticQuestion,
    Inference,
    KnowledgeGap,
    KnownFact,
    _get_relevant_topics,
    _integrate_deterministic_intelligence,
    _get_past_symptom_episodes,
    generate_personalized_questions,
    search_short_term_memory,
    load_state_vectors,
)
from sakhi.apps.api.services.ayurveda.causal_reasoning import (
    SYMPTOM_DOSHA_MAP,
    map_symptom_to_dosha,
)


class TestSpecificityClassification:
    """Test specificity classification logic."""

    def test_high_specificity_multiple_indicators(self):
        """Message with 3+ specificity indicators → high."""
        # Location + quality + timing + long message
        frame = sense_message(
            "I've had a sharp headache on my left temple every morning for the past week"
        )
        assert frame.specificity == "high"

    def test_medium_specificity_some_indicators(self):
        """Message with 1-2 indicators → medium."""
        # Needs location/quality/timing keywords or longer message to register
        frame = sense_message("I have a dull headache in my temple after work")
        assert frame.specificity in ("medium", "high")

    def test_low_specificity_no_indicators(self):
        """Very short, vague message → low."""
        frame = sense_message("hello")
        assert frame.specificity == "low"

    def test_long_message_boosts_specificity(self):
        """Messages over 100 chars get a specificity boost."""
        short = sense_message("headache")
        long_msg = sense_message(
            "I've been having this headache that comes and goes, "
            "sometimes it's worse in the morning and I'm not sure what's causing it "
            "but it's been about a week now"
        )
        # Long message should have higher or equal specificity
        specificity_order = {"low": 0, "medium": 1, "high": 2}
        assert specificity_order[long_msg.specificity] >= specificity_order[short.specificity]


class TestDomainClassification:
    """Test domain classification."""

    def test_body_domain(self):
        frame = sense_message("my head hurts and I feel tired")
        assert frame.domain == "body"

    def test_mind_domain(self):
        frame = sense_message("I feel so anxious and stressed")
        assert frame.domain == "mind"

    def test_general_domain_for_greeting(self):
        frame = sense_message("hey how are you")
        assert frame.domain == "general"


class TestTemporalMarkers:
    """Test temporal classification."""

    def test_recurring_temporal(self):
        frame = sense_message("I keep getting headaches lately")
        assert frame.temporal == "recurring"

    def test_acute_temporal(self):
        frame = sense_message("I suddenly feel dizzy right now")
        assert frame.temporal == "acute"

    def test_unspecified_temporal(self):
        frame = sense_message("hello")
        assert frame.temporal == "unspecified"


class TestToneDetection:
    """Test tone classification."""

    def test_seeking_help_tone(self):
        frame = sense_message("can you help me with my sleep issues?")
        assert frame.tone == "seeking_help"

    def test_venting_tone(self):
        frame = sense_message("ugh I'm so frustrated, had enough of this")
        assert frame.tone == "venting"

    def test_neutral_tone(self):
        frame = sense_message("hello")
        assert frame.tone == "neutral"


# =============================================================================
# DATA PIPELINE CORRECTNESS TESTS
# =============================================================================


class TestSymptomClassification:
    """Symptom classification must route to correct diagnostic path, not fallback."""

    def test_dry_skin_not_classified_as_energy(self):
        """Skin symptoms must NOT fall back to 'energy'."""
        sense = SenseFrame(domain="body", sub_domain="skin", symptom="skin", keywords=["skin", "dry"])
        result = get_symptom_from_sense(sense)
        assert result != "energy", f"Skin symptom fell back to energy: {result}"

    def test_skin_maps_to_diagnostic_path(self):
        """'skin' or 'dry_skin' must exist in DIAGNOSTIC_PATHS."""
        assert "skin" in DIAGNOSTIC_PATHS or "dry_skin" in DIAGNOSTIC_PATHS

    def test_headache_still_works(self):
        """Existing symptoms still classify correctly after adding skin."""
        sense = SenseFrame(domain="body", sub_domain="head_neurological", symptom="headache", keywords=["headache"])
        result = get_symptom_from_sense(sense)
        assert result in ("headache", "headaches")

    def test_sleep_still_works(self):
        """Sleep classification unaffected."""
        sense = SenseFrame(domain="body", sub_domain="sleep", symptom="insomnia", keywords=["insomnia"])
        result = get_symptom_from_sense(sense)
        assert result in ("sleep", "insomnia")

    def test_anxiety_still_works(self):
        """Mind domain classification unaffected."""
        sense = SenseFrame(domain="mind", sub_domain="anxiety", symptom="anxiety", keywords=["anxiety"])
        result = get_symptom_from_sense(sense)
        assert result in ("anxiety", "anxious")

    def test_dry_keyword_routes_to_skin(self):
        """'dry' keyword should route to skin path, not energy."""
        sense = SenseFrame(domain="body", sub_domain="skin", symptom="dry", keywords=["dry"])
        result = get_symptom_from_sense(sense)
        assert result != "energy"


class TestSymptomAliases:
    """Symptom aliases must resolve for all supported skin conditions."""

    def test_dry_skin_alias(self):
        assert match_symptom("dry skin") is not None

    def test_skin_alias(self):
        assert match_symptom("skin") is not None

    def test_dryness_alias(self):
        assert match_symptom("dryness") is not None

    def test_rash_alias(self):
        assert match_symptom("rash") is not None

    def test_acne_alias(self):
        assert match_symptom("acne") is not None

    def test_itchy_skin_alias(self):
        assert match_symptom("itchy skin") is not None

    def test_existing_aliases_preserved(self):
        """Adding skin aliases must not break existing ones."""
        assert match_symptom("congestion") == "congestion"
        assert match_symptom("headache") == "headache"
        assert match_symptom("fatigue") == "fatigue"
        assert match_symptom("anxiety") == "anxiety"
        assert match_symptom("stress") == "stress"


class TestSkinDiagnosticPath:
    """Skin diagnostic path must have complete dosha coverage with skin-specific questions."""

    def _get_path(self):
        return DIAGNOSTIC_PATHS.get("dry_skin") or DIAGNOSTIC_PATHS.get("skin")

    def test_path_exists(self):
        assert self._get_path() is not None

    def test_has_all_doshas(self):
        path = self._get_path()
        assert "vata" in path.dosha_questions
        assert "pitta" in path.dosha_questions
        assert "kapha" in path.dosha_questions

    def test_questions_are_skin_specific(self):
        """Skin path should NOT have generic energy/movement questions."""
        path = self._get_path()
        all_questions = []
        for dosha_qs in path.dosha_questions.values():
            all_questions.extend(q.question.lower() for q in dosha_qs)
        # Should NOT have energy-path questions
        assert not any("moving less than usual" in q for q in all_questions)
        assert not any("eating been heavier" in q for q in all_questions)
        # Should have skin-relevant questions
        assert any("dry" in q or "skin" in q or "dryness" in q for q in all_questions)

    def test_has_constitution_guidance(self):
        path = self._get_path()
        assert "vata" in path.constitution_guidance
        assert "pitta" in path.constitution_guidance
        assert "kapha" in path.constitution_guidance

    def test_has_universal_questions(self):
        path = self._get_path()
        assert len(path.universal_questions) > 0

    def test_vata_guidance_mentions_dryness_causes(self):
        path = self._get_path()
        vata = path.constitution_guidance["vata"]
        causes_str = " ".join(vata.likely_causes)
        assert "dry" in causes_str or "dehydration" in causes_str


class TestTopicKeywords:
    """Topic keywords must cover skin and digestion sub-domains."""

    def test_skin_topic_exists(self):
        assert "skin" in TOPIC_KEYWORDS

    def test_skin_topic_has_relevant_keywords(self):
        kw = TOPIC_KEYWORDS["skin"]
        assert "skin" in kw
        assert "dry" in kw
        assert "rash" in kw

    def test_digestion_topic_exists(self):
        assert "digestion" in TOPIC_KEYWORDS

    def test_skin_subdomain_triggers_skin_topics(self):
        sense = SenseFrame(domain="body", sub_domain="skin", symptom="skin", keywords=["skin"])
        topics = _get_relevant_topics(sense)
        assert "skin" in topics

    def test_digestion_subdomain_triggers_digestion_topics(self):
        sense = SenseFrame(domain="body", sub_domain="digestion", symptom="bloating", keywords=["bloating"])
        topics = _get_relevant_topics(sense)
        assert "digestion" in topics

    def test_head_subdomain_still_triggers_screen(self):
        """Existing topic routing must be preserved."""
        sense = SenseFrame(domain="body", sub_domain="head_neurological", symptom="headache", keywords=["headache"])
        topics = _get_relevant_topics(sense)
        assert "screen" in topics


class TestMemoryQueryColumns:
    """Memory queries must use correct column names matching the database schema."""

    def test_stm_query_uses_user_id(self):
        """search_short_term_memory SQL must use user_id, not person_id."""
        import inspect
        source = inspect.getsource(search_short_term_memory)
        assert "user_id" in source, "search_short_term_memory must query user_id column"
        assert "WHERE person_id" not in source, "search_short_term_memory must NOT query person_id"

    def test_state_vectors_query_uses_user_id(self):
        """load_state_vectors SQL must use user_id, not person_id."""
        import inspect
        source = inspect.getsource(load_state_vectors)
        assert "user_id" in source, "load_state_vectors must query user_id column"
        assert "WHERE person_id" not in source, "load_state_vectors must NOT query person_id"


class TestSymptomProtocolPath:
    """End-to-end: sense → get_symptom → match → dosha → insight must work for skin."""

    def test_dry_skin_reaches_protocol(self):
        """Full path for dry skin must produce a non-empty insight."""
        sense = SenseFrame(domain="body", sub_domain="skin", symptom="skin", keywords=["skin", "dry"])
        symptom_key = get_symptom_from_sense(sense)
        assert symptom_key != "energy", f"Fell back to energy: {symptom_key}"

        canonical = match_symptom(symptom_key)
        assert canonical is not None, f"No alias for: {symptom_key}"

        dosha = map_symptom_to_dosha(canonical)
        assert dosha is not None, f"No dosha mapping for: {canonical}"

        insight = get_symptom_insight(canonical, dosha, "Adaptive")
        assert insight, f"No OS insight for: {canonical}/{dosha}"

    def test_headache_reaches_protocol(self):
        """Existing symptom path must still work end-to-end."""
        sense = SenseFrame(domain="body", sub_domain="head_neurological", symptom="headache", keywords=["headache"])
        symptom_key = get_symptom_from_sense(sense)
        canonical = match_symptom(symptom_key)
        assert canonical is not None
        dosha = map_symptom_to_dosha(canonical)
        assert dosha is not None

    def test_rash_maps_to_pitta(self):
        """Rash should map to pitta dosha."""
        canonical = match_symptom("rash")
        assert canonical == "rash"
        dosha = map_symptom_to_dosha(canonical)
        assert dosha == "pitta"

    def test_acne_maps_to_pitta(self):
        """Acne should map to pitta dosha."""
        canonical = match_symptom("acne")
        assert canonical == "acne"
        dosha = map_symptom_to_dosha(canonical)
        assert dosha == "pitta"


# =============================================================================
# SYMPTOM_DOSHA_MAP FALLBACK TESTS
# =============================================================================


class TestSymptomDoshaMapFallback:
    """get_symptom_from_sense and match_symptom should use SYMPTOM_DOSHA_MAP as fallback."""

    def test_bloating_found_via_dosha_map(self):
        """Bloating exists in SYMPTOM_DOSHA_MAP → should NOT fall back to 'energy'."""
        sense = SenseFrame(domain="body", symptom="bloating", keywords=["bloating"])
        result = get_symptom_from_sense(sense)
        assert result != "energy", f"Bloating fell back to energy: {result}"

    def test_stiff_found_via_dosha_map(self):
        """'stiff' exists in SYMPTOM_DOSHA_MAP → should NOT fall back to domain default."""
        sense = SenseFrame(domain="body", symptom="stiff", keywords=["stiff"])
        result = get_symptom_from_sense(sense)
        assert result != "energy"

    def test_dizzy_found_via_dosha_map(self):
        """'dizzy' exists in SYMPTOM_DOSHA_MAP → should NOT fall back."""
        sense = SenseFrame(domain="body", symptom="dizzy", keywords=["dizzy"])
        result = get_symptom_from_sense(sense)
        assert result != "energy"

    def test_match_symptom_finds_dosha_map_entries(self):
        """match_symptom should find symptoms in SYMPTOM_DOSHA_MAP even without aliases."""
        assert match_symptom("bloating") is not None
        assert match_symptom("stiff") is not None
        assert match_symptom("dizzy") is not None
        assert match_symptom("foggy") is not None
        assert match_symptom("burnout") is not None

    def test_existing_diagnostic_paths_still_prioritized(self):
        """Headache has a DIAGNOSTIC_PATH and should still route there."""
        sense = SenseFrame(domain="body", sub_domain="head_neurological",
                          symptom="headache", keywords=["headache"])
        result = get_symptom_from_sense(sense)
        assert result in ("headache", "headaches")

    def test_dosha_map_is_broader_than_diagnostic_paths(self):
        """SYMPTOM_DOSHA_MAP should cover more symptoms than DIAGNOSTIC_PATHS."""
        assert len(SYMPTOM_DOSHA_MAP) > len(DIAGNOSTIC_PATHS)


# =============================================================================
# PERSONALIZED QUESTION GENERATION TESTS
# =============================================================================


class TestPersonalizedQuestions:
    """LLM-generated questions should use personal context."""

    def _make_sense(self, raw_text="my joints hurt", symptom="joints",
                    domain="body", sub_domain="musculoskeletal"):
        return SenseFrame(
            domain=domain, sub_domain=sub_domain, symptom=symptom,
            keywords=[symptom], raw_text=raw_text, temporal="unspecified",
        )

    def _make_constitution(self, os_type="Adaptive", dosha="vata"):
        return ConstitutionContext(
            operating_system=os_type,
            dominant_dosha=dosha,
            dosha_baseline={"vata": 0.45, "pitta": 0.30, "kapha": 0.25},
        )

    def _make_known_facts(self):
        return {
            "sleep": KnownFact(
                topic="sleep", value="sleeping only 5 hours lately",
                source="short_term", recency="recent", confidence=0.8,
            ),
            "stress": KnownFact(
                topic="stress", value="work deadline this week",
                source="episodic", recency="recent", confidence=0.7,
            ),
        }

    def _make_inferences(self):
        return {
            "vata_elevation": Inference(
                topic="vata_state",
                statement="Vata elevated 8% from baseline",
                basis="state_vector drift",
                confidence=0.7,
            ),
        }

    def _mock_llm_response(self):
        return json.dumps([
            {"id": "q1", "question": "Is the stiffness worse in the morning?",
             "priority": "high", "dosha_relevance": "vata",
             "why": "Vata stiffness is worse after inactivity"},
            {"id": "q2", "question": "Has this gotten worse with your shorter sleep?",
             "priority": "high", "dosha_relevance": "vata",
             "why": "Poor sleep worsens vata symptoms"},
            {"id": "q3", "question": "Is it the same joints or does it move around?",
             "priority": "medium", "dosha_relevance": "vata",
             "why": "Migrating joint pain is a classic vata pattern"},
        ])

    @pytest.mark.asyncio
    async def test_generates_questions_for_any_symptom(self):
        """Any symptom should get questions — no more empty []."""
        with patch("sakhi.apps.api.core.llm.call_llm",
                    new_callable=AsyncMock, return_value=self._mock_llm_response()):
            result = await generate_personalized_questions(
                self._make_sense(),
                self._make_constitution(),
                self._make_known_facts(),
                self._make_inferences(),
            )
            assert len(result) >= 2
            assert all(isinstance(q, DiagnosticQuestion) for q in result)

    @pytest.mark.asyncio
    async def test_known_facts_included_in_prompt(self):
        """LLM prompt should contain known facts so it doesn't re-ask."""
        captured_prompt = None

        async def capture_prompt(prompt, **kwargs):
            nonlocal captured_prompt
            captured_prompt = prompt
            return self._mock_llm_response()

        with patch("sakhi.apps.api.core.llm.call_llm",
                    side_effect=capture_prompt):
            await generate_personalized_questions(
                self._make_sense(),
                self._make_constitution(),
                self._make_known_facts(),
                self._make_inferences(),
            )
            assert captured_prompt is not None
            assert "sleeping only 5 hours" in captured_prompt
            assert "work deadline" in captured_prompt

    @pytest.mark.asyncio
    async def test_constitution_included_in_prompt(self):
        """LLM prompt should contain constitution info."""
        captured_prompt = None

        async def capture_prompt(prompt, **kwargs):
            nonlocal captured_prompt
            captured_prompt = prompt
            return self._mock_llm_response()

        with patch("sakhi.apps.api.core.llm.call_llm",
                    side_effect=capture_prompt):
            await generate_personalized_questions(
                self._make_sense(),
                self._make_constitution(os_type="Performance", dosha="pitta"),
                {},
                {},
            )
            assert captured_prompt is not None
            assert "Performance" in captured_prompt
            assert "pitta" in captured_prompt

    @pytest.mark.asyncio
    async def test_inferences_included_in_prompt(self):
        """LLM prompt should contain state vector inferences."""
        captured_prompt = None

        async def capture_prompt(prompt, **kwargs):
            nonlocal captured_prompt
            captured_prompt = prompt
            return self._mock_llm_response()

        with patch("sakhi.apps.api.core.llm.call_llm",
                    side_effect=capture_prompt):
            await generate_personalized_questions(
                self._make_sense(),
                self._make_constitution(),
                {},
                self._make_inferences(),
            )
            assert captured_prompt is not None
            assert "Vata elevated 8%" in captured_prompt

    @pytest.mark.asyncio
    async def test_llm_error_returns_empty_list(self):
        """LLM failure should gracefully return [] not crash."""
        with patch("sakhi.apps.api.core.llm.call_llm",
                    new_callable=AsyncMock, side_effect=Exception("LLM down")):
            result = await generate_personalized_questions(
                self._make_sense(),
                self._make_constitution(),
                {},
                {},
            )
            assert result == []

    @pytest.mark.asyncio
    async def test_handles_dict_response(self):
        """LLM returning a dict wrapper should still parse questions."""
        wrapped = json.dumps({"questions": [
            {"id": "q1", "question": "How long?", "priority": "high", "why": "timing"},
        ]})
        with patch("sakhi.apps.api.core.llm.call_llm",
                    new_callable=AsyncMock, return_value=wrapped):
            result = await generate_personalized_questions(
                self._make_sense(),
                self._make_constitution(),
                {},
                {},
            )
            assert len(result) == 1

    @pytest.mark.asyncio
    async def test_caps_at_three_questions(self):
        """Should never return more than 3 questions even if LLM returns more."""
        five_qs = json.dumps([
            {"id": f"q{i}", "question": f"Question {i}?", "priority": "medium", "why": "reason"}
            for i in range(5)
        ])
        with patch("sakhi.apps.api.core.llm.call_llm",
                    new_callable=AsyncMock, return_value=five_qs):
            result = await generate_personalized_questions(
                self._make_sense(),
                self._make_constitution(),
                {},
                {},
            )
            assert len(result) <= 3

    @pytest.mark.asyncio
    async def test_no_known_facts_states_that(self):
        """When we have no known facts, prompt should say so."""
        captured_prompt = None

        async def capture_prompt(prompt, **kwargs):
            nonlocal captured_prompt
            captured_prompt = prompt
            return self._mock_llm_response()

        with patch("sakhi.apps.api.core.llm.call_llm",
                    side_effect=capture_prompt):
            await generate_personalized_questions(
                self._make_sense(),
                self._make_constitution(),
                {},  # No known facts
                {},
            )
            assert "don't have any context about this person yet" in captured_prompt


# =============================================================================
# DATA PIPELINE FLOW TESTS
# =============================================================================
# These tests mock the DB layer (not the data) to verify that real DB rows
# actually flow through to the LLM prompt. Catches the "empty data passed
# silently" problem.


class TestConstitutionLoading:
    """Verify load_constitution_context extracts data correctly from DB rows."""

    @pytest.mark.asyncio
    async def test_extracts_os_type_from_jsonb(self):
        """personal_model.operating_system JSONB → ctx.operating_system string."""
        mock_row = {
            "operating_system": {
                "type": "Adaptive-Performance",
                "dosha_baseline": {"vata": 0.45, "pitta": 0.30, "kapha": 0.25},
            },
            "life_context": {"occupation": "engineer"},
            "decision_profile": None,
        }
        with patch("sakhi.apps.api.services.response.knowledge_gap.q",
                    new_callable=AsyncMock, return_value=mock_row):
            from sakhi.apps.api.services.response.knowledge_gap import load_constitution_context
            ctx = await load_constitution_context("test-user")
            assert ctx.operating_system == "Adaptive-Performance"
            assert ctx.dominant_dosha == "vata"  # 0.45 > 0.35 threshold
            assert ctx.dosha_baseline == {"vata": 0.45, "pitta": 0.30, "kapha": 0.25}
            assert ctx.life_context == {"occupation": "engineer"}

    @pytest.mark.asyncio
    async def test_handles_string_jsonb(self):
        """asyncpg returns JSONB as string — must parse correctly."""
        import json as _json
        mock_row = {
            "operating_system": _json.dumps({
                "type": "Conservation",
                "dosha_baseline": {"vata": 0.20, "pitta": 0.25, "kapha": 0.55},
            }),
            "life_context": _json.dumps({"city": "Mumbai"}),
            "decision_profile": None,
        }
        with patch("sakhi.apps.api.services.response.knowledge_gap.q",
                    new_callable=AsyncMock, return_value=mock_row):
            from sakhi.apps.api.services.response.knowledge_gap import load_constitution_context
            ctx = await load_constitution_context("test-user")
            assert ctx.operating_system == "Conservation"
            assert ctx.dominant_dosha == "kapha"  # 0.55 > 0.35
            assert ctx.life_context == {"city": "Mumbai"}

    @pytest.mark.asyncio
    async def test_empty_row_returns_defaults(self):
        """No personal_model row → defaults, not crash."""
        with patch("sakhi.apps.api.services.response.knowledge_gap.q",
                    new_callable=AsyncMock, return_value=None):
            from sakhi.apps.api.services.response.knowledge_gap import load_constitution_context
            ctx = await load_constitution_context("test-user")
            assert ctx.operating_system is None
            assert ctx.dominant_dosha == "balanced"
            assert ctx.dosha_baseline == {}

    @pytest.mark.asyncio
    async def test_db_error_returns_defaults(self):
        """DB exception → defaults, not crash."""
        with patch("sakhi.apps.api.services.response.knowledge_gap.q",
                    new_callable=AsyncMock, side_effect=Exception("DB down")):
            from sakhi.apps.api.services.response.knowledge_gap import load_constitution_context
            ctx = await load_constitution_context("test-user")
            assert ctx.operating_system is None
            assert ctx.dominant_dosha == "balanced"


class TestStateVectorLoading:
    """Verify load_state_vectors computes drift and guna mode from DB rows."""

    @pytest.mark.asyncio
    async def test_computes_drift_from_state_vector(self):
        """State vector dosha values → drift from baseline."""
        mock_rows = [{
            "state_vector": {"dosha": {"vata": 0.55, "pitta": 0.25, "kapha": 0.20}},
            "guna_vector": {"sattva": 0.3, "rajas": 0.5, "tamas": 0.2},
            "created_at": "2024-01-01",
        }]
        ctx = ConstitutionContext(
            dosha_baseline={"vata": 0.45, "pitta": 0.30, "kapha": 0.25},
        )
        with patch("sakhi.apps.api.services.response.knowledge_gap.q",
                    new_callable=AsyncMock, return_value=mock_rows):
            await load_state_vectors("test-user", ctx)
            assert ctx.drift["vata"] == 0.1  # 0.55 - 0.45
            assert ctx.drift["pitta"] == -0.05  # 0.25 - 0.30
            assert ctx.guna_mode == "rajas"  # highest at 0.5

    @pytest.mark.asyncio
    async def test_no_state_vectors_leaves_defaults(self):
        """No episodic entries → drift stays empty, guna stays sattva."""
        ctx = ConstitutionContext(
            dosha_baseline={"vata": 0.45, "pitta": 0.30, "kapha": 0.25},
        )
        with patch("sakhi.apps.api.services.response.knowledge_gap.q",
                    new_callable=AsyncMock, return_value=[]):
            await load_state_vectors("test-user", ctx)
            assert ctx.drift == {}
            assert ctx.guna_mode == "sattva"  # default

    @pytest.mark.asyncio
    async def test_string_state_vector_parsed_correctly(self):
        """asyncpg returns JSONB as string — must json.loads before computing drift."""
        mock_rows = [{
            "state_vector": '{"dosha": {"vata": 0.55, "pitta": 0.28, "kapha": 0.17}}',
            "guna_vector": '{"sattva": 0.2, "rajas": 0.6, "tamas": 0.2}',
            "created_at": "2024-01-01",
        }]
        ctx = ConstitutionContext(
            dosha_baseline={"vata": 0.45, "pitta": 0.30, "kapha": 0.25},
        )
        with patch("sakhi.apps.api.services.response.knowledge_gap.q",
                    new_callable=AsyncMock, return_value=mock_rows):
            await load_state_vectors("test-user", ctx)
            assert ctx.drift["vata"] == 0.1  # 0.55 - 0.45
            assert ctx.guna_mode == "rajas"


class TestInferenceGeneration:
    """Verify inferences are generated from drift and guna mode."""

    def test_vata_elevation_generates_inference(self):
        """Vata drift > 5% → inference about irregularity."""
        ctx = ConstitutionContext(
            drift={"vata": 0.08, "pitta": 0.01, "kapha": -0.02},
            guna_mode="sattva",
        )
        sense = SenseFrame(domain="body", symptom="headache", keywords=["headache"])
        from sakhi.apps.api.services.response.knowledge_gap import generate_inferences
        inferences = generate_inferences(ctx, sense)
        assert "vata_elevation" in inferences
        assert "8%" in inferences["vata_elevation"].statement

    def test_rajas_mode_generates_inference(self):
        """Rajas guna → inference about high activation."""
        ctx = ConstitutionContext(drift={}, guna_mode="rajas")
        sense = SenseFrame(domain="body", symptom="headache", keywords=["headache"])
        from sakhi.apps.api.services.response.knowledge_gap import generate_inferences
        inferences = generate_inferences(ctx, sense)
        assert "rajas_mode" in inferences

    def test_no_drift_no_inferences(self):
        """Empty drift + sattva guna → no inferences."""
        ctx = ConstitutionContext(drift={}, guna_mode="sattva")
        sense = SenseFrame(domain="body", symptom="headache", keywords=["headache"])
        from sakhi.apps.api.services.response.knowledge_gap import generate_inferences
        inferences = generate_inferences(ctx, sense)
        assert inferences == {}


class TestSTMSearch:
    """Verify search_short_term_memory finds matching rows."""

    @pytest.mark.asyncio
    async def test_keyword_match_returns_fact(self):
        """STM row containing keyword → returns KnownFact."""
        mock_rows = [
            {"text": "I've been sleeping only 5 hours this week", "created_at": "2024-01-01"},
            {"text": "had a good lunch today", "created_at": "2024-01-01"},
        ]
        with patch("sakhi.apps.api.services.response.knowledge_gap.q",
                    new_callable=AsyncMock, return_value=mock_rows):
            fact = await search_short_term_memory("test-user", "sleep", ["sleep", "tired"])
            assert fact is not None
            assert fact.topic == "sleep"
            assert "sleeping only 5 hours" in fact.value
            assert fact.source == "short_term"

    @pytest.mark.asyncio
    async def test_no_keyword_match_returns_none(self):
        """STM rows without keyword → None."""
        mock_rows = [
            {"text": "had a good lunch today", "created_at": "2024-01-01"},
        ]
        with patch("sakhi.apps.api.services.response.knowledge_gap.q",
                    new_callable=AsyncMock, return_value=mock_rows):
            fact = await search_short_term_memory("test-user", "sleep", ["sleep", "tired"])
            assert fact is None

    @pytest.mark.asyncio
    async def test_empty_stm_returns_none(self):
        """No STM rows → None."""
        with patch("sakhi.apps.api.services.response.knowledge_gap.q",
                    new_callable=AsyncMock, return_value=[]):
            fact = await search_short_term_memory("test-user", "sleep", ["sleep"])
            assert fact is None


class TestPipelineDataFlow:
    """End-to-end: verify data flows from DB mocks through to the LLM prompt."""

    @pytest.mark.asyncio
    async def test_full_pipeline_passes_real_data_to_llm(self):
        """
        Mock DB + LLM. Verify the LLM prompt contains data from ALL sources:
        - Constitution (from personal_model)
        - Recent STM entries (keyword-free — all recent entries)
        - Inferences (from state vector drift)
        """
        async def mock_q(sql, *args, **kwargs):
            sql_lower = sql.lower().strip()

            if "personal_model" in sql_lower:
                return {
                    "operating_system": {
                        "type": "Adaptive",
                        "dosha_baseline": {"vata": 0.45, "pitta": 0.30, "kapha": 0.25},
                    },
                    "life_context": {},
                    "decision_profile": None,
                }
            elif "memory_episodic" in sql_lower:
                return [{
                    "state_vector": {"dosha": {"vata": 0.55, "pitta": 0.28, "kapha": 0.17}},
                    "guna_vector": {"sattva": 0.2, "rajas": 0.6, "tamas": 0.2},
                    "created_at": "2024-01-01",
                }]
            elif "memory_short_term" in sql_lower:
                return [
                    {"text": "I've been sleeping poorly, only 4 hours"},
                    {"text": "work has been very stressful this week"},
                    {"text": "skipped breakfast again"},
                ]
            return []

        captured_prompt = None
        async def mock_llm(prompt, **kwargs):
            nonlocal captured_prompt
            captured_prompt = prompt
            return json.dumps([
                {"id": "q1", "question": "Test question?", "priority": "high", "why": "reason"},
            ])

        async def mock_recall(*args, **kwargs):
            return []

        sense = SenseFrame(
            domain="body", sub_domain="head_neurological",
            symptom="headache", keywords=["headache"],
            raw_text="I have a headache",
            temporal="acute", tone="seeking_help",
        )

        with patch("sakhi.apps.api.services.response.knowledge_gap.q", side_effect=mock_q), \
             patch("sakhi.apps.api.core.llm.call_llm", side_effect=mock_llm), \
             patch("sakhi.apps.api.services.response.knowledge_gap.recall_advanced", side_effect=mock_recall):

            from sakhi.apps.api.services.response.knowledge_gap import analyze_knowledge_gap
            gap = await analyze_knowledge_gap("test-user", sense)

            # Verify constitution was loaded
            assert gap.constitution.operating_system == "Adaptive"
            assert gap.constitution.dominant_dosha == "vata"

            # Verify drift was computed
            assert gap.constitution.drift["vata"] == 0.1  # 0.55 - 0.45
            assert gap.constitution.guna_mode == "rajas"

            # Verify known facts from recent STM (keyword-free)
            assert len(gap.known) >= 3, f"Expected 3+ known facts, got {len(gap.known)}: {list(gap.known.keys())}"
            all_values = " ".join(f.value.lower() for f in gap.known.values())
            assert "sleeping poorly" in all_values, f"STM entries not in known facts: {all_values}"
            assert "stressful" in all_values, f"STM entries not in known facts: {all_values}"
            assert "breakfast" in all_values, f"STM entries not in known facts: {all_values}"

            # Verify inferences were generated
            assert "vata_elevation" in gap.inferred
            assert "rajas_mode" in gap.inferred

            # Verify LLM was called with all the data
            assert captured_prompt is not None, "LLM was never called!"
            assert "Adaptive" in captured_prompt, "OS type missing from prompt"
            assert "vata" in captured_prompt, "Dosha missing from prompt"
            assert "sleeping poorly" in captured_prompt, "Recent STM missing from prompt"
            assert "stressful" in captured_prompt, "Recent STM missing from prompt"
            assert "Vata elevated" in captured_prompt, "Inferences missing from prompt"

            # Verify questions were returned
            assert len(gap.unknown) > 0, "No questions generated!"

    @pytest.mark.asyncio
    async def test_empty_db_still_generates_questions(self):
        """Even with no personal data, LLM should still generate questions."""
        async def mock_q(sql, *args, **kwargs):
            if "one" in str(kwargs):
                return None
            return []

        async def mock_llm(prompt, **kwargs):
            return json.dumps([
                {"id": "q1", "question": "Can you tell me more?", "priority": "high", "why": "no context"},
            ])

        async def mock_recall(*args, **kwargs):
            return []

        sense = SenseFrame(
            domain="body", symptom="joints", keywords=["joints"],
            raw_text="my joints hurt",
        )

        with patch("sakhi.apps.api.services.response.knowledge_gap.q", side_effect=mock_q), \
             patch("sakhi.apps.api.core.llm.call_llm", side_effect=mock_llm), \
             patch("sakhi.apps.api.services.response.knowledge_gap.recall_advanced", side_effect=mock_recall):

            from sakhi.apps.api.services.response.knowledge_gap import analyze_knowledge_gap
            gap = await analyze_knowledge_gap("test-user", sense)

            # Even with empty data, should still work
            assert gap.constitution.dominant_dosha == "balanced"
            assert gap.known == {}
            assert gap.inferred == {}
            # But questions should still be generated
            assert len(gap.unknown) > 0


# =============================================================================
# DETERMINISTIC INTELLIGENCE INTEGRATION TESTS
# =============================================================================


class TestDeterministicIntelligence:
    """Tests for wiring deterministic intelligence into the knowledge gap pipeline."""

    def test_patterns_become_inferences(self):
        """Personal patterns should appear as Inferences in KnowledgeGap."""
        gap = KnowledgeGap()
        det_intel = {
            "symptom_dosha": None,
            "patterns": [
                {
                    "cause_value": "late_dinner",
                    "effect_value": "scattered",
                    "correlation_strength": 0.8,
                    "observation_count": 8,
                    "ayurvedic_explanation": "late eating aggravates vata",
                },
                {
                    "cause_value": "caffeine_evening",
                    "effect_value": "insomnia",
                    "correlation_strength": 0.65,
                    "observation_count": 4,
                    "ayurvedic_explanation": "",
                },
            ],
            "behaviors": [],
            "past_episodes": [],
        }

        _integrate_deterministic_intelligence(gap, det_intel)

        assert "pattern_0" in gap.inferred
        assert "pattern_1" in gap.inferred
        assert "late_dinner" in gap.inferred["pattern_0"].statement
        assert "scattered" in gap.inferred["pattern_0"].statement
        assert "8x" in gap.inferred["pattern_0"].statement
        assert "80%" in gap.inferred["pattern_0"].statement
        assert "late eating aggravates vata" in gap.inferred["pattern_0"].statement
        assert gap.inferred["pattern_0"].topic == "personal_pattern"
        assert gap.inferred["pattern_0"].basis == "personal_patterns"
        assert gap.inferred["pattern_0"].confidence == 0.8

        # Second pattern — no explanation
        assert "caffeine_evening" in gap.inferred["pattern_1"].statement
        assert gap.inferred["pattern_1"].confidence == 0.65

    def test_behaviors_become_known_facts(self):
        """Recent behaviors should appear as KnownFacts in KnowledgeGap."""
        gap = KnowledgeGap()
        det_intel = {
            "symptom_dosha": None,
            "patterns": [],
            "behaviors": [
                {
                    "behavior_name": "caffeine_evening",
                    "dosha_effect": "vata",
                    "effect_direction": "aggravate",
                    "occurred_at": None,
                },
                {
                    "behavior_name": "skipped_lunch",
                    "dosha_effect": "pitta",
                    "effect_direction": "aggravate",
                    "occurred_at": None,
                },
            ],
            "past_episodes": [],
        }

        _integrate_deterministic_intelligence(gap, det_intel)

        assert "behavior_0" in gap.known
        assert "behavior_1" in gap.known
        fact0 = gap.known["behavior_0"]
        assert fact0.topic == "recent_behavior"
        assert fact0.source == "behavior_log"
        assert fact0.recency == "recent"
        assert fact0.confidence == 0.9
        assert "caffeine_evening" in fact0.value
        assert "aggravates vata" in fact0.value

        fact1 = gap.known["behavior_1"]
        assert "skipped_lunch" in fact1.value
        assert "aggravates pitta" in fact1.value

    def test_past_episodes_with_what_helped(self):
        """Past symptom episodes should include what helped/didn't help."""
        gap = KnowledgeGap()
        det_intel = {
            "symptom_dosha": None,
            "patterns": [],
            "behaviors": [],
            "past_episodes": [
                {
                    "symptom_name": "scattered",
                    "severity": 0.7,
                    "occurred_at": "2026-02-10",
                    "what_helped": json.dumps(["meditation", "warm tea"]),
                    "what_didnt_help": json.dumps(["coffee"]),
                    "source_text": "felt scattered",
                    "likely_dosha": "vata",
                },
            ],
        }

        _integrate_deterministic_intelligence(gap, det_intel)

        assert "past_episode_0" in gap.known
        ep = gap.known["past_episode_0"]
        assert ep.topic == "past_episode"
        assert ep.source == "symptom_log"
        assert ep.recency == "moderate"
        assert ep.confidence == 0.85
        assert "scattered" in ep.value
        assert "severity 0.7" in ep.value
        assert "meditation" in ep.value
        assert "warm tea" in ep.value
        assert "coffee" in ep.value
        assert "Didn't help" in ep.value

    def test_past_episodes_jsonb_already_parsed(self):
        """what_helped as already-parsed list (not JSON string) should work."""
        gap = KnowledgeGap()
        det_intel = {
            "symptom_dosha": None,
            "patterns": [],
            "behaviors": [],
            "past_episodes": [
                {
                    "symptom_name": "headache",
                    "severity": 0.5,
                    "occurred_at": None,
                    "what_helped": ["rest", "dark room"],
                    "what_didnt_help": None,
                    "source_text": "",
                    "likely_dosha": "pitta",
                },
            ],
        }

        _integrate_deterministic_intelligence(gap, det_intel)

        ep = gap.known["past_episode_0"]
        assert "rest" in ep.value
        assert "dark room" in ep.value

    def test_symptom_dosha_mapping(self):
        """Symptom should be mapped to dosha via deterministic map."""
        gap = KnowledgeGap()
        det_intel = {
            "symptom_dosha": "vata",
            "patterns": [],
            "behaviors": [],
            "past_episodes": [],
        }

        _integrate_deterministic_intelligence(gap, det_intel)

        assert "symptom_dosha" in gap.inferred
        inf = gap.inferred["symptom_dosha"]
        assert inf.topic == "symptom_classification"
        assert "vata" in inf.statement
        assert inf.basis == "symptom_dosha_map"
        assert inf.confidence == 0.8

    def test_no_dosha_when_none(self):
        """No symptom_dosha inference when dosha is None."""
        gap = KnowledgeGap()
        det_intel = {
            "symptom_dosha": None,
            "patterns": [],
            "behaviors": [],
            "past_episodes": [],
        }

        _integrate_deterministic_intelligence(gap, det_intel)

        assert "symptom_dosha" not in gap.inferred

    def test_empty_tables_graceful(self):
        """Empty behavior_log/symptom_log/patterns should not crash."""
        gap = KnowledgeGap()
        det_intel = {
            "symptom_dosha": None,
            "patterns": [],
            "behaviors": [],
            "past_episodes": [],
        }

        _integrate_deterministic_intelligence(gap, det_intel)

        # No known facts or inferences from det intel
        assert len(gap.known) == 0
        assert len(gap.inferred) == 0

    def test_max_limits_respected(self):
        """Should cap at 5 patterns, 5 behaviors, 3 episodes."""
        gap = KnowledgeGap()
        det_intel = {
            "symptom_dosha": None,
            "patterns": [
                {"cause_value": f"cause_{i}", "effect_value": f"effect_{i}",
                 "correlation_strength": 0.5, "observation_count": 1, "ayurvedic_explanation": ""}
                for i in range(10)
            ],
            "behaviors": [
                {"behavior_name": f"behavior_{i}", "dosha_effect": "vata",
                 "effect_direction": "aggravate", "occurred_at": None}
                for i in range(10)
            ],
            "past_episodes": [
                {"symptom_name": f"symptom_{i}", "severity": 0.5, "occurred_at": None,
                 "what_helped": None, "what_didnt_help": None, "source_text": "", "likely_dosha": "vata"}
                for i in range(10)
            ],
        }

        _integrate_deterministic_intelligence(gap, det_intel)

        pattern_keys = [k for k in gap.inferred if k.startswith("pattern_")]
        behavior_keys = [k for k in gap.known if k.startswith("behavior_")]
        episode_keys = [k for k in gap.known if k.startswith("past_episode_")]

        assert len(pattern_keys) == 5
        assert len(behavior_keys) == 5
        assert len(episode_keys) == 3

    @pytest.mark.asyncio
    async def test_patterns_in_llm_prompt(self):
        """Deterministic patterns should appear in LLM question prompt."""
        captured_prompt = []

        async def mock_llm(prompt, **kwargs):
            captured_prompt.append(prompt)
            return json.dumps([
                {"id": "q1", "question": "Has anything changed?", "priority": "high", "why": "probe trigger"},
            ])

        sense = SenseFrame(
            domain="body", symptom="scattered", keywords=["scattered"],
            raw_text="I feel scattered",
        )
        constitution = ConstitutionContext(
            operating_system="Adaptive-Performance",
            dominant_dosha="vata",
        )
        known = {
            "behavior_0": KnownFact(
                topic="recent_behavior",
                value="caffeine_evening (aggravates vata)",
                source="behavior_log",
                recency="recent",
                confidence=0.9,
            ),
            "past_episode_0": KnownFact(
                topic="past_episode",
                value="Had scattered (severity 0.7). What helped: meditation",
                source="symptom_log",
                recency="moderate",
                confidence=0.85,
            ),
        }
        inferred = {
            "pattern_0": Inference(
                topic="personal_pattern",
                statement="Known pattern: caffeine → scattered (observed 8x, strength 80%)",
                basis="personal_patterns",
                confidence=0.8,
            ),
            "symptom_dosha": Inference(
                topic="symptom_classification",
                statement="This symptom is associated with vata tendency",
                basis="symptom_dosha_map",
                confidence=0.8,
            ),
        }

        with patch("sakhi.apps.api.core.llm.call_llm", side_effect=mock_llm):
            questions = await generate_personalized_questions(sense, constitution, known, inferred)

        assert len(captured_prompt) == 1
        prompt = captured_prompt[0]

        # Structured sections should appear
        assert "Recent behaviors (last 48h):" in prompt
        assert "caffeine_evening" in prompt
        assert "Past episodes of this symptom:" in prompt
        assert "meditation" in prompt
        assert "Learned personal patterns:" in prompt
        assert "caffeine → scattered" in prompt
        assert "Symptom classification:" in prompt
        assert "vata tendency" in prompt

    @pytest.mark.asyncio
    async def test_load_deterministic_intelligence(self):
        """_load_deterministic_intelligence should load patterns, behaviors, episodes in parallel."""
        from sakhi.apps.api.services.response.knowledge_gap import _load_deterministic_intelligence

        mock_behaviors = AsyncMock(return_value=[
            {"behavior_name": "late_meal", "dosha_effect": "kapha",
             "effect_direction": "aggravate", "occurred_at": None},
        ])

        # q is called by both _get_personal_patterns_for_symptom and _get_past_symptom_episodes
        call_count = 0

        async def mock_q(sql, *args, **kwargs):
            nonlocal call_count
            call_count += 1
            if "personal_patterns" in sql:
                return [{"cause_type": "food", "cause_value": "caffeine",
                         "effect_type": "mental", "effect_value": "insomnia",
                         "correlation_strength": 0.7, "confidence": 0.7,
                         "observation_count": 5, "ayurvedic_explanation": "",
                         "related_dosha": "vata"}]
            if "symptom_log" in sql:
                return []
            return []

        sense = SenseFrame(
            domain="body", symptom="insomnia", keywords=["insomnia"],
            raw_text="can't sleep",
        )

        with patch("sakhi.apps.api.services.response.knowledge_gap.q", side_effect=mock_q), \
             patch("sakhi.apps.api.services.ayurveda.causal_reasoning.get_recent_behaviors", mock_behaviors):

            result = await _load_deterministic_intelligence("test-user", sense)

        assert result["symptom_dosha"] is not None  # insomnia should map to a dosha
        assert len(result["patterns"]) == 1
        assert result["patterns"][0]["cause_value"] == "caffeine"
        assert len(result["behaviors"]) == 1
        mock_behaviors.assert_called_once_with("test-user", hours_back=168)

    @pytest.mark.asyncio
    async def test_load_deterministic_intelligence_no_symptom(self):
        """With no symptom, pattern/episode queries should be skipped."""
        from sakhi.apps.api.services.response.knowledge_gap import _load_deterministic_intelligence

        mock_behaviors = AsyncMock(return_value=[])
        q_called = False

        async def mock_q(sql, *args, **kwargs):
            nonlocal q_called
            q_called = True
            return []

        sense = SenseFrame(
            domain="general", sub_domain="", symptom="", keywords=[],
            raw_text="how are you?",
        )

        with patch("sakhi.apps.api.services.ayurveda.causal_reasoning.get_recent_behaviors", mock_behaviors), \
             patch("sakhi.apps.api.services.response.knowledge_gap.q", side_effect=mock_q):

            result = await _load_deterministic_intelligence("test-user", sense)

        # No symptom → patterns and episodes should be empty (skipped via _empty())
        assert result["symptom_dosha"] is None
        assert result["patterns"] == []
        assert result["past_episodes"] == []
        # Behaviors always loaded (not symptom-specific)
        mock_behaviors.assert_called_once()
        # q should NOT be called (patterns and episodes use _empty() when no symptom)
        assert not q_called

    @pytest.mark.asyncio
    async def test_load_deterministic_intelligence_error_graceful(self):
        """DB errors should return empty results, not crash."""
        from sakhi.apps.api.services.response.knowledge_gap import _load_deterministic_intelligence

        sense = SenseFrame(
            domain="body", symptom="headache", keywords=["headache"],
            raw_text="I have a headache",
        )

        with patch("sakhi.apps.api.services.ayurveda.causal_reasoning.get_recent_behaviors",
                    side_effect=Exception("DB connection failed")), \
             patch("sakhi.apps.api.services.response.knowledge_gap.q",
                    side_effect=Exception("DB connection failed")):

            result = await _load_deterministic_intelligence("test-user", sense)

        assert result["patterns"] == []
        assert result["behaviors"] == []
        assert result["past_episodes"] == []


class TestPastSymptomEpisodes:
    """Tests for _get_past_symptom_episodes() DB helper."""

    @pytest.mark.asyncio
    async def test_returns_episodes(self):
        """Should return parsed episode dicts from DB rows."""
        mock_rows = [
            {"symptom_name": "headache", "severity": 0.7, "occurred_at": "2026-02-10",
             "what_helped": json.dumps(["rest"]), "what_didnt_help": None,
             "source_text": "bad headache", "likely_dosha": "pitta"},
        ]

        async def mock_q(sql, *args, **kwargs):
            return mock_rows

        with patch("sakhi.apps.api.services.response.knowledge_gap.q", side_effect=mock_q):
            result = await _get_past_symptom_episodes("test-user", "headache", limit=3)

        assert len(result) == 1
        assert result[0]["symptom_name"] == "headache"
        assert result[0]["severity"] == 0.7

    @pytest.mark.asyncio
    async def test_ilike_pattern(self):
        """Should pass ILIKE pattern with % wildcards."""
        captured_args = []

        async def mock_q(sql, *args, **kwargs):
            captured_args.extend(args)
            return []

        with patch("sakhi.apps.api.services.response.knowledge_gap.q", side_effect=mock_q):
            await _get_past_symptom_episodes("test-user", "headache", limit=3)

        # Args: person_id, pattern, limit
        assert captured_args[1] == "%headache%"

    @pytest.mark.asyncio
    async def test_db_error_returns_empty(self):
        """DB failure should return [] not crash."""
        async def mock_q(sql, *args, **kwargs):
            raise Exception("connection timeout")

        with patch("sakhi.apps.api.services.response.knowledge_gap.q", side_effect=mock_q):
            result = await _get_past_symptom_episodes("test-user", "headache")

        assert result == []

    @pytest.mark.asyncio
    async def test_empty_result(self):
        """No matching rows should return empty list."""
        async def mock_q(sql, *args, **kwargs):
            return []

        with patch("sakhi.apps.api.services.response.knowledge_gap.q", side_effect=mock_q):
            result = await _get_past_symptom_episodes("test-user", "nonexistent")

        assert result == []
