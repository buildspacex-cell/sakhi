from __future__ import annotations

import importlib

import pytest

bm25_module = importlib.import_module("sakhi.apps.api.services.memory.bm25")
last_time_module = importlib.import_module("sakhi.apps.api.services.memory.last_time")


def test_best_journal_match_prefers_stronger_keyword_signal():
    rows = [
        {"id": "recent", "content": "We discussed founder alignment and roadmap."},
        {"id": "older", "content": "Founder alignment founder alignment became explicit."},
    ]

    match = last_time_module._best_journal_match(rows, "founder alignment")

    assert match is not None
    assert match["id"] == "older"
    assert "founder alignment" in str(match.get("content", "")).lower()


@pytest.mark.asyncio
async def test_bm25_search_journals_uses_decrypted_content_fallback(monkeypatch):
    async def _fake_dbfetch(*args, **kwargs):
        return [
            {"id": "1", "user_id": "u", "content": "Founder alignment and continuity are the core."},
            {"id": "2", "user_id": "u", "content": "General update with no direct match."},
            {"id": "3", "user_id": "u", "content": "Continuity continuity continuity."},
        ]

    monkeypatch.setattr(bm25_module, "dbfetch", _fake_dbfetch)

    ranked = await bm25_module.bm25_search_journals("u", "continuity", limit=2)

    assert ranked
    assert ranked[0][0] == "3"
    assert 0.0 <= ranked[0][1] <= 1.0
