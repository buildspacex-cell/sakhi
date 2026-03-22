from __future__ import annotations

import pytest

from sakhi.apps.api.core import person_utils


@pytest.mark.asyncio
async def test_resolve_journal_owner_ids_prefers_person_profile_mapping(monkeypatch):
    async def fake_q(query: str, candidate: str, one: bool = False):
        if "FROM person_profile_map" in query:
            return {
                "person_id": "11111111-1111-4111-8111-111111111111",
                "profile_user_id": "22222222-2222-4222-8222-222222222222",
            }
        return None

    monkeypatch.setattr(person_utils, "q", fake_q)

    person_id, user_id = await person_utils.resolve_journal_owner_ids(
        "11111111-1111-4111-8111-111111111111"
    )

    assert person_id == "11111111-1111-4111-8111-111111111111"
    assert user_id == "22222222-2222-4222-8222-222222222222"


@pytest.mark.asyncio
async def test_resolve_journal_owner_ids_falls_back_to_profile_id(monkeypatch):
    async def fake_q(query: str, candidate: str, one: bool = False):
        if "FROM person_profile_map" in query:
            return None
        if "FROM profiles" in query:
            return {"user_id": candidate}
        return None

    monkeypatch.setattr(person_utils, "q", fake_q)

    person_id, user_id = await person_utils.resolve_journal_owner_ids(
        "33333333-3333-4333-8333-333333333333"
    )

    assert person_id == "33333333-3333-4333-8333-333333333333"
    assert user_id == "33333333-3333-4333-8333-333333333333"


@pytest.mark.asyncio
async def test_resolve_person_id_uses_journal_owner_resolution(monkeypatch):
    async def fake_resolve(candidate: str):
        return "person-ignored", "44444444-4444-4444-8444-444444444444"

    monkeypatch.setattr(person_utils, "resolve_journal_owner_ids", fake_resolve)

    resolved = await person_utils.resolve_person_id(
        "44444444-4444-4444-8444-444444444444"
    )

    assert resolved == "44444444-4444-4444-8444-444444444444"
