import json

import pytest

from sakhi.apps.api.services.demo import simulation_profile_updater as updater


@pytest.mark.asyncio
async def test_add_journal_to_simulation_profile_appends_entry_and_snapshot(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
):
    sim_file = tmp_path / "vidhya.json"
    sim_file.write_text(
        json.dumps(
            {
                "persona_id": "vidhya",
                "user_id": "a1b2c3d4-1111-4000-8000-000000000001",
                "persona": {
                    "id": "vidhya",
                    "name": "Vidhya",
                    "dosha_baseline": {"vata": 0.25, "pitta": 0.5, "kapha": 0.25},
                    "rhythm": {"morning": "high", "afternoon": "medium", "evening": "low"},
                },
                "total_days": 2,
                "total_entries": 2,
                "entries": [
                    {
                        "day": 1,
                        "time_of_day": "morning",
                        "content": "Entry 1",
                        "timestamp": "2026-01-01T08:00:00+00:00",
                        "reply": "Reply 1",
                    },
                    {
                        "day": 2,
                        "time_of_day": "evening",
                        "content": "Entry 2",
                        "timestamp": "2026-01-02T21:00:00+00:00",
                        "reply": "Reply 2",
                    },
                ],
                "snapshots": [{"day": 1}, {"day": 2}],
                "errors": [],
            }
        ),
        encoding="utf-8",
    )

    async def fake_ensure_profile_user(*, user_id: str, persona):
        assert user_id == "a1b2c3d4-1111-4000-8000-000000000001"
        assert persona["id"] == "vidhya"

    async def fake_run_turn_for_journal(*, app, user_id: str, content: str, timestamp, day: int):
        assert user_id == "a1b2c3d4-1111-4000-8000-000000000001"
        assert content == "New appended journal"
        assert day == 3
        assert timestamp.hour == 14
        return {
            "entry_id": "entry-3",
            "reply": "Processed reply",
            "friction_state": {"state": "balanced"},
        }

    async def fake_run_daily_workers_for_user(*, user_id: str, day: int):
        assert user_id == "a1b2c3d4-1111-4000-8000-000000000001"
        assert day == 3
        return {"daily_reflection": {"ok": True}}

    async def fake_capture_snapshot(*, user_id: str, day: int, reference_time, worker_results):
        assert user_id == "a1b2c3d4-1111-4000-8000-000000000001"
        assert day == 3
        assert worker_results == {"daily_reflection": {"ok": True}}
        return {"day": day, "worker_results": worker_results}

    monkeypatch.setattr(updater, "_simulation_file", lambda _: sim_file)
    monkeypatch.setattr(updater, "_ensure_profile_user", fake_ensure_profile_user)
    monkeypatch.setattr(updater, "_run_turn_for_journal", fake_run_turn_for_journal)
    monkeypatch.setattr(updater, "_run_daily_workers_for_user", fake_run_daily_workers_for_user)
    monkeypatch.setattr(updater, "_capture_snapshot", fake_capture_snapshot)

    result = await updater.add_journal_to_simulation_profile(
        app=object(),
        persona_id="vidhya",
        content="  New appended journal  ",
        time_of_day="afternoon",
    )

    assert result["entry"]["day"] == 3
    assert result["total_entries"] == 3
    assert result["total_days"] == 3

    updated = json.loads(sim_file.read_text(encoding="utf-8"))
    assert updated["total_entries"] == 3
    assert updated["total_days"] == 3
    assert updated["entries"][-1]["day"] == 3
    assert updated["entries"][-1]["time_of_day"] == "afternoon"
    assert updated["entries"][-1]["content"] == "New appended journal"
    assert updated["entries"][-1]["reply"] == "Processed reply"
    assert updated["snapshots"][-1]["day"] == 3


@pytest.mark.asyncio
async def test_add_journal_rejects_empty_content():
    with pytest.raises(ValueError):
        await updater.add_journal_to_simulation_profile(
            app=object(),
            persona_id="vidhya",
            content="   ",
            time_of_day="evening",
        )


@pytest.mark.asyncio
async def test_add_journal_requires_existing_profile(monkeypatch: pytest.MonkeyPatch, tmp_path):
    missing = tmp_path / "missing.json"
    monkeypatch.setattr(updater, "_simulation_file", lambda _: missing)

    with pytest.raises(FileNotFoundError):
        await updater.add_journal_to_simulation_profile(
            app=object(),
            persona_id="missing",
            content="A journal",
            time_of_day="morning",
        )
