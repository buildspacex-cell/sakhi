import importlib
import os
from typing import Any, Mapping

import pytest

os.environ["ENCRYPTION_KEY"] = "unit-test-key"

from sakhi.libs.security import crypto as crypto_module
from sakhi.libs.security import idempotency as idempotency_module

crypto = importlib.reload(crypto_module)
idempotency = importlib.reload(idempotency_module)


def test_encrypt_decrypt_round_trip() -> None:
    plaintext = "secret-value"

    encrypted = crypto.encrypt_field(plaintext)
    assert encrypted != plaintext

    decrypted = crypto.decrypt_field(encrypted)
    assert decrypted == plaintext


@pytest.mark.asyncio
async def test_duplicate_idempotency_returns_cached(monkeypatch: pytest.MonkeyPatch) -> None:
    store: dict[str, dict[str, Any]] = {}

    async def fake_fetch(query: str, key: str) -> Mapping[str, Any] | None:
        return store.get(key)

    async def fake_execute(
        query: str,
        user_id: str | None,
        event_type: str,
        payload: Any,
        key: str,
        result: Any,
    ) -> str:
        store[key] = {"response": result}
        return "INSERT 0 1"

    monkeypatch.setattr(idempotency, "fetch_one", fake_fetch)
    monkeypatch.setattr(idempotency, "execute", fake_execute)

    counter = 0

    async def handler() -> dict[str, Any]:
        nonlocal counter
        counter += 1
        return {"count": counter}

    headers = {"Idempotency-Key": "abc-123"}

    first = await idempotency.run_idempotent(headers, handler)
    second = await idempotency.run_idempotent(headers, handler)

    assert first == {"count": 1}
    assert second == first
    assert counter == 1

