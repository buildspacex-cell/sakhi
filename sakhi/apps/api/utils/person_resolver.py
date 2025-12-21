from __future__ import annotations

from typing import Tuple

from sakhi.config.dev_persons import DEV_PERSONS


def resolve_person(request, user_key: str | None = None) -> Tuple[str, str, str]:
    """
    Resolve active dev person.
    Priority:
      1. ?user=a|b query param
      2. X-DEV-USER header
      3. default = 'a'
    """
    user_key = user_key or request.query_params.get("user")

    if user_key in DEV_PERSONS:
        p = DEV_PERSONS[user_key]
        return p["id"], p["label"], user_key

    header_key = request.headers.get("X-DEV-USER")
    if header_key in DEV_PERSONS:
        p = DEV_PERSONS[header_key]
        return p["id"], p["label"], header_key

    p = DEV_PERSONS["a"]
    return p["id"], p["label"], "a"


__all__ = ["resolve_person"]
