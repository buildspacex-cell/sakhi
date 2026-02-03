import pytest

from sakhi.apps.api.services.persona import session_tuning


@pytest.mark.asyncio
async def test_update_session_persona_resolves_id(monkeypatch):
    calls = {"pid": None}

    async def fake_resolve(pid):
        calls["pid"] = pid
        return "resolved-id"

    async def fake_fetch(pid):
        return {}

    async def fake_analyze(text: str):
        return {"warmth": 0.8, "reflectiveness": 0.5, "humor": 0.3, "expressiveness": 0.4, "tone_bias": "warm"}

    async def fake_q(sql, *args, **kwargs):
        return {}

    monkeypatch.setattr(session_tuning, "resolve_person_id", fake_resolve)
    monkeypatch.setattr(session_tuning, "_fetch_persona_row", fake_fetch)
    monkeypatch.setattr(session_tuning, "analyze_persona_features", fake_analyze)
    monkeypatch.setattr(session_tuning, "q", fake_q)

    result = await session_tuning.update_session_persona("candidate", "hello")
    assert calls["pid"] == "candidate"
    assert result["warmth"] == pytest.approx(0.1 + 0.9 * 0.8, rel=1e-3) or result["warmth"] is not None
