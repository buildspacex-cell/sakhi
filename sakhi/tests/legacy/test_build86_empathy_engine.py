import os
import pytest

# env to satisfy auth import
os.environ.setdefault("SUPABASE_URL", "http://localhost")
os.environ.setdefault("SUPABASE_ANON_KEY", "dummy")

from httpx import AsyncClient, ASGITransport

from sakhi.apps.engine.empathy import engine as empathy_engine
from sakhi.apps.api.routes import turn_v2
from sakhi.apps.api.deps import auth as auth_deps
from sakhi.apps.api.main import app
from sakhi.apps.api.main import app


@pytest.mark.asyncio
async def test_empathy_patterns(monkeypatch):
    async def fake_q(sql, *args, **kwargs):
        if "FROM personal_model" in sql:
            return {
                "emotion_state": {"mode": "neutral", "drift": -0.1},
                "forecast_state": {"emotion_forecast": {"fatigue": 0.7}, "clarity_forecast": {}, "risk_windows": {}},
                "conflict_state": {"conflict_score": 0.2},
                "coherence_state": {"coherence_score": 0.8},
            }
        return {}

    async def fake_resolve(pid):
        return pid

    async def fake_exec(*args, **kwargs):
        return None

    monkeypatch.setattr(empathy_engine, "q", fake_q)
    monkeypatch.setattr(empathy_engine, "dbexec", fake_exec)
    monkeypatch.setattr(empathy_engine, "resolve_person_id", fake_resolve)

    state = await empathy_engine.compute_empathy("user", "tired today")
    assert state["pattern"] == "gentle_grounding"
    assert "fatigue" not in state["instruction"].lower() or "avoid" in state["instruction"].lower()


@pytest.mark.asyncio
async def test_empathy_in_turn(monkeypatch):
    async def fake_empathy(uid, text):
        return {"pattern": "clarity_support", "instruction": "Provide structure.", "emotion_context": {"current_emotion": "neutral", "intensity": 0.2}, "updated_at": "now"}

    async def fake_tone(uid):
        return {"final": "warm"}

    async def fake_reply(person_id, user_text, metadata=None, behavior_profile=None):
        assert metadata and metadata.get("empathy_state")
        return {"reply": "ok", "tone_blueprint": {"style": "auto"}, "journaling_ai": None}

    async def fake_orchestrate_turn(**kwargs):
        return {"brain": {}, "intents": [], "plans": [], "triage": {}, "topics": [], "emotion": {}, "pattern_sense": {}, "forecast_state": {}}

    test_person_id = "00000000-0000-0000-0000-000000000001"

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
    monkeypatch.setattr("sakhi.apps.engine.microreg.engine.compute_microreg", lambda *args, **kwargs: {"pattern": "neutral_balance"})
    async def fake_resolve(pid):
        return test_person_id
    monkeypatch.setattr("sakhi.apps.api.routes.turn_v2.resolve_person_id", fake_resolve)
    async def fake_unified(person_id, text):
        return {"brain": {"emotion_state": {}, "soul_state": {}, "rhythm_state": {}}, "intents": [], "plans": [], "triage": {}, "topics": [], "emotion": {}, "pattern_sense": {}, "forecast_state": {}}
    monkeypatch.setattr("sakhi.apps.api.routes.turn_v2.run_unified_turn", fake_unified)
    monkeypatch.setattr(turn_v2, "personal_brain", type("pb", (), {"get_brain_state": lambda *args, **kwargs: {}}), raising=False)
    monkeypatch.setattr(turn_v2, "q", lambda *args, **kwargs: [], raising=False)
    app.dependency_overrides[auth_deps.get_current_user_id] = lambda: "user"

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post("/v2/turn", json={"text": "hello"})
    assert resp.status_code == 200
    assert "empathy_state" in resp.json()
