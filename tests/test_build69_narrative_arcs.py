import datetime as dt

import pytest

from sakhi.apps.api.services.ingestion import unified_ingest as ingest


def test_arc_templates():
    from sakhi.apps.services.narrative import narrative_templates as tmpl

    assert "Early stage" in tmpl.early_stage("music")


@pytest.mark.asyncio
async def test_arc_detection_writes_cache(monkeypatch):
    calls = {"q": 0, "exec": 0}
    now = dt.datetime.utcnow().isoformat()

    async def fake_q(sql, *args, **kwargs):
        calls["q"] += 1
        if "FROM memory_episodic" in sql:
            return [
                {"id": "1", "text": "practice guitar daily", "time_scope": now, "context_tags": [], "triage": {}, "updated_at": now},
                {"id": "2", "text": "guitar goals", "time_scope": now, "context_tags": [], "triage": {}, "updated_at": now},
                {"id": "3", "text": "love guitar practice", "time_scope": now, "context_tags": [], "triage": {}, "updated_at": now},
            ]
        if "FROM personal_model" in sql:
            return {"long_term": {}}
        return None

    async def fake_existing_vector(*args, **kwargs):
        return None

    async def fake_exec(sql, *args, **kwargs):
        calls["exec"] += 1

    monkeypatch.setattr(ingest, "q", fake_q)
    monkeypatch.setattr(ingest, "dbexec", fake_exec)
    # avoid DB in embed path
    async def fake_emotion(pid):
        return {}
    async def fake_mind(pid):
        return {}
    async def fake_soul(pid):
        return {}
    monkeypatch.setattr(ingest, "compute_emotion", fake_emotion)
    monkeypatch.setattr(ingest, "compute_mind", fake_mind)
    monkeypatch.setattr(ingest, "compute_soul", fake_soul)
    async def fake_identity_graph(pid):
        return {}
    monkeypatch.setattr(ingest, "build_identity_graph", fake_identity_graph)
    async def fake_embed(text):
        return [1.0, 0.0, 0.0]
    monkeypatch.setattr(ingest, "embed_normalized", fake_embed)
    async def fake_resolve(pid):
        return pid
    monkeypatch.setattr(ingest, "resolve_person_id", fake_resolve)
    monkeypatch.setattr(ingest, "_existing_vector", fake_existing_vector)
    async def fake_update_pm(person_id, payload, **kwargs):
        return {"long_term": {}}
    monkeypatch.setattr(ingest, "update_personal_model", fake_update_pm)

    res = await ingest.ingest_heavy(person_id="00000000-0000-0000-0000-000000000000", entry_id="e1", text="practice guitar today", ts=dt.datetime.utcnow())
    assert res.get("entry_id") == "e1"
    assert calls["exec"] >= 1
