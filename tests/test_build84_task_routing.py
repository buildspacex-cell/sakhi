import os
import pytest
import asyncio

# satisfy auth import expectations
os.environ.setdefault("SUPABASE_URL", "http://localhost")
os.environ.setdefault("SUPABASE_ANON_KEY", "dummy")

from sakhi.apps.engine.task_routing.classifier import classify_task
from sakhi.apps.engine.task_routing import engine as routing_engine
from sakhi.apps.worker.tasks import task_routing_worker
from sakhi.apps.api.routes import task_routing as task_route


def test_classify_task():
    assert classify_task("analyze report")["category"] == "high_focus"
    assert classify_task("call and clean")["category"] == "low_energy"
    assert classify_task("design logo")["category"] == "creative"
    assert classify_task("journal feelings")["category"] == "emotional"
    assert classify_task("go for a run")["category"] == "physical"


@pytest.mark.asyncio
async def test_compute_routing(monkeypatch):
    async def fake_q(sql, *args, **kwargs):
        return {"forecast_state": {"emotion_forecast": {"calm": 0.5, "irritability": 0.1, "motivation": 0.4}}}

    async def fake_resolve(pid):
        return pid

    monkeypatch.setattr(routing_engine, "q", fake_q)
    monkeypatch.setattr(routing_engine, "resolve_person_id", fake_resolve)
    routing = await routing_engine.compute_routing("p1", {"title": "analyze data", "classification": {"category": "high_focus"}})
    assert routing["recommended_window"]
    assert routing["category"] == "high_focus"


@pytest.mark.asyncio
async def test_worker_updates(monkeypatch):
    calls = {"insert": 0, "update": 0}

    async def fake_q(sql, *args, **kwargs):
        if "FROM tasks" in sql:
            return [{"id": "t1", "title": "analyze data", "description": "", "status": "open"}]
        if "forecast_cache" in sql:
            return {"forecast_state": {"emotion_forecast": {"calm": 0.5}}}
        return {"coherence_state": {}, "conflict_state": {}}

    async def fake_dbexec(sql, *args, **kwargs):
        if "INSERT INTO task_routing_cache" in sql:
            calls["insert"] += 1
        if "UPDATE tasks SET routing_state" in sql:
            calls["update"] += 1

    async def fake_resolve(pid):
        return pid

    monkeypatch.setattr(task_routing_worker, "q", fake_q)
    monkeypatch.setattr(task_routing_worker, "dbexec", fake_dbexec)
    monkeypatch.setattr(task_routing_worker, "resolve_person_id", fake_resolve)
    # avoid hitting real DB in compute_routing
    monkeypatch.setattr(task_routing_worker, "compute_routing", lambda person_id, task: asyncio.ensure_future(
        asyncio.sleep(0, result={"category": "high_focus", "recommended_window": "morning", "reason": "test", "forecast_snapshot": {}}
    )))

    result = await task_routing_worker.run_task_routing("p1")
    assert result["count"] == 1
    assert calls["insert"] == 1
    assert calls["update"] == 1


@pytest.mark.asyncio
async def test_task_routing_api(monkeypatch):
    async def fake_q(sql, *args, **kwargs):
        return [{"task_id": "t1", "category": "high_focus", "recommended_window": "morning", "reason": "clarity", "forecast_snapshot": {}, "updated_at": "now"}]

    async def fake_resolve(pid):
        return pid

    monkeypatch.setattr(task_route, "q", fake_q)
    monkeypatch.setattr(task_route, "resolve_person_id", fake_resolve)
    resp = await task_route.list_routing(person_id="u1", user_id="u1")
    assert resp["items"][0]["category"] == "high_focus"
