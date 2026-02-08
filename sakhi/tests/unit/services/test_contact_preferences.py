"""
Unit tests for Contact Preferences service.

Tests the pure logic (format_preferences_for_llm, priority ordering)
without hitting the database.
"""

import pytest
from unittest.mock import AsyncMock, patch

from sakhi.apps.api.services.email.contact_preferences import (
    format_preferences_for_llm,
    PRIORITY_ORDER,
)


# =============================================================================
# format_preferences_for_llm
# =============================================================================


class TestFormatPreferencesForLLM:
    """Tests for LLM prompt formatting."""

    def test_empty_preferences_returns_empty_string(self):
        assert format_preferences_for_llm([]) == ""

    def test_all_normal_no_notes_returns_empty(self):
        """Normal priority without notes is excluded from LLM context."""
        prefs = [
            {"contact_identifier": "bob@acme.com", "priority": "normal", "notes": None, "relationship": None, "organization": None},
        ]
        assert format_preferences_for_llm(prefs) == ""

    def test_normal_with_notes_included(self):
        """Normal priority WITH notes should be included."""
        prefs = [
            {"contact_identifier": "bob@acme.com", "priority": "normal", "notes": "Replies slowly", "relationship": None, "organization": None},
        ]
        result = format_preferences_for_llm(prefs)
        assert "bob@acme.com" in result
        assert "Replies slowly" in result

    def test_critical_priority_format(self):
        prefs = [
            {
                "contact_identifier": "sarah@acme.com",
                "priority": "critical",
                "relationship": "boss",
                "organization": "Acme Corp",
                "notes": "Always reply same day",
            },
        ]
        result = format_preferences_for_llm(prefs)
        assert "sarah@acme.com" in result
        assert "BOSS" in result
        assert "Acme Corp" in result
        assert "CRITICAL" in result
        assert "Always reply same day" in result

    def test_muted_priority_format(self):
        prefs = [
            {
                "contact_identifier": "newsletter@substack.com",
                "priority": "muted",
                "relationship": None,
                "organization": None,
                "notes": None,
            },
        ]
        result = format_preferences_for_llm(prefs)
        assert "newsletter@substack.com" in result
        assert "MUTED" in result

    def test_multiple_preferences_all_listed(self):
        prefs = [
            {"contact_identifier": "boss@co.com", "priority": "critical", "relationship": "boss", "organization": None, "notes": None},
            {"contact_identifier": "mom@gmail.com", "priority": "high", "relationship": "family", "organization": None, "notes": None},
            {"contact_identifier": "spam@vendor.com", "priority": "muted", "relationship": None, "organization": None, "notes": None},
        ]
        result = format_preferences_for_llm(prefs)
        assert "boss@co.com" in result
        assert "mom@gmail.com" in result
        assert "spam@vendor.com" in result
        assert result.startswith("The user has set these contact preferences:")

    def test_header_line_present(self):
        prefs = [
            {"contact_identifier": "x@y.com", "priority": "high", "relationship": None, "organization": None, "notes": None},
        ]
        result = format_preferences_for_llm(prefs)
        assert result.startswith("The user has set these contact preferences:")

    def test_low_priority_included(self):
        prefs = [
            {"contact_identifier": "vendor@saas.com", "priority": "low", "relationship": "vendor", "organization": None, "notes": "Only urgent if mentions renewal"},
        ]
        result = format_preferences_for_llm(prefs)
        assert "vendor@saas.com" in result
        assert "LOW" in result
        assert "VENDOR" in result


# =============================================================================
# Priority Ordering
# =============================================================================


class TestPriorityOrder:
    """Tests for priority sort constants."""

    def test_critical_sorts_first(self):
        assert PRIORITY_ORDER["critical"] < PRIORITY_ORDER["high"]

    def test_muted_sorts_last(self):
        assert PRIORITY_ORDER["muted"] > PRIORITY_ORDER["low"]

    def test_full_ordering(self):
        ordered = sorted(PRIORITY_ORDER.keys(), key=lambda k: PRIORITY_ORDER[k])
        assert ordered == ["critical", "high", "normal", "low", "muted"]


# =============================================================================
# get_preferences (mocked DB)
# =============================================================================


class TestGetPreferences:
    """Tests for get_preferences with mocked database."""

    @pytest.mark.asyncio
    async def test_returns_serialized_rows(self):
        import uuid
        from datetime import datetime, timezone

        mock_rows = [
            {
                "id": uuid.uuid4(),
                "person_id": uuid.uuid4(),
                "contact_identifier": "boss@acme.com",
                "channel": "email",
                "display_name": "Sarah",
                "relationship": "boss",
                "organization": "Acme",
                "priority": "critical",
                "notes": "Reply fast",
                "learned_from": "user_set",
                "confidence": 1.0,
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
            }
        ]

        with patch("sakhi.apps.api.services.email.contact_preferences.dbfetch", new_callable=AsyncMock) as mock_db:
            mock_db.return_value = mock_rows

            from sakhi.apps.api.services.email.contact_preferences import get_preferences
            result = await get_preferences("test-person-id")

            assert len(result) == 1
            assert result[0]["contact_identifier"] == "boss@acme.com"
            # UUIDs and timestamps should be serialized to strings
            assert isinstance(result[0]["id"], str)
            assert isinstance(result[0]["created_at"], str)

    @pytest.mark.asyncio
    async def test_empty_returns_empty_list(self):
        with patch("sakhi.apps.api.services.email.contact_preferences.dbfetch", new_callable=AsyncMock) as mock_db:
            mock_db.return_value = []

            from sakhi.apps.api.services.email.contact_preferences import get_preferences
            result = await get_preferences("test-person-id")
            assert result == []


# =============================================================================
# get_suggestions (mocked DB)
# =============================================================================


class TestGetSuggestions:
    """Tests for dismiss-based and reply-based suggestions."""

    @pytest.mark.asyncio
    async def test_returns_mute_suggestions_for_frequent_dismissals(self):
        mute_rows = [
            {"contact_identifier": "vendor@spam.com", "dismiss_count": 5},
            {"contact_identifier": "promo@store.com", "dismiss_count": 3},
        ]
        promote_rows = []  # No promote suggestions

        with patch("sakhi.apps.api.services.email.contact_preferences.dbfetch", new_callable=AsyncMock) as mock_db:
            mock_db.side_effect = [mute_rows, promote_rows]

            from sakhi.apps.api.services.email.contact_preferences import get_suggestions
            result = await get_suggestions("test-person-id")

            assert len(result) == 2
            assert result[0]["contact_identifier"] == "vendor@spam.com"
            assert result[0]["suggested_priority"] == "muted"
            assert "5" in result[0]["reason"]

    @pytest.mark.asyncio
    async def test_returns_promote_suggestions_for_frequent_replies(self):
        mute_rows = []
        promote_rows = [
            {"contact_identifier": "colleague@work.com", "reply_count": 8},
        ]

        with patch("sakhi.apps.api.services.email.contact_preferences.dbfetch", new_callable=AsyncMock) as mock_db:
            mock_db.side_effect = [mute_rows, promote_rows]

            from sakhi.apps.api.services.email.contact_preferences import get_suggestions
            result = await get_suggestions("test-person-id")

            assert len(result) == 1
            assert result[0]["contact_identifier"] == "colleague@work.com"
            assert result[0]["suggested_priority"] == "high"
            assert "8" in result[0]["reason"]

    @pytest.mark.asyncio
    async def test_combines_mute_and_promote_suggestions(self):
        mute_rows = [{"contact_identifier": "spam@vendor.com", "dismiss_count": 4}]
        promote_rows = [{"contact_identifier": "boss@co.com", "reply_count": 10}]

        with patch("sakhi.apps.api.services.email.contact_preferences.dbfetch", new_callable=AsyncMock) as mock_db:
            mock_db.side_effect = [mute_rows, promote_rows]

            from sakhi.apps.api.services.email.contact_preferences import get_suggestions
            result = await get_suggestions("test-person-id")

            assert len(result) == 2
            muted = [s for s in result if s["suggested_priority"] == "muted"]
            promoted = [s for s in result if s["suggested_priority"] == "high"]
            assert len(muted) == 1
            assert len(promoted) == 1

    @pytest.mark.asyncio
    async def test_no_patterns_returns_empty(self):
        with patch("sakhi.apps.api.services.email.contact_preferences.dbfetch", new_callable=AsyncMock) as mock_db:
            mock_db.side_effect = [[], []]

            from sakhi.apps.api.services.email.contact_preferences import get_suggestions
            result = await get_suggestions("test-person-id")
            assert result == []
