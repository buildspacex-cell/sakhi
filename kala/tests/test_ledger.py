"""Tests for kala.ledger — append-only event ledger."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from kala.ledger.core import (
    VALID_ACTORS,
    VALID_EVENT_TYPES,
    Event,
    InMemoryBackend,
    Ledger,
    LedgerBackend,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_T0 = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)


def _make_event(
    *,
    id: str = "evt-1",
    timestamp: datetime = _T0,
    entity_id: str = "user-1",
    event_type: str = "proposed",
    action: str = "suggest_routine",
    actor: str = "llm",
    data: dict | None = None,
    reason: str = "",
) -> Event:
    return Event(
        id=id,
        timestamp=timestamp,
        entity_id=entity_id,
        event_type=event_type,
        action=action,
        actor=actor,
        data=data or {},
        reason=reason,
    )


# ===========================================================================
# Event dataclass
# ===========================================================================


class TestEvent:
    def test_creation(self) -> None:
        e = _make_event()
        assert e.id == "evt-1"
        assert e.entity_id == "user-1"
        assert e.event_type == "proposed"

    def test_frozen(self) -> None:
        e = _make_event()
        with pytest.raises(AttributeError):
            e.action = "changed"  # type: ignore[misc]

    def test_defaults(self) -> None:
        e = _make_event()
        assert e.data == {}
        assert e.reason == ""

    def test_with_data(self) -> None:
        e = _make_event(data={"goal": "sleep early"})
        assert e.data["goal"] == "sleep early"

    def test_valid_event_types(self) -> None:
        expected = {"proposed", "validated", "committed", "rejected", "reconciled", "observed"}
        assert VALID_EVENT_TYPES == expected

    def test_valid_actors(self) -> None:
        expected = {"llm", "user", "system", "crystallization", "governance"}
        assert VALID_ACTORS == expected


# ===========================================================================
# Ledger — append + basic operations
# ===========================================================================


class TestLedgerAppend:
    def test_append_increases_length(self) -> None:
        ledger = Ledger()
        assert len(ledger) == 0
        ledger.append(_make_event())
        assert len(ledger) == 1

    def test_append_preserves_order(self) -> None:
        ledger = Ledger()
        e1 = _make_event(id="e1", timestamp=_T0)
        e2 = _make_event(id="e2", timestamp=_T0 + timedelta(hours=1))
        ledger.append(e1)
        ledger.append(e2)
        events = list(ledger)
        assert events[0].id == "e1"
        assert events[1].id == "e2"

    def test_appended_event_retrievable(self) -> None:
        ledger = Ledger()
        e = _make_event(entity_id="user-42")
        ledger.append(e)
        results = ledger.query(entity_id="user-42")
        assert len(results) == 1
        assert results[0].id == e.id

    def test_multiple_appends(self) -> None:
        ledger = Ledger()
        for i in range(5):
            ledger.append(_make_event(id=f"e{i}"))
        assert len(ledger) == 5


# ===========================================================================
# Ledger — query
# ===========================================================================


class TestLedgerQuery:
    def test_by_entity_id(self) -> None:
        ledger = Ledger()
        ledger.append(_make_event(id="e1", entity_id="a"))
        ledger.append(_make_event(id="e2", entity_id="b"))
        assert len(ledger.query(entity_id="a")) == 1

    def test_by_event_type(self) -> None:
        ledger = Ledger()
        ledger.append(_make_event(id="e1", event_type="proposed"))
        ledger.append(_make_event(id="e2", event_type="committed"))
        assert len(ledger.query(event_type="committed")) == 1

    def test_by_action(self) -> None:
        ledger = Ledger()
        ledger.append(_make_event(id="e1", action="suggest_routine"))
        ledger.append(_make_event(id="e2", action="update_goal"))
        assert len(ledger.query(action="update_goal")) == 1

    def test_by_actor(self) -> None:
        ledger = Ledger()
        ledger.append(_make_event(id="e1", actor="llm"))
        ledger.append(_make_event(id="e2", actor="user"))
        assert len(ledger.query(actor="user")) == 1

    def test_by_time_after(self) -> None:
        ledger = Ledger()
        ledger.append(_make_event(id="e1", timestamp=_T0))
        ledger.append(_make_event(id="e2", timestamp=_T0 + timedelta(hours=2)))
        results = ledger.query(after=_T0 + timedelta(hours=1))
        assert len(results) == 1
        assert results[0].id == "e2"

    def test_by_time_before(self) -> None:
        ledger = Ledger()
        ledger.append(_make_event(id="e1", timestamp=_T0))
        ledger.append(_make_event(id="e2", timestamp=_T0 + timedelta(hours=2)))
        results = ledger.query(before=_T0 + timedelta(hours=1))
        assert len(results) == 1
        assert results[0].id == "e1"

    def test_combined_filters(self) -> None:
        ledger = Ledger()
        ledger.append(_make_event(id="e1", entity_id="a", event_type="proposed"))
        ledger.append(_make_event(id="e2", entity_id="a", event_type="committed"))
        ledger.append(_make_event(id="e3", entity_id="b", event_type="proposed"))
        results = ledger.query(entity_id="a", event_type="proposed")
        assert len(results) == 1
        assert results[0].id == "e1"

    def test_no_match(self) -> None:
        ledger = Ledger()
        ledger.append(_make_event(entity_id="a"))
        assert ledger.query(entity_id="z") == []


# ===========================================================================
# Ledger — latest
# ===========================================================================


class TestLedgerLatest:
    def test_returns_most_recent(self) -> None:
        ledger = Ledger()
        ledger.append(_make_event(id="e1", entity_id="a", timestamp=_T0))
        ledger.append(_make_event(id="e2", entity_id="a", timestamp=_T0 + timedelta(hours=1)))
        result = ledger.latest("a")
        assert result is not None
        assert result.id == "e2"

    def test_with_type_filter(self) -> None:
        ledger = Ledger()
        ledger.append(_make_event(id="e1", entity_id="a", event_type="proposed"))
        ledger.append(_make_event(id="e2", entity_id="a", event_type="committed"))
        result = ledger.latest("a", event_type="proposed")
        assert result is not None
        assert result.id == "e1"

    def test_nonexistent_entity(self) -> None:
        ledger = Ledger()
        assert ledger.latest("nonexistent") is None


# ===========================================================================
# Ledger — dunder methods
# ===========================================================================


class TestLedgerDunder:
    def test_len(self) -> None:
        ledger = Ledger()
        assert len(ledger) == 0
        ledger.append(_make_event())
        assert len(ledger) == 1

    def test_bool_empty(self) -> None:
        ledger = Ledger()
        assert not ledger

    def test_bool_nonempty(self) -> None:
        ledger = Ledger()
        ledger.append(_make_event())
        assert ledger

    def test_iter(self) -> None:
        ledger = Ledger()
        ledger.append(_make_event(id="e1"))
        ledger.append(_make_event(id="e2"))
        ids = [e.id for e in ledger]
        assert ids == ["e1", "e2"]


# ===========================================================================
# InMemoryBackend is a LedgerBackend
# ===========================================================================


class TestInMemoryBackend:
    def test_is_subclass(self) -> None:
        assert issubclass(InMemoryBackend, LedgerBackend)

    def test_custom_backend(self) -> None:
        """Verify Ledger works with any LedgerBackend implementation."""

        class ListBackend(LedgerBackend):
            def __init__(self):
                self._data: list[Event] = []

            def append(self, event: Event) -> None:
                self._data.append(event)

            def query(self, **kwargs) -> list[Event]:
                return list(self._data)

        ledger = Ledger(backend=ListBackend())
        ledger.append(_make_event())
        assert len(ledger) == 1
