import asyncio
import datetime as dt

import pytest

from sakhi.apps.worker.tasks import brain_goals_themes_refresh as worker


def test_cluster_entries_merges_similar():
    v1 = [1.0, 0.0, 0.0]
    v2 = [0.99, 0.01, 0.0]
    entries = [
        {"id": "a", "text": "goal one", "vector": v1},
        {"id": "b", "text": "goal one duplicate", "vector": v2},
    ]
    clusters = worker._cluster_entries(entries, threshold=0.2)
    assert len(clusters) == 1
    assert len(clusters[0]["items"]) == 2


@pytest.mark.asyncio
async def test_worker_updates_personal_model(monkeypatch):
    calls = {"select_ep": 0, "upsert": 0, "pm": 0}
    fake_ep_rows = [
        {"id": "11111111-1111-1111-1111-111111111111", "text": "learn guitar", "vector_vec": [1.0, 0.0, 0.0], "triage": {}}
    ]
    pm_state = {"long_term": {}}

    async def fake_q(sql, *args, **kwargs):
        if "FROM memory_episodic" in sql:
            calls["select_ep"] += 1
            return fake_ep_rows
        if "FROM personal_model" in sql:
            calls["pm"] += 1
            return pm_state
        return None

    async def fake_exec(sql, *args, **kwargs):
        calls["upsert"] += 1

    monkeypatch.setattr(worker, "q", fake_q)
    monkeypatch.setattr(worker, "dbexec", fake_exec)
    async def fake_resolve(pid):
        return pid

    monkeypatch.setattr(worker, "resolve_person_id", fake_resolve)
    monkeypatch.setattr(worker, "embed_normalized", lambda text: [1.0, 0.0, 0.0])
    res = await worker.run_brain_goals_themes_refresh("00000000-0000-0000-0000-000000000000")
    assert res.get("clusters") == 1
    assert calls["select_ep"] == 1
    assert calls["upsert"] >= 1
