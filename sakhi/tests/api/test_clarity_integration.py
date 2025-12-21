from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

import pytest
from httpx import AsyncClient

from fastapi import FastAPI

from sakhi.apps.api.core.response_policy import PolicyDecision
from sakhi.apps.api.routers.clarity import router as clarity_router

test_app = FastAPI()
test_app.include_router(clarity_router)


@pytest.fixture(autouse=True)
def setup_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SAKHI_ENVIRONMENT", "test")
    monkeypatch.setenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/sakhi")


@pytest.mark.asyncio
async def test_clarity_evaluate_records_suggestion(monkeypatch: pytest.MonkeyPatch) -> None:
    person_id = "person-test"
    recorded: List[Dict[str, Any]] = []
    updated_models: List[Dict[str, Any]] = []

    async def fake_record_suggestion(pid: str, **payload: Any) -> None:
        recorded.append({"person_id": pid, **payload})

    async def fake_has_duplicate(*_args, **_kwargs) -> bool:
        return False

    async def fake_should_suggest(*_args, **_kwargs) -> PolicyDecision:
        return PolicyDecision(allow=True, reason="enabled", meta={"recent_count": 0})

    async def fake_q(sql: str, *args: Any, one: bool = False) -> Any:
        lower = sql.lower()
        if "person_summary_v" in lower:
            row = {
                "person_id": person_id,
                "goals": [{"title": "Run a 5k", "status": "proposed"}],
                "values_prefs": [{"key": "evening_boundary", "value": {"after": "20:00"}, "confidence": 0.6}],
                "themes": ["health"],
                "avg_mood_7d": 0.5,
                "aspect_snapshot": [
                    {"aspect": "time", "value": {"score": 0.6}},
                    {"aspect": "energy", "value": {"score": 0.4}},
                ],
            }
            return row if one else [row]
        if "short_horizon_v" in lower:
            row = {
                "person_id": person_id,
                "recent_tags": [{"tag": "fitness", "n": 2}],
                "avg_mood_7d": 0.5,
            }
            return row if one else [row]
        if "observations" in lower:
            return []
        return None if one else []

    async def fake_exec(*_args, **_kwargs) -> str:
        return "OK"

    async def fake_call_llm(*args: Any, **kwargs: Any) -> Any:
        schema = kwargs.get("schema")
        if schema is None:
            return json.dumps(
                {
                    "options": [
                        {"title": "Option A", "steps": ["Step 1"], "why": "Context rich plan"}
                    ],
                    "notes": ["note"],
                    "clarifications": [],
                    "risk_flags": [],
                }
            )
        # PhraseOutput expected
        return schema.parse_obj(
            {
                "lines": ["How about a light walk after dinner?"],
                "style": "nudge",
                "confidence": 0.8,
                "safety": "ok",
            }
        )

    async def fake_ensure_person_id(base_ref: Optional[str]) -> str:
        return person_id

    async def fake_persist_trace(_payload: Dict[str, Any]) -> None:
        return None

    async def fake_update_personal_model(_pid: str, summary: Dict[str, Any]) -> None:
        updated_models.append({"person_id": _pid, "summary": summary})

    # Monkeypatch dependencies throughout pipeline
    monkeypatch.setattr("sakhi.apps.api.core.db.q", fake_q)
    monkeypatch.setattr("sakhi.apps.api.core.db.exec", fake_exec)
    monkeypatch.setattr("sakhi.apps.api.core.persons.ensure_person_id", fake_ensure_person_id)
    monkeypatch.setattr("sakhi.apps.api.core.llm.call_llm", fake_call_llm)
    monkeypatch.setattr("sakhi.apps.api.clarity.phrasing.has_recent_duplicate", fake_has_duplicate)
    monkeypatch.setattr("sakhi.apps.api.clarity.phrasing.record_suggestion", fake_record_suggestion)
    monkeypatch.setattr("sakhi.apps.api.clarity.phrasing.should_suggest", fake_should_suggest)
    monkeypatch.setattr("sakhi.apps.api.core.trace_store.persist_trace", fake_persist_trace)
    monkeypatch.setattr("sakhi.apps.api.services.memory.personal_model.update_personal_model", fake_update_personal_model)

    async with AsyncClient(app=test_app, base_url="http://test") as client:
        response = await client.post(
            "/clarity/evaluate",
            json={"person_id": person_id, "user_text": "Need help sticking to my walk habit", "need": "plan"},
        )

    assert response.status_code == 200
    payload = response.json()

    phrase = payload.get("phrase")
    assert phrase and phrase.get("lines") == ["How about a light walk after dinner?"]
    assert payload.get("impact_panel", {}).get("anchors")
    assert recorded, "Suggestion should be recorded when phrase is delivered"
    assert recorded[0]["person_id"] == person_id
    assert recorded[0]["suggestion"] == "How about a light walk after dinner?"
    assert payload.get("personal_model"), "Expected personal model summary in response"
    assert updated_models and updated_models[0]["person_id"] == person_id
