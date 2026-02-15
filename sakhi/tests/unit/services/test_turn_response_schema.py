"""
Tests for TurnResponse schema contract.

Ensures:
- Product fields are exactly what the frontend expects
- Debug fields are NOT in the product model
- Schema is stable (snapshot test)
"""

import pytest

from sakhi.apps.api.schemas.turn_response import (
    TurnResponseProduct,
    TurnResponseDebug,
    TurnResponse,
    PRODUCT_FIELDS,
    DEBUG_FIELDS,
)


class TestProductFieldsContract:
    """Snapshot test: the frontend depends on exactly these fields."""

    EXPECTED_PRODUCT_FIELDS = {
        "reply",
        "sessionId",
        "tone_blueprint",
        "adaptive_response",
        "friction_state",
        "personalized_recommendations",
        "journaling_ai",
        "memory_recall",
        "agent_task_context",
        "entry_id",
    }

    def test_product_fields_match_expected(self):
        assert PRODUCT_FIELDS == self.EXPECTED_PRODUCT_FIELDS

    def test_no_debug_fields_in_product(self):
        """Debug fields must never appear at the product level."""
        leaked = PRODUCT_FIELDS & DEBUG_FIELDS
        assert leaked == set(), f"Debug fields leaked into product: {leaked}"

    def test_debug_field_not_in_product_model(self):
        """The 'debug' and 'reasoning' keys must not be product fields."""
        assert "debug" not in PRODUCT_FIELDS
        assert "reasoning" not in PRODUCT_FIELDS
        assert "orchestration" not in PRODUCT_FIELDS
        assert "memory_write" not in PRODUCT_FIELDS

    def test_product_model_has_reply(self):
        model = TurnResponseProduct(reply="hello")
        assert model.reply == "hello"

    def test_product_model_defaults(self):
        model = TurnResponseProduct()
        assert model.reply == ""
        assert model.adaptive_response is None
        assert model.memory_recall is None


class TestTurnResponseDebug:
    """Debug model captures all the internal fields."""

    def test_debug_has_reasoning(self):
        assert "reasoning" in DEBUG_FIELDS

    def test_debug_has_orchestration(self):
        assert "orchestration" in DEBUG_FIELDS

    def test_debug_has_memory_write(self):
        assert "memory_write" in DEBUG_FIELDS

    def test_debug_has_debug(self):
        assert "debug" in DEBUG_FIELDS


class TestTurnResponseCombined:
    """Combined model includes product + optional debug."""

    def test_combined_has_debug_data_field(self):
        assert "debug_data" in TurnResponse.model_fields

    def test_combined_inherits_product_fields(self):
        for field in PRODUCT_FIELDS:
            assert field in TurnResponse.model_fields

    def test_debug_data_is_optional(self):
        model = TurnResponse(reply="hello")
        assert model.debug_data is None
