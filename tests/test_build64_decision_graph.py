import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from sakhi.core.intelligence.decision_graph_engine import compute_fast_decision_graph_frame, compute_deep_decision_graph
from sakhi.apps.worker import decision_graph_deep
from sakhi.apps.api.routes import decision_graph as decision_graph_route


def test_fast_decision_graph_frame():
    out = compute_fast_decision_graph_frame(
        [{"text": "progress"}],
        [{"title": "learn guitar"}],
        [{"title": "guitar goal"}],
        [{"title": "practice 10m"}],
        {"core_values": ["growth"], "shadow": ["doubt"], "friction": ["time"]},
    )
    assert "active_nodes" in out
    assert "energy_path" in out


@pytest.mark.asyncio
async def test_deep_decision_graph(monkeypatch):
    async def fake_llm(messages=None, **kwargs):
        return {"nodes": {"values": []}, "edges": {}, "graph_metadata": {}}

    async def fake_dbexec(sql, *args, **kwargs):
        pass

    async def fake_q(*a, **k):
        return []

    monkeypatch.setattr("sakhi.core.intelligence.decision_graph_engine.call_llm", fake_llm, raising=False)
    monkeypatch.setattr("sakhi.apps.worker.decision_graph_deep.dbexec", fake_dbexec)
    monkeypatch.setattr("sakhi.apps.worker.decision_graph_deep.q", fake_q)

    res = await compute_deep_decision_graph("pid", [], {}, {}, [])
    assert "nodes" in res or "graph_metadata" in res
    await decision_graph_deep.run_decision_graph_deep("pid")


def test_decision_graph_api(monkeypatch):
    app = FastAPI()

    async def fake_q(query, person_id, one=False):
        return {"soul_state": {"core_values": ["growth"]}, "goals_state": {"active_goals": [{"title": "g"}]}, "internal_decision_graph": {"deep": True}}

    monkeypatch.setattr("sakhi.apps.api.routes.decision_graph.q", fake_q)
    app.include_router(decision_graph_route.router)
    client = TestClient(app)
    resp = client.get("/decision_graph/demo")
    assert resp.status_code == 200
    data = resp.json()
    assert "fast" in data and "deep" in data
