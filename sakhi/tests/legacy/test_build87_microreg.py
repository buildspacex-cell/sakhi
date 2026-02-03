import pytest

from sakhi.apps.engine.microreg import engine as microreg_engine


@pytest.mark.asyncio
async def test_microreg_patterns(monkeypatch):
    # prevent DB writes
    monkeypatch.setattr(microreg_engine, "dbexec", lambda *args, **kwargs: None, raising=False)
    async def fake_q(sql, *args, **kwargs):
        return {
            "forecast_state": {
                "emotion_forecast": {"fatigue_prob": 0.7, "irritability_prob": 0.1, "motivation_prob": 0.0},
                "clarity_forecast": {"confusion_score": 0.1},
                "risk_windows": {},
            },
            "conflict_state": {"conflict_score": 0.1},
        }
    async def fake_resolve(pid):
        return pid
    monkeypatch.setattr(microreg_engine, "q", fake_q)
    monkeypatch.setattr(microreg_engine, "resolve_person_id", fake_resolve)

    state = await microreg_engine.compute_microreg("00000000-0000-0000-0000-000000000001", "i feel tired")
    assert state["pattern"] == "grounding"
    assert state["instruction"]


@pytest.mark.asyncio
async def test_microreg_in_turn(monkeypatch):
    from httpx import AsyncClient, ASGITransport
    from sakhi.apps.api.main import app
    from sakhi.apps.api.deps import auth as auth_deps
    from sakhi.apps.api.routes import turn_v2

    async def fake_microreg(pid, text):
        return {"pattern": "supportive_momentum", "instruction": "Affirm motivation; keep tone uplifting but steady; offer one next step.", "shift": "upward", "amplitude": 0.1, "risk": "low", "updated_at": "now"}

    async def fake_empathy(uid, text):
        return {"pattern": "clarity_support", "instruction": "Provide structure.", "emotion_context": {"current_emotion": "neutral", "intensity": 0.2}, "updated_at": "now"}

    async def fake_tone(uid):
        return {"final": "warm"}

    async def fake_reply(person_id, user_text, metadata=None, behavior_profile=None):
        assert metadata.get("microreg_state")
        return {"reply": "ok", "tone_blueprint": {"style": "auto"}, "journaling_ai": None}

    async def fake_orchestrate_turn(**kwargs):
        return {"brain": {}, "intents": [], "plans": [], "triage": {}, "topics": [], "emotion": {}, "pattern_sense": {}, "forecast_state": {}}

    test_person_id = "00000000-0000-0000-0000-000000000002"

    monkeypatch.setattr("sakhi.apps.api.routes.turn_v2.compute_microreg", fake_microreg)
    monkeypatch.setattr("sakhi.apps.api.routes.turn_v2.compute_empathy", fake_empathy)
    monkeypatch.setattr("sakhi.apps.api.routes.turn_v2.compute_tone", fake_tone)
    monkeypatch.setattr("sakhi.apps.api.routes.turn_v2.generate_reply", fake_reply)
    monkeypatch.setattr("sakhi.apps.api.routes.turn_v2.compute_alignment", lambda *args, **kwargs: {})
    monkeypatch.setattr("sakhi.apps.api.routes.turn_v2.orchestrate_turn", fake_orchestrate_turn)
    monkeypatch.setattr("sakhi.apps.api.services.memory.recall.memory_recall", lambda **kwargs: {})
    monkeypatch.setattr("sakhi.apps.api.services.journaling.enrich.call_llm", lambda **kwargs: {})
    monkeypatch.setattr("sakhi.apps.api.routes.turn_v2.compute_fast_rhythm_soul_frame", lambda *args, **kwargs: {})
    monkeypatch.setattr("sakhi.apps.api.routes.turn_v2.compute_fast_esr_frame", lambda *args, **kwargs: {})
    monkeypatch.setattr("sakhi.apps.api.routes.turn_v2.compute_fast_identity_momentum", lambda *args, **kwargs: {})
    monkeypatch.setattr("sakhi.apps.api.routes.turn_v2.compute_fast_identity_timeline_frame", lambda *args, **kwargs: {})
    monkeypatch.setattr("sakhi.apps.api.routes.turn_v2.compute_fast_narrative", lambda *args, **kwargs: {})
    monkeypatch.setattr("sakhi.apps.engine.continuity.engine.update_continuity", lambda *args, **kwargs: {})
    monkeypatch.setattr("sakhi.apps.engine.continuity.engine.load_continuity", lambda *args, **kwargs: {})
    async def fake_resolve(pid):
        return test_person_id
    monkeypatch.setattr("sakhi.apps.api.routes.turn_v2.resolve_person_id", fake_resolve)
    async def fake_run_unified(*args, **kwargs):
        return {"brain": {"emotion_state": {}, "soul_state": {}, "rhythm_state": {}}, "intents": [], "plans": [], "triage": {}, "topics": [], "emotion": {}, "pattern_sense": {}, "forecast_state": {}}
    monkeypatch.setattr("sakhi.apps.api.routes.turn_v2.run_unified_turn", fake_run_unified)
    monkeypatch.setattr(turn_v2, "q", lambda *args, **kwargs: [], raising=False)

    app.dependency_overrides[auth_deps.get_current_user_id] = lambda: "user"

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post("/v2/turn", json={"text": "hello"})
    assert resp.status_code == 200
    body = resp.json()
    assert "microreg_state" in body
