import pytest

from sakhi.apps.brain.engines import soul_engine
from sakhi.apps.worker.tasks import soul_extract_worker, soul_refresh_worker


class FakeDB:
    def __init__(self):
        self.storage = {}
        self.exec_calls = []
        self.rows = []

    async def q(self, sql, *args, one=False):
        if "FROM memory_short_term" in sql:
            return {"text": self.storage.get("mst_text", "")}
        if "FROM memory_episodic" in sql:
            return self.rows
        if "FROM personal_model" in sql:
            return self.storage.get("pm_row")
        return None

    async def exec(self, sql, *args):
        self.exec_calls.append((sql, args))
        if "UPDATE memory_short_term" in sql:
            if "soul_shadow" in sql:
                self.storage["mst_shadow"] = args[1]
                self.storage["mst_light"] = args[2]
                return
            self.storage["mst_soul"] = args[1]
        if "UPDATE memory_episodic" in sql:
            if "soul_shadow" in sql:
                self.storage["ep_shadow"] = args[1]
                self.storage["ep_light"] = args[2]
                self.storage["ep_conflict"] = args[3]
                self.storage["ep_friction"] = args[4]
                return
            self.storage["me_soul"] = args[1]
        if "UPDATE personal_model" in sql:
            self.storage["pm_update"] = {"soul_state": args[1], "soul_vector": args[2]}


@pytest.mark.asyncio
async def test_soul_extraction_worker(monkeypatch: pytest.MonkeyPatch):
    fake_db = FakeDB()
    fake_db.storage["mst_text"] = "I want to be disciplined and balanced"

    async def fake_llm(prompt=None, messages=None, schema=None, model=None, **kwargs):
        return {"core_values": ["discipline"], "longing": ["balanced"], "confidence": 0.7}

    monkeypatch.setattr(soul_extract_worker, "q", fake_db.q)
    monkeypatch.setattr(soul_extract_worker, "dbexec", fake_db.exec)
    monkeypatch.setattr("sakhi.apps.worker.tasks.soul_extract_worker.call_llm", fake_llm)

    result = await soul_extract_worker.soul_extract_worker("entry-1", "person-1")
    assert result["soul"]["core_values"] == ["discipline"]
    assert fake_db.storage["mst_soul"]["core_values"] == ["discipline"]
    assert fake_db.storage["me_soul"]["core_values"] == ["discipline"]


@pytest.mark.asyncio
async def test_soul_refresh_worker(monkeypatch: pytest.MonkeyPatch):
    fake_db = FakeDB()
    fake_db.rows = [
        {"soul": {"core_values": ["growth"], "confidence": 0.5}, "vector": [1.0, 0.0]},
        {"soul": {"core_values": ["discipline"], "confidence": 0.8}, "vector": [0.0, 1.0]},
    ]

    monkeypatch.setattr(soul_refresh_worker, "q", fake_db.q)
    monkeypatch.setattr(soul_refresh_worker, "dbexec", fake_db.exec)

    result = await soul_refresh_worker.soul_refresh_worker("person-1")
    assert result["updated"] is True
    assert fake_db.storage["pm_update"]["soul_state"]["core_values"]
    assert fake_db.storage["pm_update"]["soul_vector"]


@pytest.mark.asyncio
async def test_soul_engine_update_soul_state():
    observations = [
        "I want to be the kind of person who practices daily",
        "Music and guitar give me energy",
        "I need discipline and balance",
    ]
    result = await soul_engine.update_soul_state("p1", observations, embeddings=[[1.0, 0.0], [0.5, 0.5]])
    assert "core_values" in result
    assert any("discipline" in v for v in result["core_values"])
    assert result["direction_vector"]
