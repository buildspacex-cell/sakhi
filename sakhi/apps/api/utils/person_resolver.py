from __future__ import annotations

import re
from typing import Tuple

from sakhi.config.dev_persons import DEV_PERSONS

# UUID pattern (8-4-4-4-12 hex digits)
UUID_PATTERN = re.compile(r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$')


def resolve_person(request, user_key: str | None = None) -> Tuple[str, str, str]:
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
    user_key = user_key or request.query_params.get("user")

    # If user_key is a valid UUID, use it directly (authenticated user)
    if user_key and UUID_PATTERN.match(user_key):
        return user_key, "User", user_key[:8]

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
