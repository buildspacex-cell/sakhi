import asyncio
import json
import uuid
from typing import Any, Dict

import pytest

from sakhi.apps.api.services.ingestion import unified_ingest as ingest
from sakhi.apps.api.services.memory import personal_model


class FakeDB:
    def __init__(self):
        self.journal_embeddings: Dict[str, Any] = {}
        self.memory_short_term: Dict[str, Any] = {}
        self.memory_episodic: Dict[str, Any] = {}
        self.personal_model: Dict[str, Any] = {}
        self.memory_context_cache: set[str] = set()

    async def q(self, sql: str, *args, one: bool = False):
        if "journal_embeddings" in sql:
            content_hash = args[0]
            vec = self.journal_embeddings.get(content_hash)
            return {"vec": vec} if vec is not None else (None if one else [])

        if "memory_short_term" in sql and "content_hash" in sql:
            if "vector_vec" in sql:
                content_hash = args[0]
                record = self.memory_short_term.get(content_hash)
                vec = record.get("vector_vec") if record else None
                return {"vec": vec} if vec is not None else (None if one else [])
            content_hash = args[1]
            exists = content_hash in self.memory_short_term
            return {"exists": 1} if exists else (None if one else [])

        if "memory_episodic" in sql and "content_hash" in sql:
            if "vector_vec" in sql:
                content_hash = args[0]
                record = self.memory_episodic.get(content_hash)
                vec = record.get("vector_vec") if record else None
                return {"vec": vec} if vec is not None else (None if one else [])
            content_hash = args[1]
            exists = content_hash in self.memory_episodic
            return {"exists": 1} if exists else (None if one else [])

        if "FROM personal_model" in sql:
            person_id = args[0]
            return self.personal_model.get(person_id)

        return None if one else []

    async def exec(self, sql: str, *args):
        if "INSERT INTO journal_embeddings" in sql:
            entry_id, model, vec, content_hash = args[:4]
            self.journal_embeddings[content_hash] = list(vec)
            return

        if "INSERT INTO memory_short_term" in sql:
            (
                record_id,
                person_id,
                entry_id,
                text,
                vec,
                content_hash,
                layer,
                triage,
            ) = args
            if content_hash not in self.memory_short_term:
                self.memory_short_term[content_hash] = {
                    "id": record_id,
                    "person_id": person_id,
                    "entry_id": entry_id,
                    "text": text,
                    "vector_vec": list(vec),
                    "content_hash": content_hash,
                    "layer": layer,
                    "triage": triage,
                }
            return

        if "INSERT INTO memory_episodic" in sql:
            (
                record_id,
                person_id,
                entry_id,
                text,
                vec,
                content_hash,
                time_scope,
            ) = args[:7]
            if content_hash not in self.memory_episodic:
                self.memory_episodic[content_hash] = {
                    "id": record_id,
                    "person_id": person_id,
                    "entry_id": entry_id,
                    "text": text,
                    "vector_vec": list(vec),
                    "content_hash": content_hash,
                    "time_scope": time_scope,
                }
            return

        if "INSERT INTO personal_model" in sql:
            person_id, short_term, long_term, _ = args
            self.personal_model[person_id] = {
                "short_term": json.loads(short_term),
                "long_term": json.loads(long_term),
            }
            return

        if "INSERT INTO memory_context_cache" in sql:
            person_id = args[0]
            self.memory_context_cache.add(person_id)
            return

    async def fetchrow(self, sql: str, *args):
        if "FROM personal_model" in sql:
            person_id = args[0]
            return self.personal_model.get(person_id)
        return None


def _patch_db(monkeypatch: pytest.MonkeyPatch, fake: FakeDB):
    monkeypatch.setattr(ingest, "dbexec", fake.exec)
    monkeypatch.setattr(ingest, "q", fake.q)
    monkeypatch.setattr(ingest, "_processed_fast", set())
    monkeypatch.setattr(ingest, "_processed_heavy", set())
    monkeypatch.setattr(personal_model, "dbexec", fake.exec)
    monkeypatch.setattr(personal_model, "dbfetchrow", fake.fetchrow)
    async def _resolve(pid):
        return pid

    monkeypatch.setattr(ingest, "resolve_person_id", _resolve)
    monkeypatch.setattr(ingest, "extract", lambda text, ts: {})
    async def _noop_state(person_id):
        return {"summary": None, "confidence": 0.0, "metrics": {}, "updated_at": "now"}

    monkeypatch.setattr(ingest, "compute_emotion", _noop_state)
    monkeypatch.setattr(ingest, "compute_mind", _noop_state)
    async def _noop_soul(person_id):
        return {"summary": None, "confidence": 0.0, "metrics": {}, "updated_at": "now", "signal_count": 0}

    monkeypatch.setattr(ingest, "compute_soul", _noop_soul)
    async def _noop_identity(person_id):
        return {}

    monkeypatch.setattr(ingest, "build_identity_graph", _noop_identity)


@pytest.mark.asyncio
async def test_global_dedup(monkeypatch: pytest.MonkeyPatch):
    fake_db = FakeDB()
    calls = {"count": 0}

    async def fake_embed(text: str):
        calls["count"] += 1
        return [1.0, 1.0]

    _patch_db(monkeypatch, fake_db)
    monkeypatch.setattr(ingest, "embed_normalized", fake_embed)

    await ingest.ingest_heavy(person_id="p1", entry_id=str(uuid.uuid4()), text="Hello World")
    await ingest.ingest_heavy(person_id="p1", entry_id=str(uuid.uuid4()), text=" hello   world ")

    assert calls["count"] == 1
    assert len(fake_db.memory_short_term) == 1
    observations = fake_db.personal_model["p1"]["long_term"]["observations"]
    assert len(observations) == 1


@pytest.mark.asyncio
async def test_vector_reuse(monkeypatch: pytest.MonkeyPatch):
    fake_db = FakeDB()
    calls = {"count": 0}

    async def fake_embed(text: str):
        calls["count"] += 1
        if calls["count"] > 1:
            raise AssertionError("embed_normalized called more than once for duplicate content")
        return [0.5, 0.5]

    _patch_db(monkeypatch, fake_db)
    monkeypatch.setattr(ingest, "embed_normalized", fake_embed)

    await ingest.ingest_heavy(person_id="p2", entry_id=str(uuid.uuid4()), text="Reuse me")
    await ingest.ingest_heavy(person_id="p2", entry_id=str(uuid.uuid4()), text="reuse   me")

    assert calls["count"] == 1
    vec_st = next(iter(fake_db.memory_short_term.values()))["vector_vec"]
    vec_ep = next(iter(fake_db.memory_episodic.values()))["vector_vec"]
    assert vec_st == vec_ep == [0.5, 0.5]


@pytest.mark.asyncio
async def test_merged_vector_average(monkeypatch: pytest.MonkeyPatch):
    fake_db = FakeDB()
    vectors = {
        "first": [1.0, 1.0],
        "second": [3.0, 3.0],
    }

    async def fake_embed(text: str):
        if "alpha" in text:
            return vectors["first"]
        return vectors["second"]

    _patch_db(monkeypatch, fake_db)
    monkeypatch.setattr(ingest, "embed_normalized", fake_embed)

    await ingest.ingest_heavy(person_id="p3", entry_id=str(uuid.uuid4()), text="Alpha note")
    await ingest.ingest_heavy(person_id="p3", entry_id=str(uuid.uuid4()), text="Beta idea")

    merged = fake_db.personal_model["p3"]["long_term"]["merged_vector"]
    assert merged == [2.0, 2.0]


@pytest.mark.asyncio
async def test_context_cache_row_created(monkeypatch: pytest.MonkeyPatch):
    fake_db = FakeDB()

    async def fake_embed(text: str):
        return [0.1, 0.1]

    _patch_db(monkeypatch, fake_db)
    monkeypatch.setattr(ingest, "embed_normalized", fake_embed)

    await ingest.ingest_heavy(person_id="p4", entry_id=str(uuid.uuid4()), text="Cache me")
    assert "p4" in fake_db.memory_context_cache


def test_normalization_hash_consistency():
    n = personal_model._normalize_text
    h = personal_model._hash_text
    base = h(n("Hello   WORLD"))
    assert base == h(n("hello world"))
    assert base == h(n("  HELLO world  "))
