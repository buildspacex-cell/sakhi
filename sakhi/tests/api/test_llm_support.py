from __future__ import annotations

import importlib
import json
import os
from pathlib import Path

import pytest

from sakhi.apps.api.core.llm import LLMResponseError


@pytest.fixture(autouse=True)
def reset_llm_router():
    from sakhi.apps.api.core import llm as llm_module

    original = llm_module._ROUTER
    llm_module._ROUTER = None
    yield
    llm_module._ROUTER = original


@pytest.fixture(autouse=True)
def reset_config_loader_env():
    yield
    config_loader = importlib.import_module("sakhi.apps.api.core.config_loader")
    importlib.reload(config_loader)


def test_config_loader_hot_reload(tmp_path, monkeypatch):
    prompt_dir = tmp_path / "prompts"
    prompt_dir.mkdir()
    prompt_file = prompt_dir / "demo.json"
    prompt_file.write_text(json.dumps({"system": "v1"}), encoding="utf-8")

    monkeypatch.setenv("SAKHI_PROMPTS_DIR", str(prompt_dir))
    monkeypatch.setenv("SAKHI_CONFIG_HOT", "1")
    monkeypatch.setenv("SAKHI_ENVIRONMENT", "development")

    config_loader = importlib.import_module("sakhi.apps.api.core.config_loader")
    importlib.reload(config_loader)

    first = config_loader.get_prompt("demo")
    assert first["system"] == "v1"

    prompt_file.write_text(json.dumps({"system": "v2"}), encoding="utf-8")
    second = config_loader.get_prompt("demo")
    assert second["system"] == "v2"


@pytest.mark.asyncio
async def test_call_llm_repair_loop(monkeypatch):
    from pydantic import BaseModel
    from sakhi.apps.api.core import llm as llm_module

    class StubResponse:
        def __init__(self, text: str):
            self.text = text
            self.provider = "stub"
            self.model = "stub-model"
            self.usage = {"calls": 1}

    class StubRouter:
        def __init__(self):
            self.calls = 0

        async def chat(self, messages, model=None, force_json=False):
            self.calls += 1
            if self.calls == 1:
                return StubResponse("not-json")
            return StubResponse(json.dumps({"ok": True}))

    class DemoSchema(BaseModel):
        ok: bool

    llm_module.set_router(StubRouter())
    result = await llm_module.call_llm(messages=[{"role": "user", "content": "{}"}], schema=DemoSchema)
    assert result.ok is True


@pytest.mark.asyncio
async def test_compute_state_vector_fallback(monkeypatch):
    from apps.worker.enrich import state_vector

    async def fake_call_llm(*args, **kwargs):
        raise LLMResponseError("boom")

    monkeypatch.setattr(state_vector, "call_llm", fake_call_llm)
    observations = [{"lens": "self", "kind": "valence", "payload": {"valence": -0.4}, "confidence": 0.6}]
    vector, error, method = await state_vector.compute_state_vector(observations, "Feeling scattered and anxious")
    assert vector is not None
    assert method == "heuristic"
    assert isinstance(error, str)
    assert any("heuristic" in note.lower() for note in vector.notes)


@pytest.mark.asyncio
async def test_generate_phrase_policy(monkeypatch):
    from sakhi.apps.api.clarity import phrasing
    from sakhi.apps.api.core.response_policy import PolicyDecision
    from sakhi.apps.api.core.llm_schemas import PhraseOutput

    async def allow_policy(*_args, **_kwargs):
        return PolicyDecision(allow=True, reason="enabled", meta={"recent_count": 0})

    async def deny_policy(*_args, **_kwargs):
        return PolicyDecision(allow=False, reason="state_confidence_low", meta={"state_confidence": 0.4})

    async def fake_duplicate(*_args, **_kwargs):
        return False

    async def fake_record(*_args, **_kwargs):
        fake_record.called = True

    fake_record.called = False

    async def fake_call_llm(*_args, **_kwargs):
        return PhraseOutput(lines=["Try a short walk"], style="nudge", confidence=0.8)

    monkeypatch.setattr(phrasing, "should_suggest", allow_policy)
    monkeypatch.setattr(phrasing, "has_recent_duplicate", fake_duplicate)
    monkeypatch.setattr(phrasing, "record_suggestion", fake_record)
    monkeypatch.setattr(phrasing, "call_llm", fake_call_llm)

    ctx = {"intent_need": "plan", "input_text": "Need to get moving", "support": {"aspects": []}}
    delivered = await phrasing.generate_phrase("person-1", ctx, None)
    assert delivered["lines"]
    assert fake_record.called is True

    monkeypatch.setattr(phrasing, "should_suggest", deny_policy)
    muted = await phrasing.generate_phrase("person-1", ctx, None)
    assert muted["meta"]["skipped"] is True
    assert muted["meta"]["reason"] == "state_confidence_low"
