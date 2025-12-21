import pytest
from httpx import AsyncClient, ASGITransport

from sakhi.apps.engine.inner_dialogue import engine as inner_dialogue_engine
from sakhi.apps.api.main import app


@pytest.mark.asyncio
async def test_inner_dialogue_rules(monkeypatch):
    async def fake_align(person_id):
        return {"recommended_actions": ["do something light"]}

    async def fake_coherence(person_id):
        return {"issues": ["mismatch"]}

    async def fake_arcs(person_id):
        return [{"stage": "Climax", "momentum": 0.7}]

    async def fake_patterns(person_id):
        return {}

    async def fake_emotion(person_id):
        return {"drift": -0.3, "mode": "falling"}

    async def fake_q(sql, *args, **kwargs):
        if "FROM wellness_state_cache" in sql:
            return {"body": {"score": 0}, "mind": {"score": 3}, "emotion": {"score": -0.1}, "energy": {"score": -0.4}}
        return {}

    async def fake_resolve(pid):
        return pid

    monkeypatch.setattr(inner_dialogue_engine.alignment_engine, "compute_alignment_map", fake_align)
    monkeypatch.setattr(inner_dialogue_engine.coherence_engine, "compute_coherence", fake_coherence)
    monkeypatch.setattr(inner_dialogue_engine.narrative_engine, "compute_narrative_arcs", fake_arcs)
    monkeypatch.setattr(inner_dialogue_engine.pattern_engine, "compute_patterns", fake_patterns)
    monkeypatch.setattr(inner_dialogue_engine.emotion_engine, "compute_emotion_loop_for_person", fake_emotion)
    monkeypatch.setattr(inner_dialogue_engine, "q", fake_q)
    monkeypatch.setattr(inner_dialogue_engine, "resolve_person_id", fake_resolve)

    res = await inner_dialogue_engine.compute_inner_dialogue("person-1", "hello", {})
    assert res["guidance_intention"] == "soft realignment"
    assert res["tone"] == "warm"
    assert any("Coherence" in msg or "Coherence" in msg for msg in res["reflections"]) or "Coherence issues present." in res["reflections"]
    assert "avoid confrontation" in res["signals"]


@pytest.mark.asyncio
async def test_inner_dialogue_api(monkeypatch):
    async def fake_q(sql, *args, **kwargs):
        if "inner_dialogue_state" in sql:
            return {"inner_dialogue_state": {"tone": "warm"}}
        return None

    monkeypatch.setattr("sakhi.apps.api.routes.inner_dialogue.q", fake_q)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/v1/inner_dialogue", params={"person_id": "demo"})
    assert resp.status_code == 200
    assert resp.json().get("dialogue", {}).get("tone") == "warm"
