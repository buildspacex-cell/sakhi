import asyncio
import types

import pytest

from sakhi.apps.api.core import person_utils


@pytest.mark.asyncio
async def test_resolve_person_id_profile_match(monkeypatch):
    async def fake_q(sql, val, one=False):
        if "FROM profiles" in sql:
            return {"user_id": val}
        return None

    monkeypatch.setattr(person_utils, "q", fake_q)
    resolved = await person_utils.resolve_person_id("abc")
    assert resolved == "abc"


@pytest.mark.asyncio
async def test_resolve_person_id_map(monkeypatch):
    async def fake_q(sql, val, one=False):
        if "FROM profiles" in sql:
            return None
        if "person_profile_map" in sql:
            return {"profile_user_id": "mapped"}
        return None

    monkeypatch.setattr(person_utils, "q", fake_q)
    resolved = await person_utils.resolve_person_id("abc")
    assert resolved == "mapped"


@pytest.mark.asyncio
async def test_resolve_person_id_none(monkeypatch):
    async def fake_q(sql, val, one=False):
        return None

    monkeypatch.setattr(person_utils, "q", fake_q)
    resolved = await person_utils.resolve_person_id("abc")
    assert resolved is None
