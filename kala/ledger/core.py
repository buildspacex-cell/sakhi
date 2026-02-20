"""Append-only event ledger with backend abstraction.

The ledger records every governance-relevant event in chronological order.
It is **append-only** — events are never modified or deleted.

``LedgerBackend`` is an ABC for persistence.  kala ships with
``InMemoryBackend``; consuming applications provide DB-backed backends.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

# ---------------------------------------------------------------------------
# Valid enumerations
# ---------------------------------------------------------------------------

VALID_EVENT_TYPES: frozenset[str] = frozenset({
    "proposed",
    "validated",
    "committed",
    "rejected",
    "reconciled",
    "observed",
})

VALID_ACTORS: frozenset[str] = frozenset({
    "llm",
    "user",
    "system",
    "crystallization",
    "governance",
})


# ---------------------------------------------------------------------------
# Event data type
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Event:
    """An immutable governance event."""

    id: str
    timestamp: datetime
    entity_id: str
    event_type: str
    action: str
    actor: str
    data: dict[str, Any] = field(default_factory=dict)
    reason: str = ""


# ---------------------------------------------------------------------------
# Backend abstraction
# ---------------------------------------------------------------------------


class LedgerBackend(ABC):
    """Abstract persistence interface for the event ledger.

    kala provides :class:`InMemoryBackend`.  Production applications
    inject a DB-backed implementation.
    """

    @abstractmethod
    def append(self, event: Event) -> None:
        """Persist a single event."""
        ...

    @abstractmethod
    def query(
        self,
        *,
        entity_id: str | None = None,
        event_type: str | None = None,
        action: str | None = None,
        actor: str | None = None,
        after: datetime | None = None,
        before: datetime | None = None,
    ) -> list[Event]:
        """Return events matching **all** supplied filters."""
        ...


class InMemoryBackend(LedgerBackend):
    """Default in-memory backend — suitable for tests and single-process use."""

    def __init__(self) -> None:
        self._events: list[Event] = []

    def append(self, event: Event) -> None:
        self._events.append(event)

    def query(
        self,
        *,
        entity_id: str | None = None,
        event_type: str | None = None,
        action: str | None = None,
        actor: str | None = None,
        after: datetime | None = None,
        before: datetime | None = None,
    ) -> list[Event]:
        results = self._events
        if entity_id is not None:
            results = [e for e in results if e.entity_id == entity_id]
        if event_type is not None:
            results = [e for e in results if e.event_type == event_type]
        if action is not None:
            results = [e for e in results if e.action == action]
        if actor is not None:
            results = [e for e in results if e.actor == actor]
        if after is not None:
            results = [e for e in results if e.timestamp > after]
        if before is not None:
            results = [e for e in results if e.timestamp < before]
        return results


# ---------------------------------------------------------------------------
# Ledger — the main API
# ---------------------------------------------------------------------------


class Ledger:
    """Append-only event log with pluggable backend.

    Usage::

        ledger = Ledger()  # InMemoryBackend by default
        ledger.append(Event(...))
        events = ledger.query(entity_id="user-123", event_type="committed")
    """

    def __init__(self, backend: LedgerBackend | None = None) -> None:
        self._backend = backend or InMemoryBackend()

    def append(self, event: Event) -> None:
        """Append an event to the ledger."""
        self._backend.append(event)

    def query(self, **filters: Any) -> list[Event]:
        """Query events by filter criteria."""
        return self._backend.query(**filters)

    def latest(self, entity_id: str, event_type: str | None = None) -> Event | None:
        """Return the most recent event for an entity, optionally filtered by type."""
        events = self._backend.query(entity_id=entity_id, event_type=event_type)
        return events[-1] if events else None

    def count(self, **filters: Any) -> int:
        """Count events matching the given filters."""
        return len(self._backend.query(**filters))

    def __len__(self) -> int:
        return len(self._backend.query())

    def __bool__(self) -> bool:
        return len(self) > 0

    def __iter__(self):
        return iter(self._backend.query())
