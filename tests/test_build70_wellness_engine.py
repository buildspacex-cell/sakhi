import datetime as dt

import pytest

from sakhi.apps.api.services.ingestion import unified_ingest as ingest


def test_keyword_scoring():
    text = "I feel tired and exhausted but also motivated"
    normalized = ingest._normalize_text(text)
    body_score = sum(1 for k in ingest.BODY_KEYWORDS if k in normalized)
    energy_score = sum(1 for k in ingest.ENERGY_KEYWORDS if k in normalized)
    assert body_score >= 1
    assert energy_score >= 1


@pytest.mark.asyncio
async def test_wellness_tags_applied(monkeypatch):
    calls = {"exec": 0}
    now = dt.datetime.utcnow().isoformat()

    async def fake_q(sql, *args, **kwargs):
        if "FROM memory_episodic" in sql:
            return [
                {"context_tags": [{"wellness_tags": {"body": 1, "mind": 0, "emotion": 0.1, "energy": 1}}], "updated_at": now}
            ]
        if "FROM personal_model" in sql:
            return {"long_term": {}}
        return None

    async def fake_exec(sql, *args, **kwargs):
        calls["exec"] += 1

    async def fake_embed(text):
        return [1.0, 0.0, 0.0]

    async def fake_resolve(pid):
        return pid

    async def fake_emotion(pid):
        return {}

    async def fake_mind(pid):
        return {}

    async def fake_soul(pid):
        return {}

    async def fake_identity(pid):
        return {}

    monkeypatch.setattr(ingest, "q", fake_q)
    monkeypatch.setattr(ingest, "dbexec", fake_exec)
    monkeypatch.setattr(ingest, "embed_normalized", fake_embed)
    monkeypatch.setattr(ingest, "resolve_person_id", fake_resolve)
    monkeypatch.setattr(ingest, "compute_emotion", fake_emotion)
    monkeypatch.setattr(ingest, "compute_mind", fake_mind)
    monkeypatch.setattr(ingest, "compute_soul", fake_soul)
    monkeypatch.setattr(ingest, "build_identity_graph", fake_identity)
    async def fake_existing_vector(*args, **kwargs):
        return None
    monkeypatch.setattr(ingest, "_existing_vector", fake_existing_vector)
    async def fake_update_pm(person_id, payload, **kwargs):
        return {"long_term": {}}
    monkeypatch.setattr(ingest, "update_personal_model", fake_update_pm)

    res = await ingest.ingest_heavy(
        person_id="00000000-0000-0000-0000-000000000000",
        entry_id="e-well",
        text="I feel tired but motivated today",
        ts=dt.datetime.utcnow(),
    )
    assert res.get("entry_id") == "e-well"
    assert calls["exec"] >= 1
