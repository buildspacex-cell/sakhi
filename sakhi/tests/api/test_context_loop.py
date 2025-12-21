import asyncio
from typing import Any, Dict, List, Optional

import pytest
from httpx import AsyncClient

from sakhi.apps.api.main import app
from sakhi.apps.api.deps.auth import get_current_user_id


@pytest.fixture(autouse=True)
def configure_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENCRYPTION_KEY", "tests-secret-key")
    monkeypatch.setenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/sakhi")
    monkeypatch.setenv("SAKHI_POSTGRES_DSN", "postgresql://postgres:postgres@localhost:5432/sakhi")
    monkeypatch.setenv("SAKHI_ENVIRONMENT", "test")


@pytest.fixture
def journal_auth_ctx() -> None:
    app.dependency_overrides[get_current_user_id] = lambda: "test-user"
    yield
    app.dependency_overrides.pop(get_current_user_id, None)


@pytest.fixture(autouse=True)
def mock_loop_dependencies(monkeypatch: pytest.MonkeyPatch) -> None:
    state: Dict[str, Any] = {"turns": [], "summary": "", "tasks": [
        {
            "id": "task-1",
            "title": "Find a gym near Varthur",
            "status": "todo",
        }
    ], "sessions": {}}

    async def ensure_session(user_id: str, slug: str = "journal") -> str:
        session_id = f"session-{slug}"
        state["sessions"].setdefault(session_id, {"slug": slug, "title": None})
        return session_id

    async def append_turn(user_id: str, session_id: str, role: str, text: str, tone=None, archetype=None) -> None:
        state["turns"].append({
            "role": role,
            "text": text,
            "tone": tone,
            "archetype": archetype,
            "session_id": session_id,
        })

    async def load_recent_turns(session_id: str, limit: int = 12) -> List[Dict[str, Any]]:
        turns = [t for t in state["turns"] if t.get("session_id") == session_id]
        return turns[-limit:]

    async def get_summary(session_id: str) -> str:
        return state.get("summary", "")

    async def set_summary(session_id: str, summary: str) -> None:
        state["summary"] = summary

    async def load_memories(user_id: str, kinds: List[str]) -> Dict[str, Dict[str, Any]]:
        return {}

    async def roll_summary(summary: str, recent: List[Dict[str, Any]]) -> str:
        return f"Summary turns={len(recent)}"

    async def dispatch_actions(user_id: str, actions: List[Dict[str, Any]]) -> List[str]:
        return ["Queued plan."] if actions else []

    async def talk_with_objective(user_id: str, text: str, ctx: Dict[str, Any], objective: str, clarity_hint: str | None = None) -> str:
        return "Let's explore next steps."

    async def load_graph(user_id: str):
        return state["tasks"], []

    def rank_frontier(frontier: List[Dict[str, Any]], ctx: Dict[str, Any], prefs: Dict[str, Any]):
        return frontier

    async def write_journal_entry(user_id: str, text: str, reply: str | None) -> None:
        return None

    async def topic_shift_score(text: str, summary: str, last_user: List[str]) -> Dict[str, float]:
        return {"semantic_sim": 0.9, "shift": 0.1}

    def infer_slug(_: str) -> str:
        return "journal"

    async def best_match(user_id: str, text: str):
        return None, 0.0

    async def upsert_session_vector(session_id: str, title: Optional[str], summary: Optional[str]):
        return None

    async def get_session_info(session_id: str) -> Dict[str, Any]:
        return {
            "id": session_id,
            "user_id": "test-user",
            "slug": state["sessions"].get(session_id, {}).get("slug", "journal"),
            "title": state["sessions"].get(session_id, {}).get("title"),
            "status": "active",
        }

    async def set_session_title(session_id: str, title: str) -> None:
        state["sessions"].setdefault(session_id, {"slug": "journal"})
        state["sessions"][session_id]["title"] = title

    monkeypatch.setattr("sakhi.apps.api.services.loop.run_loop.ensure_session", ensure_session)
    monkeypatch.setattr("sakhi.apps.api.services.loop.run_loop.append_turn", append_turn)
    monkeypatch.setattr("sakhi.apps.api.services.loop.run_loop.load_recent_turns", load_recent_turns)
    monkeypatch.setattr("sakhi.apps.api.services.loop.run_loop.get_summary", get_summary)
    monkeypatch.setattr("sakhi.apps.api.services.loop.run_loop.set_summary", set_summary)
    monkeypatch.setattr("sakhi.apps.api.services.loop.run_loop.load_memories", load_memories)
    monkeypatch.setattr("sakhi.apps.api.services.loop.run_loop.roll_summary", roll_summary)
    monkeypatch.setattr("sakhi.apps.api.services.loop.run_loop.dispatch_actions", dispatch_actions)
    monkeypatch.setattr("sakhi.apps.api.services.loop.run_loop.talk_with_objective", talk_with_objective)
    monkeypatch.setattr("sakhi.apps.api.services.loop.run_loop.load_graph", load_graph)
    monkeypatch.setattr("sakhi.apps.api.services.loop.run_loop.rank_frontier", rank_frontier)
    monkeypatch.setattr("sakhi.apps.api.services.loop.run_loop.write_journal_entry", write_journal_entry)
    monkeypatch.setattr("sakhi.apps.api.services.loop.run_loop.topic_shift_score", topic_shift_score)
    monkeypatch.setattr("sakhi.apps.api.services.loop.run_loop.infer_slug", infer_slug)
    monkeypatch.setattr("sakhi.apps.api.services.loop.run_loop.best_match", best_match)
    monkeypatch.setattr("sakhi.apps.api.services.loop.run_loop.upsert_session_vector", upsert_session_vector)
    monkeypatch.setattr("sakhi.apps.api.services.loop.run_loop.get_session_info", get_session_info)
    monkeypatch.setattr("sakhi.apps.api.services.loop.run_loop.set_session_title", set_session_title)


@pytest.mark.asyncio
async def test_multi_turn_context(journal_auth_ctx):
    async with AsyncClient(app=app, base_url="http://test") as ac:
        await ac.post("/journal/turn", json={"text": "I want to join a gym", "session": "journal"})
        await ac.post("/journal/turn", json={"text": "Budget 3000, evenings", "session": "journal"})
        response = await ac.post("/journal/turn", json={"text": "Near Varthur", "session": "journal"})

    assert response.status_code == 200
    data = response.json()
    assert data["dev"]["historyCount"] >= 2
    assert data["dev"]["suggestions"] or data["dev"]["confirmations"] is not None
    assert data["dev"]["topicShift"]["shiftScore"] >= 0.0
    assert data["dev"]["session"] == "journal"
