import datetime as dt

import pytest

from sakhi.apps.intent_engine import evolution
from sakhi.apps.worker.tasks import intent_evolution_decay
from sakhi.apps.api.services.memory import personal_model as pm


@pytest.mark.asyncio
async def test_intent_creation(monkeypatch):
    calls = {"insert": False}

    async def fake_q(sql, *args, **kwargs):
        return None

    async def fake_exec(sql, *args, **kwargs):
        calls["insert"] = True

    async def fake_resolve(pid):
        return pid

    monkeypatch.setattr(evolution, "q", fake_q)
    monkeypatch.setattr(evolution, "dbexec", fake_exec)
    monkeypatch.setattr(evolution, "resolve_person_id", fake_resolve)
    res = await evolution.evolve("p1", "Plan project", 0.3)
    assert res["strength"] == 0.2
    assert calls["insert"] is True


@pytest.mark.asyncio
async def test_intent_strengthen(monkeypatch):
    async def fake_q(sql, *args, **kwargs):
        return {"strength": 0.2, "emotional_alignment": 0.1}

    async def fake_exec(sql, *args, **kwargs):
        return None

    async def fake_resolve(pid):
        return pid

    monkeypatch.setattr(evolution, "q", fake_q)
    monkeypatch.setattr(evolution, "dbexec", fake_exec)
    monkeypatch.setattr(evolution, "resolve_person_id", fake_resolve)
    res = await evolution.evolve("p1", "Plan project", 0.3)
    assert res["strength"] > 0.2
    assert res["trend"] == "up"


@pytest.mark.asyncio
async def test_decay(monkeypatch):
    updates = []

    async def fake_q(sql, *args, **kwargs):
        return [{"intent_name": "plan project", "strength": 0.5}]

    async def fake_exec(sql, *args, **kwargs):
        updates.append(args)

    monkeypatch.setattr(intent_evolution_decay, "q", fake_q)
    monkeypatch.setattr(intent_evolution_decay, "dbexec", fake_exec)
    await intent_evolution_decay.intent_evolution_decay("p1")
    assert updates


@pytest.mark.asyncio
async def test_personal_model_sync(monkeypatch):
    async def fake_dbfetchrow(*args, **kwargs):
        return {"short_term": {}, "long_term": {}}

    async def fake_q(sql, *args, **kwargs):
        if "FROM intent_evolution" in sql:
            return [
                {"intent_name": "plan", "strength": 0.5, "trend": "up", "emotional_alignment": 0.2, "last_seen": dt.datetime.utcnow().isoformat()}
            ]
        return None

    async def fake_exec(*args, **kwargs):
        return None

    monkeypatch.setattr(pm, "dbfetchrow", fake_dbfetchrow)
    monkeypatch.setattr(pm, "dbexec", fake_exec)
    monkeypatch.setattr(pm, "q", fake_q)

    res = await pm.update_personal_model("p1", {"text": "hi", "layer": "test"}, vector=[], layer_overrides=None)
    intents = res.get("long_term", {}).get("intents", [])
    assert intents
