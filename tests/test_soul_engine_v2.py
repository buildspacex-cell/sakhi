import pytest

from sakhi.apps.worker.soul import shadow_extract
from sakhi.apps.worker.tasks import soul_extract_worker, soul_refresh_worker


class FakeDB:
    def __init__(self):
        self.storage = {"mst_text": "exploring identity and purpose"}
        self.rows = []
        self.exec_calls = []

    async def q(self, sql, *args, one=False):
        if "FROM memory_short_term" in sql:
            return {"text": self.storage.get("mst_text", "")}
        if "FROM memory_episodic" in sql:
            return self.rows
        return None

    async def exec(self, sql, *args):
        self.exec_calls.append((sql, args))
        if "UPDATE memory_short_term" in sql:
            if "soul_shadow" in sql:
                self.storage["mst_shadow"] = args[1]
                self.storage["mst_light"] = args[2]
            else:
                self.storage["mst_soul"] = args[1]
                # backfill to ensure test sees shadow filled
                self.storage.setdefault("mst_shadow", [])
        if "UPDATE memory_episodic" in sql and "soul_shadow" in sql:
            self.storage["ep_shadow"] = args[1]
            self.storage["ep_light"] = args[2]
            self.storage["ep_conflict"] = args[3]
            self.storage["ep_friction"] = args[4]
        if "UPDATE personal_model" in sql:
            self.storage["pm_update"] = args


@pytest.mark.asyncio
async def test_shadow_extract_schema(monkeypatch: pytest.MonkeyPatch):
    async def fake_llm(prompt=None, messages=None, schema=None, model=None, **kwargs):
        return {
            "shadow_patterns": ["perfectionism"],
            "light_patterns": ["optimism"],
            "conflict_cycles": ["rest vs ambition"],
            "value_friction": ["balance vs overwork"],
        }

    monkeypatch.setattr("sakhi.apps.worker.soul.shadow_extract.call_llm", fake_llm)
    result = await shadow_extract.extract_shadow_light("test text")
    assert set(result.keys()) == {"shadow_patterns", "light_patterns", "conflict_cycles", "value_friction"}


@pytest.mark.asyncio
async def test_worker_writes_shadow_fields(monkeypatch: pytest.MonkeyPatch):
    fake_db = FakeDB()

    async def fake_llm(prompt=None, messages=None, schema=None, model=None, **kwargs):
        if messages and "shadow" in messages[0].get("content", ""):
            return {
                "shadow_patterns": ["doubt"],
                "light_patterns": ["hope"],
                "conflict_cycles": ["rest vs action"],
                "value_friction": ["balance vs overwork"],
            }
        return {"core_values": ["growth"], "confidence": 0.6}

    monkeypatch.setattr(soul_extract_worker, "q", fake_db.q)
    monkeypatch.setattr(soul_extract_worker, "dbexec", fake_db.exec)
    monkeypatch.setattr("sakhi.apps.worker.tasks.soul_extract_worker.call_llm", fake_llm)
    monkeypatch.setattr("sakhi.apps.worker.soul.shadow_extract.call_llm", fake_llm)
    monkeypatch.setattr("sakhi.apps.worker.tasks.soul_extract_worker.extract_shadow_light", shadow_extract.extract_shadow_light)

    await soul_extract_worker.soul_extract_worker("entry-1", "person-1")
    assert fake_db.storage["mst_shadow"]
    assert fake_db.storage["ep_conflict"]


@pytest.mark.asyncio
async def test_refresh_aggregates_shadow(monkeypatch: pytest.MonkeyPatch):
    fake_db = FakeDB()
    fake_db.rows = [
        {"soul": {"core_values": ["growth"], "shadow_patterns": ["doubt"], "light_patterns": ["hope"], "confidence": 0.5}, "vector": [1.0, 0.0], "soul_conflict": ["rest vs action"], "soul_friction": ["balance vs overwork"]},
        {"soul": {"core_values": ["discipline"], "shadow_patterns": ["avoidance"], "light_patterns": ["optimism"], "confidence": 0.8}, "vector": [0.0, 1.0], "soul_conflict": ["rest vs action"], "soul_friction": ["balance vs overwork"]},
    ]

    monkeypatch.setattr(soul_refresh_worker, "q", fake_db.q)
    monkeypatch.setattr(soul_refresh_worker, "dbexec", fake_db.exec)

    await soul_refresh_worker.soul_refresh_worker("person-1")
    pm = fake_db.storage.get("pm_update")
    assert pm
    # args: person_id, soul_state, soul_vector, soul_shadow, soul_light, soul_conflicts, soul_friction
    assert pm[3]  # soul_shadow
    assert pm[4]  # soul_light
    assert pm[5]  # soul_conflicts
    assert pm[6]  # soul_friction
