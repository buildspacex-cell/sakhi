import pytest
from httpx import AsyncClient, ASGITransport

from sakhi.apps.api.main import app
from sakhi.apps.api.deps import auth as auth_deps


@pytest.mark.asyncio
async def test_daily_reflection_route(monkeypatch):
    async def fake_q(sql, *args, **kwargs):
        return [
            {"reflection_date": "2025-11-26", "summary": {"final_reflection": "ok"}, "generated_at": "2025-11-26T21:30:00Z"}
        ]

    async def fake_resolve(pid):
        return pid

    monkeypatch.setattr("sakhi.apps.api.routes.daily_reflection.q", fake_q)
    monkeypatch.setattr("sakhi.apps.api.routes.daily_reflection.resolve_person_id", fake_resolve)
    app.dependency_overrides[auth_deps.get_current_user_id] = lambda: "user"

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/v1/daily_reflection", params={"person_id": "00000000-0000-0000-0000-000000000001"})
    assert resp.status_code == 200
    assert resp.json()["summary"]


@pytest.mark.asyncio
async def test_daily_reflection_route_not_found(monkeypatch):
    async def fake_q(sql, *args, **kwargs):
        return []

    async def fake_resolve(pid):
        return pid

    monkeypatch.setattr("sakhi.apps.api.routes.daily_reflection.q", fake_q)
    monkeypatch.setattr("sakhi.apps.api.routes.daily_reflection.resolve_person_id", fake_resolve)
    app.dependency_overrides[auth_deps.get_current_user_id] = lambda: "user"

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/v1/daily_reflection", params={"person_id": "00000000-0000-0000-0000-000000000001"})
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_daily_reflection_in_turn(monkeypatch):
    async def fake_q(sql, *args, **kwargs):
        if "daily_reflection_cache" in sql:
            return [
                {"summary": {"final_reflection": "ok"}, "reflection_date": "2025-11-26", "generated_at": "2025-11-26T21:30:00Z"}
            ]
        return []

    async def fake_resolve(pid):
        return "00000000-0000-0000-0000-000000000050"

    monkeypatch.setattr("sakhi.apps.api.routes.turn_v2.q", fake_q)
    monkeypatch.setattr("sakhi.apps.api.routes.turn_v2.resolve_person_id", fake_resolve)
    async def fake_orchestrate(**kwargs):
        return {"brain": {}, "intents": [], "plans": [], "triage": {}, "topics": [], "emotion": {}, "pattern_sense": {}, "forecast_state": {}, "entry_id": "e1"}
    monkeypatch.setattr("sakhi.apps.api.routes.turn_v2.orchestrate_turn", fake_orchestrate)
    async def fake_run_unified(*args, **kwargs):
        return {"brain": {"emotion_state": {}, "soul_state": {}, "rhythm_state": {}}, "intents": [], "plans": [], "triage": {}, "topics": [], "emotion": {}, "pattern_sense": {}, "forecast_state": {}}
    monkeypatch.setattr("sakhi.apps.api.routes.turn_v2.run_unified_turn", fake_run_unified)

    async def fake_microreg(*args, **kwargs):
        return {}
    async def fake_empathy(*args, **kwargs):
        return {}
    async def fake_tone(*args, **kwargs):
        return {}
    def fake_alignment(*args, **kwargs):
        return {}
    monkeypatch.setattr("sakhi.apps.api.routes.turn_v2.compute_microreg", fake_microreg)
    monkeypatch.setattr("sakhi.apps.api.routes.turn_v2.compute_empathy", fake_empathy)
    monkeypatch.setattr("sakhi.apps.api.routes.turn_v2.compute_tone", fake_tone)
    monkeypatch.setattr("sakhi.apps.api.routes.turn_v2.compute_alignment", fake_alignment)
    async def fake_reply(*args, **kwargs):
        return {"reply": "ok", "tone_blueprint": {"style": "auto"}, "journaling_ai": None}
    monkeypatch.setattr("sakhi.apps.api.routes.turn_v2.generate_reply", fake_reply)
    async def fake_load_continuity(*args, **kwargs):
        return {}
    async def fake_update_continuity(*args, **kwargs):
        return {}
    monkeypatch.setattr("sakhi.apps.engine.continuity.engine.load_continuity", fake_load_continuity)
    monkeypatch.setattr("sakhi.apps.engine.continuity.engine.update_continuity", fake_update_continuity)
    async def fake_memory_recall(**kwargs):
        return {}
    monkeypatch.setattr("sakhi.apps.api.services.memory.recall.memory_recall", fake_memory_recall)
    monkeypatch.setattr("sakhi.apps.api.routes.turn_v2.compute_fast_rhythm_soul_frame", lambda *args, **kwargs: {})
    monkeypatch.setattr("sakhi.apps.api.routes.turn_v2.compute_fast_esr_frame", lambda *args, **kwargs: {})
    monkeypatch.setattr("sakhi.apps.api.routes.turn_v2.compute_fast_identity_momentum", lambda *args, **kwargs: {})
    monkeypatch.setattr("sakhi.apps.api.routes.turn_v2.compute_fast_identity_timeline_frame", lambda *args, **kwargs: {})
    monkeypatch.setattr("sakhi.apps.api.routes.turn_v2.compute_fast_narrative", lambda *args, **kwargs: {})

    class PB:
        @staticmethod
        async def get_brain_state(*args, **kwargs):
            return {}
    monkeypatch.setattr("sakhi.apps.api.routes.turn_v2.personal_brain", PB(), raising=False)
    monkeypatch.setattr("sakhi.apps.api.routes.turn_v2.compute_behavior_profile", lambda *args, **kwargs: {}, raising=False)
    monkeypatch.setattr("sakhi.apps.api.routes.turn_v2.q", fake_q, raising=False)

    app.dependency_overrides[auth_deps.get_current_user_id] = lambda: "user"

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post("/v2/turn", json={"text": "hello"})
    assert resp.status_code == 200
    body = resp.json()
    assert "daily_reflection" in body
