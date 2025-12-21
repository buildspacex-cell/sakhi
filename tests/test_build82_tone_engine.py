import pytest
from httpx import AsyncClient, ASGITransport

from sakhi.apps.engine.tone import engine as tone_engine
from sakhi.apps.api.main import app


@pytest.mark.asyncio
async def test_tone_modifiers(monkeypatch):
    async def fake_q(sql, *args, **kwargs):
        if "FROM personal_model" in sql:
            return {
                "persona_state": {"custom_tone": None},
                "coherence_state": {"coherence_map": {"thought": 0.3}, "coherence_score": 0.3},
                "conflict_state": {"conflict_score": 0.7},
                "forecast_state": {"emotion_forecast": {"fatigue": 0.7, "irritability": 0.6, "motivation": 0.2}},
                "emotion_state": {"mode": "falling"},
            }
        return None

    async def fake_resolve(pid):
        return pid

    async def fake_exec(sql, *args, **kwargs):
        return None

    monkeypatch.setattr(tone_engine, "q", fake_q)
    monkeypatch.setattr(tone_engine, "resolve_person_id", fake_resolve)
    monkeypatch.setattr(tone_engine, "dbexec", fake_exec)

    tone = await tone_engine.compute_tone("demo")
    assert "soft" in tone["modifiers"]
    assert "de-escalating" in tone["modifiers"]
    assert "guiding" in tone["modifiers"]
    assert "non-challenging" in tone["modifiers"]
    assert tone["final"].startswith("warm")


@pytest.mark.asyncio
async def test_tone_api_integration(monkeypatch):
    async def fake_tone(user_id):
        return {"final": "warm + soft", "base": "warm", "modifiers": ["soft"], "updated_at": "now"}

    async def fake_reply(person_id, user_text, metadata=None, behavior_profile=None):
        # ensure tone_state propagated in metadata
        assert metadata and metadata.get("tone_state")
        return {"reply": "ok", "tone_blueprint": {"style": "auto"}, "journaling_ai": None}

    async def fake_orchestrate_turn(**kwargs):
        return {"brain": {}, "intents": [], "plans": [], "triage": {}, "topics": [], "emotion": {}}

    monkeypatch.setattr("sakhi.apps.api.routes.turn_v2.compute_tone", fake_tone)
    monkeypatch.setattr("sakhi.apps.api.routes.turn_v2.generate_reply", fake_reply)
    monkeypatch.setattr("sakhi.apps.api.routes.turn_v2.compute_alignment", lambda *args, **kwargs: {})
    monkeypatch.setattr("sakhi.apps.api.routes.turn_v2.orchestrate_turn", fake_orchestrate_turn)
    monkeypatch.setattr("sakhi.apps.api.routes.turn_v2.compute_fast_rhythm_soul_frame", lambda *args, **kwargs: {})
    monkeypatch.setattr("sakhi.apps.api.routes.turn_v2.compute_fast_esr_frame", lambda *args, **kwargs: {})
    monkeypatch.setattr("sakhi.apps.api.routes.turn_v2.compute_fast_identity_momentum", lambda *args, **kwargs: {})
    monkeypatch.setattr("sakhi.apps.api.routes.turn_v2.compute_fast_identity_timeline_frame", lambda *args, **kwargs: {})
    monkeypatch.setattr("sakhi.apps.api.routes.turn_v2.compute_fast_narrative", lambda *args, **kwargs: {})
    monkeypatch.setattr("sakhi.apps.api.services.memory.recall.memory_recall", lambda **kwargs: {})
    monkeypatch.setattr("sakhi.apps.api.services.journaling.enrich.call_llm", lambda **kwargs: {})

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post("/v2/turn", json={"text": "hello"})
    assert resp.status_code == 200
    assert resp.json().get("tone_used") == "warm + soft"
