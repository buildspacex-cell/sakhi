import datetime
import pytest

from sakhi.apps.engine.daily_reflection import engine as dr_engine
from sakhi.apps.worker.tasks import daily_reflection_worker


@pytest.mark.asyncio
async def test_generate_daily_reflection(monkeypatch):
    async def fake_q(sql, *args, **kwargs):
        if "session_continuity" in sql:
            return {
                "continuity_state": {
                    "last_text_turns": ["a", "b", "c"],
                    "last_voice_inputs": ["v"],
                    "last_tasks": ["t1", "t2"],
                    "last_emotion_snapshots": [{"risk": "low"}],
                    "last_microreg_snapshots": [{"pattern": "neutral"}],
                    "last_nudges": ["n1"],
                }
            }
        if "personal_model" in sql:
            return {"coherence_state": {"coherence_score": 0.6}, "identity_state": {"drift_score": 0.0}}
        if "forecast_cache" in sql:
            return {"forecast_state": {}}
        return {}

    async def fake_resolve(pid):
        return pid

    monkeypatch.setattr(dr_engine, "q", fake_q)
    monkeypatch.setattr(dr_engine, "resolve_person_id", fake_resolve)

    summary = await dr_engine.generate_daily_reflection("00000000-0000-0000-0000-000000000010")
    assert summary["emotional_summary"].startswith("Texts:")
    assert "final_reflection" in summary
    assert summary["coherence_note"] in {"ok", "low coherence"}


@pytest.mark.asyncio
async def test_daily_reflection_worker(monkeypatch):
    called = {"upsert": False, "pm": False}

    async def fake_generate(pid):
        return {"final_reflection": "ok", "generated_at": datetime.datetime.utcnow().isoformat()}

    async def fake_dbexec(sql, *args, **kwargs):
        if "daily_reflection_cache" in sql:
            called["upsert"] = True
        if "personal_model" in sql:
            called["pm"] = True

    async def fake_resolve(pid):
        return pid
    monkeypatch.setattr(dr_engine, "resolve_person_id", fake_resolve)
    monkeypatch.setattr(dr_engine, "generate_daily_reflection", fake_generate)
    monkeypatch.setattr(dr_engine, "dbexec", fake_dbexec)
    monkeypatch.setattr(daily_reflection_worker, "persist_daily_reflection", dr_engine.persist_daily_reflection)

    await daily_reflection_worker.run_daily_reflection("00000000-0000-0000-0000-000000000020")
    assert called["upsert"] and called["pm"]
