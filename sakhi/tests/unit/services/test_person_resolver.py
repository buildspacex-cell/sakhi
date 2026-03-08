from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from sakhi.apps.api.utils import person_resolver


def _make_request(*, query_user: str | None = None):
    query_params = {}
    if query_user is not None:
        query_params["user"] = query_user
    return SimpleNamespace(
        query_params=query_params,
        headers={},
        state=SimpleNamespace(),
    )


@pytest.mark.asyncio
async def test_resolve_person_non_enforced_accepts_uuid(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(person_resolver, "_should_enforce_user_binding", lambda: False)
    request = _make_request(query_user="11111111-1111-4111-8111-111111111111")

    person_id, _, _ = await person_resolver.resolve_person(request)

    assert person_id == "11111111-1111-4111-8111-111111111111"


@pytest.mark.asyncio
async def test_resolve_person_enforced_requires_authenticated_person(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(person_resolver, "_should_enforce_user_binding", lambda: True)

    async def _no_auth(_request):
        return None

    monkeypatch.setattr(person_resolver, "_resolve_authenticated_person_id", _no_auth)
    request = _make_request(query_user="11111111-1111-4111-8111-111111111111")

    with pytest.raises(HTTPException) as exc_info:
        await person_resolver.resolve_person(request)

    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_resolve_person_enforced_rejects_user_mismatch(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(person_resolver, "_should_enforce_user_binding", lambda: True)

    async def _auth_person(_request):
        return "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"

    monkeypatch.setattr(person_resolver, "_resolve_authenticated_person_id", _auth_person)
    request = _make_request(query_user="bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb")

    with pytest.raises(HTTPException) as exc_info:
        await person_resolver.resolve_person(request)

    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_resolve_person_enforced_uses_authenticated_person(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(person_resolver, "_should_enforce_user_binding", lambda: True)

    async def _auth_person(_request):
        return "cccccccc-cccc-4ccc-8ccc-cccccccccccc"

    monkeypatch.setattr(person_resolver, "_resolve_authenticated_person_id", _auth_person)
    request = _make_request(query_user="cccccccc-cccc-4ccc-8ccc-cccccccccccc")

    person_id, label, key = await person_resolver.resolve_person(request)

    assert person_id == "cccccccc-cccc-4ccc-8ccc-cccccccccccc"
    assert label == "User"
    assert key == "cccccccc"

