from __future__ import annotations

import os
import re

from fastapi import HTTPException, status

from sakhi.config.dev_persons import DEV_PERSONS

# UUID pattern (8-4-4-4-12 hex digits)
UUID_PATTERN = re.compile(r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$')
TRUTHY_VALUES = {"1", "true", "yes", "y", "on"}


def _is_prod_runtime() -> bool:
    node_env = str(os.getenv("NODE_ENV", "")).strip().lower()
    app_env = str(os.getenv("ENV", "")).strip().lower()
    vercel_env = str(os.getenv("VERCEL_ENV", "")).strip().lower()
    return node_env == "production" or app_env == "production" or vercel_env == "production"


def _as_bool(value: str | None) -> bool:
    return bool(value and value.strip().lower() in TRUTHY_VALUES)


def _should_enforce_user_binding() -> bool:
    explicit = os.getenv("SAKHI_ENFORCE_USER_BINDING")
    if explicit is not None:
        return _as_bool(explicit)
    return _is_prod_runtime()


async def _resolve_authenticated_person_id(request) -> str | None:
    cached = getattr(request.state, "authenticated_person_id", None)
    if cached:
        return str(cached)

    state_user_id = getattr(request.state, "user_id", None)
    if state_user_id:
        resolved = str(state_user_id)
        request.state.authenticated_person_id = resolved
        return resolved

    authorization = request.headers.get("Authorization") or request.headers.get("authorization")
    if not authorization:
        return None

    # Lazy imports keep local/dev modules import-safe when auth env vars are absent.
    from sakhi.apps.api.core.db import q
    from sakhi.apps.api.deps.auth import get_current_user_id

    supabase_user_id = await get_current_user_id(authorization)
    row = await q(
        """
        SELECT id
        FROM auth_users
        WHERE supabase_user_id = $1 OR id = $1
        LIMIT 1
        """,
        str(supabase_user_id),
        one=True,
    )
    resolved = str((row or {}).get("id") or supabase_user_id)
    request.state.authenticated_person_id = resolved
    return resolved


async def resolve_person(request, user_key: str | None = None) -> tuple[str, str, str]:
    """
    Resolve person ID from request.

    Priority:
      1. ?user=<uuid> query param (actual authenticated user)
      2. ?user=a|b query param (dev shortcuts)
      3. X-DEV-USER header (dev shortcuts)
      4. default = 'a' (fallback for dev)

    If user_key is a valid UUID, use it directly (authenticated user flow).
    If user_key is a dev shortcut (a, b, etc.), look up in DEV_PERSONS.
    """
    query_user = request.query_params.get("user")
    user_key = user_key or query_user

    if _should_enforce_user_binding():
        authenticated_person_id = await _resolve_authenticated_person_id(request)
        if not authenticated_person_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Unauthenticated",
            )
        if user_key and UUID_PATTERN.match(str(user_key)) and str(user_key) != authenticated_person_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Forbidden: user mismatch",
            )
        return authenticated_person_id, "User", authenticated_person_id[:8]

    # If user_key is a valid UUID, use it directly.
    if user_key and UUID_PATTERN.match(str(user_key)):
        key_str = str(user_key)
        return key_str, "User", key_str[:8]

    # Check dev person shortcuts
    if user_key in DEV_PERSONS:
        p = DEV_PERSONS[user_key]
        return p["id"], p["label"], user_key

    header_key = request.headers.get("X-DEV-USER")
    if header_key in DEV_PERSONS:
        p = DEV_PERSONS[header_key]
        return p["id"], p["label"], header_key

    # Default to first dev person (for backwards compatibility)
    p = DEV_PERSONS["a"]
    return p["id"], p["label"], "a"


__all__ = ["resolve_person"]
