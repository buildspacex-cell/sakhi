import asyncio
from typing import Any, Dict

import pytest

from datetime import datetime, timezone
from sakhi.apps.api.services.memory import personal_model


class _FakeStore:
    def __init__(self):
        self.row: Dict[str, Any] = {}

    async def fetchrow(self, sql: str, person_id: str):
        return self.row.get(person_id)

    async def exec(self, sql: str, person_id: str, short_term, long_term, updated_at):
        self.row[person_id] = {
            "short_term": short_term,
            "long_term": long_term,
        }


@pytest.mark.asyncio
async def test_dedup_observations():
    store = _FakeStore()
    # Patch db funcs
    personal_model.dbfetchrow = store.fetchrow  # type: ignore
    personal_model.dbexec = store.exec  # type: ignore

    pid = "pid-1"
    text = "Best guitar for beginners"
    await personal_model.update_personal_model(pid, {"text": text, "layer": "journal"}, vector=[1.0, 1.0])
    await personal_model.update_personal_model(pid, {"text": text + "  ", "layer": "journal"}, vector=[1.0, 1.0])
    await personal_model.update_personal_model(pid, {"text": "best   guitar for beginners", "layer": "journal"}, vector=[1.0, 1.0])

    row = store.row[pid]
    observations = row["long_term"]["observations"]
    assert len(observations) == 1


@pytest.mark.asyncio
async def test_identity_graph_exists():
    store = _FakeStore()
    personal_model.dbfetchrow = store.fetchrow  # type: ignore
    personal_model.dbexec = store.exec  # type: ignore
    pid = "pid-2"
    await personal_model.update_personal_model(pid, {"text": "hello world", "layer": "conversation"}, vector=[])
    row = store.row[pid]
    identity_graph = row["long_term"]["identity_graph"]
    assert set(identity_graph.keys()) == {"skills", "interests", "preferences", "values", "patterns"}


@pytest.mark.asyncio
async def test_merged_vector_average():
    store = _FakeStore()
    personal_model.dbfetchrow = store.fetchrow  # type: ignore
    personal_model.dbexec = store.exec  # type: ignore
    pid = "pid-3"
    await personal_model.update_personal_model(pid, {"text": "first", "layer": "journal"}, vector=[1.0, 1.0])
    await personal_model.update_personal_model(pid, {"text": "second entry", "layer": "journal"}, vector=[3.0, 3.0])
    row = store.row[pid]
    merged = row["long_term"]["merged_vector"]
    assert merged == [2.0, 2.0]


def test_api_does_not_touch_personal_model(monkeypatch):
    # Ensure ingest_fast does not call update_personal_model (would raise if called)
    async def boom(*args, **kwargs):
        raise AssertionError("should not be called")

    monkeypatch.setattr(personal_model, "update_personal_model", boom)
    # ingest_fast should complete without invoking update_personal_model
    from sakhi.apps.api.services.ingestion import unified_ingest

    async def run():
        await unified_ingest.ingest_fast(
            person_id="pid-4",
            text="hello",
            layer="conversation",
            ts=datetime.now(timezone.utc),
            session_id=None,
            entry_id="entry-1",
        )

    asyncio.run(run())
