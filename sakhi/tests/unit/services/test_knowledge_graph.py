"""
Unit tests for Ayurvedic Knowledge Graph services.
"""

from datetime import datetime, timezone
import pytest
from unittest.mock import AsyncMock, patch


# =============================================================================
# Graph Reasoning Tests
# =============================================================================

class TestGraphReasoning:
    """Tests for graph_reasoning.py functions."""

    @pytest.mark.asyncio
    async def test_query_foods_for_dosha_returns_citations(self):
        """Foods query should include citations from classical texts."""
        mock_results = [
            {
                "name": "ginger",
                "name_sanskrit": "Shunti",
                "display_name": "Ginger",
                "attrs": '{"rasa": "katu", "virya": "ushna"}',
                "citations": '[{"source": "charaka_samhita", "chapter": "sutrasthana.27"}]',
                "confidence": 0.9,
                "weight": 0.85,
            }
        ]

        with patch("sakhi.apps.api.services.ayurveda.graph_reasoning.dbfetch", new_callable=AsyncMock) as mock_db:
            mock_db.return_value = mock_results

            from sakhi.apps.api.services.ayurveda.graph_reasoning import query_foods_for_dosha

            foods = await query_foods_for_dosha("vata", "PACIFIES", limit=5)

            assert len(foods) == 1
            assert foods[0]["name"] == "ginger"
            assert foods[0]["name_sanskrit"] == "Shunti"
            assert foods[0]["rasa"] == "katu"
            assert foods[0]["virya"] == "ushna"
            assert len(foods[0]["citations"]) > 0
            assert foods[0]["citations"][0]["source"] == "charaka_samhita"

    @pytest.mark.asyncio
    async def test_query_practices_for_dosha(self):
        """Practices query should include Sanskrit names and benefits."""
        mock_results = [
            {
                "name": "pranayama",
                "name_sanskrit": "Pranayama",
                "display_name": "Pranayama",
                "attrs": '{"type": "breathing", "intensity": "gentle", "duration_min": 15, "benefits": ["calms mind"]}',
                "citations": '[]',
                "confidence": 0.85,
                "weight": 0.9,
            }
        ]

        with patch("sakhi.apps.api.services.ayurveda.graph_reasoning.dbfetch", new_callable=AsyncMock) as mock_db:
            mock_db.return_value = mock_results

            from sakhi.apps.api.services.ayurveda.graph_reasoning import query_practices_for_dosha

            practices = await query_practices_for_dosha("vata", limit=5)

            assert len(practices) == 1
            assert practices[0]["name"] == "pranayama"
            assert practices[0]["type"] == "breathing"
            assert practices[0]["intensity"] == "gentle"
            assert practices[0]["duration_min"] == 15
            assert "calms mind" in practices[0]["benefits"]

    @pytest.mark.asyncio
    async def test_query_symptoms_for_dosha(self):
        """Symptoms query should include severity and category."""
        mock_results = [
            {
                "name": "anxiety",
                "name_sanskrit": "Chinta",
                "display_name": "Anxiety",
                "attrs": '{"severity": "moderate", "category": "mental"}',
                "citations": '[{"source": "ashtanga_hridaya"}]',
                "confidence": 0.8,
                "weight": 0.85,
            }
        ]

        with patch("sakhi.apps.api.services.ayurveda.graph_reasoning.dbfetch", new_callable=AsyncMock) as mock_db:
            mock_db.return_value = mock_results

            from sakhi.apps.api.services.ayurveda.graph_reasoning import query_symptoms_for_dosha

            symptoms = await query_symptoms_for_dosha("vata", limit=5)

            assert len(symptoms) == 1
            assert symptoms[0]["name"] == "anxiety"
            assert symptoms[0]["severity"] == "moderate"
            assert symptoms[0]["category"] == "mental"

    @pytest.mark.asyncio
    async def test_query_asanas_for_dosha(self):
        """Asanas query should include benefits, level, and contraindications."""
        mock_results = [
            {
                "name": "shavasana",
                "name_sanskrit": "Shavasana",
                "display_name": "Corpse Pose",
                "attrs": '{"category": "restorative", "level": "beginner", "benefits": ["calms nervous system", "reduces stress"], "contraindications": [], "chakra_activation": ["anahata"]}',
                "citations": '[{"source": "hatha_yoga_pradipika", "chapter": "1.34"}]',
                "confidence": 0.9,
                "weight": 0.85,
            }
        ]

        with patch("sakhi.apps.api.services.ayurveda.graph_reasoning.dbfetch", new_callable=AsyncMock) as mock_db:
            mock_db.return_value = mock_results

            from sakhi.apps.api.services.ayurveda.graph_reasoning import query_asanas_for_dosha

            asanas = await query_asanas_for_dosha("vata", limit=5)

            assert len(asanas) == 1
            assert asanas[0]["name"] == "shavasana"
            assert asanas[0]["name_sanskrit"] == "Shavasana"
            assert asanas[0]["category"] == "restorative"
            assert asanas[0]["level"] == "beginner"
            assert "calms nervous system" in asanas[0]["benefits"]
            assert len(asanas[0]["citations"]) > 0

    @pytest.mark.asyncio
    async def test_query_asanas_filters_by_level(self):
        """Asanas query should filter by level when specified."""
        mock_results = [
            {
                "name": "shavasana",
                "name_sanskrit": "Shavasana",
                "display_name": "Corpse Pose",
                "attrs": '{"category": "restorative", "level": "beginner", "benefits": []}',
                "citations": '[]',
                "confidence": 0.9,
                "weight": 0.85,
            },
            {
                "name": "viparita_karani",
                "name_sanskrit": "Viparita Karani",
                "display_name": "Legs Up The Wall",
                "attrs": '{"category": "inversion", "level": "intermediate", "benefits": []}',
                "citations": '[]',
                "confidence": 0.85,
                "weight": 0.8,
            }
        ]

        with patch("sakhi.apps.api.services.ayurveda.graph_reasoning.dbfetch", new_callable=AsyncMock) as mock_db:
            mock_db.return_value = mock_results

            from sakhi.apps.api.services.ayurveda.graph_reasoning import query_asanas_for_dosha

            # Filter for beginner only
            asanas = await query_asanas_for_dosha("vata", level="beginner", limit=5)

            assert len(asanas) == 1
            assert asanas[0]["name"] == "shavasana"
            assert asanas[0]["level"] == "beginner"


# =============================================================================
# Causal Reasoning Tests
# =============================================================================

class TestCausalReasoning:
    """Tests for causal_reasoning.py functions."""

    def test_map_symptom_to_dosha(self):
        """Should map common symptoms to correct doshas."""
        from sakhi.apps.api.services.ayurveda.causal_reasoning import map_symptom_to_dosha

        # Vata symptoms
        assert map_symptom_to_dosha("anxiety") == "vata"
        assert map_symptom_to_dosha("scattered") == "vata"
        assert map_symptom_to_dosha("restless") == "vata"

        # Pitta symptoms
        assert map_symptom_to_dosha("irritable") == "pitta"
        assert map_symptom_to_dosha("angry") == "pitta"
        assert map_symptom_to_dosha("inflammation") == "pitta"

        # Kapha symptoms
        assert map_symptom_to_dosha("lethargic") == "kapha"
        assert map_symptom_to_dosha("heavy") == "kapha"
        assert map_symptom_to_dosha("congestion") == "kapha"

    @pytest.mark.asyncio
    async def test_get_ayurvedic_causes_returns_citations(self):
        """Causes query should include citations when available."""
        mock_symptom = {
            "id": 1,
            "name": "anxiety",
            "name_sanskrit": "Chinta",
            "attrs": "{}",
            "citations": '[{"source": "charaka_samhita"}]',
        }

        mock_causes = [
            {
                "name": "late_night",
                "name_sanskrit": None,
                "kind": "behavior",
                "attrs": "{}",
                "citations": '[{"source": "ashtanga_hridaya", "chapter": "sutrasthana.4"}]',
                "weight": 0.8,
            }
        ]

        with patch("sakhi.apps.api.services.ayurveda.causal_reasoning.dbfetch", new_callable=AsyncMock) as mock_db:
            # First call returns symptom, second returns causes
            mock_db.side_effect = [mock_symptom, mock_causes]

            from sakhi.apps.api.services.ayurveda.causal_reasoning import get_ayurvedic_causes_for_symptom

            causes = await get_ayurvedic_causes_for_symptom("anxiety", "vata")

            assert len(causes) == 1
            assert causes[0]["name"] == "late_night"
            assert causes[0]["ayurvedic_source"] == "Ashtanga Hridaya, sutrasthana.4"


# =============================================================================
# Pattern Learning Tests
# =============================================================================

class TestPatternLearning:
    """Tests for pattern_learning.py functions."""

    @pytest.mark.asyncio
    async def test_extract_behaviors_and_symptoms(self):
        """Should extract behaviors and symptoms from text."""
        from sakhi.apps.api.services.ayurveda.pattern_learning import (
            ExtractionResult,
            extract_behaviors_and_symptoms,
        )

        mock_llm_result = ExtractionResult()

        with patch("sakhi.apps.api.services.ayurveda.pattern_learning.call_llm", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = mock_llm_result

            result = await extract_behaviors_and_symptoms(
                "I stayed up late and now feel anxious",
                person_id="test-user",
            )

            # Should have called LLM
            mock_llm.assert_called_once()
            assert isinstance(result, ExtractionResult)
            assert mock_llm.await_args.kwargs["max_repair_attempts"] == 3
            assert "at most 3 behaviors" in mock_llm.await_args.kwargs["prompt"]

    @pytest.mark.asyncio
    async def test_detect_patterns_batches_new_matches_once(self):
        """Repeated raw matches should upsert one pattern per unique cause/effect pair."""
        matches = [
            {
                "cause_type": "food",
                "cause_value": "late_dinner",
                "effect_type": "physical",
                "effect_value": "poor_sleep",
                "related_dosha": "vata",
                "observed_at": datetime(2026, 3, 1, 8, 0, tzinfo=timezone.utc),
            },
            {
                "cause_type": "food",
                "cause_value": "late_dinner",
                "effect_type": "physical",
                "effect_value": "poor_sleep",
                "related_dosha": "vata",
                "observed_at": datetime(2026, 3, 1, 9, 0, tzinfo=timezone.utc),
            },
            {
                "cause_type": "work",
                "cause_value": "overwork",
                "effect_type": "physical",
                "effect_value": "elevated_heart_rate",
                "related_dosha": "pitta",
                "observed_at": datetime(2026, 3, 1, 10, 0, tzinfo=timezone.utc),
            },
        ]

        with patch(
            "sakhi.apps.api.services.ayurveda.pattern_learning._find_new_behavior_symptom_matches",
            new_callable=AsyncMock,
        ) as mock_find, patch(
            "sakhi.apps.api.services.ayurveda.pattern_learning._record_behavior_symptom_matches",
            new_callable=AsyncMock,
        ) as mock_record, patch(
            "sakhi.apps.api.services.ayurveda.pattern_learning._upsert_pattern",
            new_callable=AsyncMock,
        ) as mock_upsert:
            mock_find.return_value = matches
            mock_record.return_value = matches
            mock_upsert.side_effect = [
                {
                    "cause": "food:late_dinner",
                    "effect": "physical:poor_sleep",
                    "observation_count": 2,
                    "status": "strengthened",
                },
                {
                    "cause": "work:overwork",
                    "effect": "physical:elevated_heart_rate",
                    "observation_count": 1,
                    "status": "new",
                },
            ]

            from sakhi.apps.api.services.ayurveda.pattern_learning import detect_patterns

            result = await detect_patterns("test-user", lookback_days=14)

            assert len(result) == 2
            assert mock_upsert.await_count == 2

            calls = mock_upsert.await_args_list
            assert any(
                call.kwargs["cause_value"] == "late_dinner"
                and call.kwargs["increment"] == 2
                for call in calls
            )
            assert any(
                call.kwargs["cause_value"] == "overwork"
                and call.kwargs["increment"] == 1
                for call in calls
            )

    def test_get_dosha_effect(self):
        """Should return correct dosha effect for known behaviors."""
        from sakhi.apps.api.services.ayurveda.pattern_learning import get_dosha_effect

        # Vata-aggravating
        dosha, direction = get_dosha_effect("irregular_schedule")
        assert dosha == "vata"
        assert direction == "aggravates"

        # Pitta-aggravating
        dosha, direction = get_dosha_effect("spicy_food")
        assert dosha == "pitta"
        assert direction == "aggravates"

        # Kapha-aggravating
        dosha, direction = get_dosha_effect("overeating")
        assert dosha == "kapha"
        assert direction == "aggravates"

        # Unknown behavior
        dosha, direction = get_dosha_effect("unknown_behavior")
        assert dosha is None
        assert direction is None


# =============================================================================
# Recommendation Generator Tests
# =============================================================================

class TestRecommendationGenerator:
    """Tests for recommendation generator."""

    def test_personalized_recommendation_model(self):
        """PersonalizedRecommendation should have all required fields."""
        from sakhi.apps.api.services.recommendations.generator import PersonalizedRecommendation

        rec = PersonalizedRecommendation(
            name="Ginger Tea",
            name_sanskrit="Shunti Kashaya",
            category="food",
            score=0.85,
            ayurvedic_reason="Pungent taste, warming energy",
            ayurvedic_source="Bhavaprakasha, Madhya Khanda",
            dosha_effect="Pacifies vata",
            contraindications=["Avoid in high pitta"],
        )

        assert rec.name == "Ginger Tea"
        assert rec.name_sanskrit == "Shunti Kashaya"
        assert rec.ayurvedic_source == "Bhavaprakasha, Madhya Khanda"
        assert len(rec.contraindications) == 1

    def test_recommendation_set_includes_herbs(self):
        """RecommendationSet should include herbs field."""
        from sakhi.apps.api.services.recommendations.generator import (
            RecommendationSet,
            PersonalizedRecommendation,
        )

        herb = PersonalizedRecommendation(
            name="Ashwagandha",
            category="herb",
            score=0.9,
            ayurvedic_reason="Rejuvenative",
        )

        rec_set = RecommendationSet(
            person_id="test-user",
            friction_state="Chaos Friction",
            urgency_level="moderate",
            personalization_confidence=0.7,
            why_this_state="Elevated vata",
            herbs=[herb],
        )

        assert len(rec_set.herbs) == 1
        assert rec_set.herbs[0].name == "Ashwagandha"

    @pytest.mark.asyncio
    async def test_query_herbs_for_dosha(self):
        """Should query herbs that pacify a dosha."""
        mock_results = [
            {
                "name": "ashwagandha",
                "name_sanskrit": "Ashvagandha",
                "display_name": "Ashwagandha",
                "attrs": '{"rasa": "tikta", "virya": "ushna", "therapeutic_uses": ["adaptogen", "rejuvenative"]}',
                "citations": '[{"source": "charaka_samhita", "chapter": "chikitsasthana"}]',
                "confidence": 0.9,
                "weight": 0.9,
            }
        ]

        with patch("sakhi.apps.api.services.recommendations.generator.dbfetch", new_callable=AsyncMock) as mock_db:
            mock_db.return_value = mock_results

            from sakhi.apps.api.services.recommendations.generator import query_herbs_for_dosha

            herbs = await query_herbs_for_dosha("vata", limit=5)

            assert len(herbs) == 1
            assert herbs[0]["name"] == "ashwagandha"
            assert herbs[0]["name_sanskrit"] == "Ashvagandha"
            assert "adaptogen" in herbs[0]["therapeutic_uses"]

    def test_format_citation(self):
        """Should format citation from knowledge graph."""
        from sakhi.apps.api.services.recommendations.generator import _format_citation

        citations = [{"source": "charaka_samhita", "chapter": "sutrasthana.27"}]
        result = _format_citation(citations)
        assert result == "Charaka Samhita, sutrasthana.27"

        # Empty citations
        assert _format_citation([]) is None
        assert _format_citation(None) is None


# =============================================================================
# Feedback Loop Tests
# =============================================================================

class TestFeedbackLoop:
    """Tests for feedback extraction and processing."""

    @pytest.mark.asyncio
    async def test_extract_feedback_from_text_positive(self):
        """Should extract positive feedback signals from user text."""
        from sakhi.apps.api.services.learning.feedback import (
            extract_feedback_from_text,
            FeedbackType,
        )

        # Test with clear positive text (doesn't need LLM)
        result = await extract_feedback_from_text(
            person_id="test-user",
            text="I loved that warm milk recommendation",
            recent_recommendation={"domain": "food", "type": "food"},
        )

        assert result is not None
        assert result.feedback_type == FeedbackType.PRAISE

    @pytest.mark.asyncio
    async def test_extract_feedback_from_text_negative(self):
        """Should extract negative feedback signals from user text."""
        from sakhi.apps.api.services.learning.feedback import (
            extract_feedback_from_text,
            FeedbackType,
        )

        # Test with clear negative text (doesn't need LLM)
        result = await extract_feedback_from_text(
            person_id="test-user",
            text="That ginger tea was too spicy for me",
            recent_recommendation={"domain": "food", "type": "food"},
        )

        assert result is not None
        assert result.feedback_type == FeedbackType.COMPLAINT

    @pytest.mark.asyncio
    async def test_extract_feedback_returns_none_for_neutral(self):
        """Should return None for neutral text without feedback signals."""
        from sakhi.apps.api.services.learning.feedback import extract_feedback_from_text

        result = await extract_feedback_from_text(
            person_id="test-user",
            text="Hello, how are you today?",
        )

        assert result is None
