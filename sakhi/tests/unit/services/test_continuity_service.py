from unittest.mock import AsyncMock

import pytest

from sakhi.apps.api.services.continuity import adapters, service


@pytest.mark.asyncio
async def test_get_continuity_arc_requires_opt_in(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(service, "get_continuity_policy", AsyncMock(return_value={"enabled": False, "exclusions": []}))

    with pytest.raises(PermissionError):
        await service.get_continuity_arc("person-1", "career")


@pytest.mark.asyncio
async def test_get_continuity_topics_returns_compiled_summaries(monkeypatch: pytest.MonkeyPatch):
    compiled = {
        "taxonomy_version": "2026.03.03",
        "compiler_version": "2026.03.03.1",
        "threshold_profile_version": "2026.03.03.1",
        "compiled_at": "2026-03-04T10:00:00+00:00",
        "inputs_hash": "abc123",
        "topics": [
            {
                "anchor": "career",
                "label": "Career",
                "confidence": 0.81,
                "selected_count": 4,
                "surface": {"mirror_allowed": True, "detail_allowed": True},
                "arc": {
                    "span_days": 45.0,
                    "start_ts": "2026-01-01T10:00:00+00:00",
                    "end_ts": "2026-02-15T10:00:00+00:00",
                    "features": {"direction": "flat"},
                },
                "entry_tags": {"1|2026-01-01T10:00:00+00:00": {"trace": {"anchor": {}}}},
            }
        ],
    }

    monkeypatch.setattr(
        service,
        "_compile_window_continuity",
        AsyncMock(
            return_value=(
                compiled,
                {"enabled": True, "exclusions": []},
                service.datetime(2025, 12, 4, tzinfo=service.UTC),
                service.datetime(2026, 3, 4, tzinfo=service.UTC),
            )
        ),
    )

    payload = await service.get_continuity_topics("person-1", window="90d")

    assert payload["person_id"] == "person-1"
    assert payload["versions"]["inputs_hash"] == "abc123"
    assert payload["topics"][0]["anchor"] == "career"
    assert payload["topics"][0]["direction"] == "flat"


@pytest.mark.asyncio
async def test_get_continuity_arc_builds_rich_response_and_logs(monkeypatch: pytest.MonkeyPatch):
    compiled = {
        "taxonomy_version": "2026.03.03",
        "compiler_version": "2026.03.03.1",
        "threshold_profile_version": "2026.03.03.1",
        "compiled_at": "2026-03-04T10:00:00+00:00",
        "inputs_hash": "abc123",
        "topics": [],
    }
    selected_topic = {
        "anchor": "career",
        "label": "Career",
        "confidence": 0.84,
        "selected_count": 3,
        "surface": {"mirror_allowed": True, "detail_allowed": True},
        "arc": {
            "features": {"direction": "rising"},
            "event_refs": [
                {
                    "day": 1,
                    "ts": "2026-01-01T10:00:00+00:00",
                    "source_type": "journal",
                    "source_id": "a",
                    "source_ref": "journal:a",
                    "excerpt": "Thinking about growth",
                    "facet": "promotion",
                    "facet_state": "CONFIDENT",
                    "decision_state": "questioning",
                    "stance": "toward",
                },
                {
                    "day": 10,
                    "ts": "2026-01-10T10:00:00+00:00",
                    "source_type": "journal",
                    "source_id": "b",
                    "source_ref": "journal:b",
                    "excerpt": "Tension with the current role",
                    "facet": "promotion",
                    "facet_state": "CONFIDENT",
                    "decision_state": "leaning_yes",
                    "stance": "toward",
                },
            ],
        },
        "entry_tags": {
            "1|2026-01-01T10:00:00+00:00": {
                "confidence": 0.7,
                "facet": "promotion",
                "facet_state": "CONFIDENT",
                "decision_state": "questioning",
                "stance": "toward",
                "trace": {"anchor": {}},
            },
            "10|2026-01-10T10:00:00+00:00": {
                "confidence": 0.9,
                "facet": "promotion",
                "facet_state": "CONFIDENT",
                "decision_state": "leaning_yes",
                "stance": "toward",
                "trace": {"anchor": {}},
            },
        },
    }

    monkeypatch.setattr(
        service,
        "_compile_window_continuity",
        AsyncMock(
            return_value=(
                compiled,
                {"enabled": True, "exclusions": []},
                service.datetime(2025, 12, 1, tzinfo=service.UTC),
                service.datetime(2026, 3, 1, tzinfo=service.UTC),
            )
        ),
    )
    monkeypatch.setattr(service, "select_compiled_topic", lambda compiled, anchor, debug=False: selected_topic)
    mock_log = AsyncMock()
    monkeypatch.setattr(service, "log_turn_event", mock_log)

    payload = await service.get_continuity_arc("person-1", "Career", window="90d", max_gap_days=21, min_len=2)

    assert payload["anchor"] == "career"
    assert payload["label"] == "Career"
    assert payload["topic_confidence"] == 0.84
    assert payload["arc"]["features"]["direction"] == "rising"
    assert len(payload["included_moments"]) == 2
    assert payload["included_moments"][0]["source_ref"] == "journal:a"
    assert payload["versions"]["inputs_hash"] == "abc123"
    mock_log.assert_awaited_once()


@pytest.mark.asyncio
async def test_load_continuity_items_applies_exclusions(monkeypatch: pytest.MonkeyPatch):
    seen_sql: list[str] = []

    async def fake_dbfetch(sql: str, *args, one: bool = False):
        seen_sql.append(sql)
        return [
            {
                "source_type": "journal",
                "source_id": "keep",
                "anchor": "career",
                "facets": ["autonomy"],
                "entities": [],
                "scalar": None,
                "metadata": {},
                "ts": service.datetime(2026, 1, 1, tzinfo=service.UTC),
                "content": "Keep me",
            },
            {
                "source_type": "journal",
                "source_id": "hide",
                "anchor": "career",
                "facets": ["autonomy"],
                "entities": [],
                "scalar": None,
                "metadata": {},
                "ts": service.datetime(2026, 1, 2, tzinfo=service.UTC),
                "content": "Hide me",
            },
        ]

    monkeypatch.setattr(adapters, "dbfetch", fake_dbfetch)

    items = await adapters.load_continuity_items(
        "person-1",
        anchor="career",
        from_ts=service.datetime(2025, 12, 1, tzinfo=service.UTC),
        to_ts=service.datetime(2026, 3, 1, tzinfo=service.UTC),
        exclusions=[{"source": "journal", "id": "hide"}],
    )

    assert len(items) == 1
    assert items[0]["source_id"] == "keep"
    assert "je.person_id = cl.person_id OR je.user_id = cl.person_id" in seen_sql[0]


@pytest.mark.asyncio
async def test_load_journal_entries_for_continuity_applies_exclusions(monkeypatch: pytest.MonkeyPatch):
    async def fake_dbfetch(sql: str, *args, one: bool = False):
        return [
            {
                "id": "keep",
                "person_id": "person-1",
                "user_id": "person-1",
                "ts": service.datetime(2026, 1, 1, tzinfo=service.UTC),
                "created_at": service.datetime(2026, 1, 1, tzinfo=service.UTC),
                "updated_at": service.datetime(2026, 1, 1, tzinfo=service.UTC),
                "content": "Keep me",
                "cleaned": "",
                "title": "",
            },
            {
                "id": "hide",
                "person_id": "person-1",
                "user_id": "person-1",
                "ts": service.datetime(2026, 1, 2, tzinfo=service.UTC),
                "created_at": service.datetime(2026, 1, 2, tzinfo=service.UTC),
                "updated_at": service.datetime(2026, 1, 2, tzinfo=service.UTC),
                "content": "Hide me",
                "cleaned": "",
                "title": "",
            },
        ]

    monkeypatch.setattr(adapters, "dbfetch", fake_dbfetch)

    items = await adapters.load_journal_entries_for_continuity(
        "person-1",
        from_ts=service.datetime(2025, 12, 1, tzinfo=service.UTC),
        to_ts=service.datetime(2026, 3, 1, tzinfo=service.UTC),
        exclusions=[{"source": "journal", "id": "hide"}],
    )

    assert [item["id"] for item in items] == ["keep"]
