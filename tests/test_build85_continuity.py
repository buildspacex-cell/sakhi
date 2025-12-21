import os
import pytest
import datetime as dt

# env to satisfy auth import
os.environ.setdefault("SUPABASE_URL", "http://localhost")
os.environ.setdefault("SUPABASE_ANON_KEY", "dummy")

from sakhi.apps.engine.continuity import engine as cont_engine


@pytest.mark.asyncio
async def test_continuity_markers_thread():
    markers = cont_engine.compute_continuity_markers({"type": "text_message"}, [{"theme": "guitar"}, {"theme": "guitar"}], None)
    assert markers["continuity_thread"] == "guitar"
    assert markers["confidence"] >= 0.5


@pytest.mark.asyncio
async def test_update_continuity(monkeypatch):
    async def fake_q(sql, *args, **kwargs):
        return {"continuity_state": {}}

    async def fake_dbexec(sql, *args, **kwargs):
        return None

    async def fake_resolve(pid):
        return pid

    monkeypatch.setattr(cont_engine, "q", fake_q)
    monkeypatch.setattr(cont_engine, "dbexec", fake_dbexec)
    monkeypatch.setattr(cont_engine, "resolve_person_id", fake_resolve)

    state = await cont_engine.update_continuity(
        "user1",
        {"type": "text_message", "text": "hello", "emotion": {"mood": "calm"}, "tone_state": {"final": "warm"}, "forecast_state": {"summary": "stable"}},
        memory_short_term=[{"theme": "practice"}, {"theme": "practice"}],
        pattern_sense=None,
    )
    assert state["last_text_turns"]
    assert state["threads"]["current"] in ["practice", "general"]


@pytest.mark.asyncio
async def test_continuity_prunes(monkeypatch):
    async def fake_q(sql, *args, **kwargs):
        old_ts = (dt.datetime.utcnow() - dt.timedelta(hours=13)).isoformat()
        return {"continuity_state": {"last_text_turns": [{"ts": old_ts, "text": "old"}]}}

    async def fake_dbexec(sql, *args, **kwargs):
        return None

    async def fake_resolve(pid):
        return pid

    monkeypatch.setattr(cont_engine, "q", fake_q)
    monkeypatch.setattr(cont_engine, "dbexec", fake_dbexec)
    monkeypatch.setattr(cont_engine, "resolve_person_id", fake_resolve)

    state = await cont_engine.update_continuity("user1", {"type": "text_message", "text": "new"})
    assert len(state["last_text_turns"]) == 1
    assert state["last_text_turns"][0]["text"] == "new"
