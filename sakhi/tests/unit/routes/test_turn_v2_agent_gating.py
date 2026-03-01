import pytest

from sakhi.apps.api.routes import turn_v2


def test_agent_task_execution_disabled_by_default(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("SAKHI_ENABLE_AGENT_EXECUTION", raising=False)

    assert turn_v2._agent_task_execution_enabled() is False


def test_agent_task_execution_enabled_with_env(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("SAKHI_ENABLE_AGENT_EXECUTION", "1")

    assert turn_v2._agent_task_execution_enabled() is True


def test_agent_task_guard_blocks_autonomous_promises_when_disabled():
    guard = turn_v2._build_agent_task_guard(False)

    assert "disabled in this environment" in guard
    assert "Do not offer to start autonomous tasks" in guard
