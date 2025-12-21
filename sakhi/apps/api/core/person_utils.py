from __future__ import annotations

from typing import Optional
from uuid import UUID

from sakhi.apps.api.core.db import q


def _is_uuid(value: str) -> bool:
    try:
        UUID(str(value))
        return True
    except Exception:
        return False


async def resolve_person_id(candidate: str) -> Optional[str]:
    """
    Resolve a provided identifier to a profiles.user_id.
    Falls back to person_profile_map if necessary.
    """
    if not candidate or not _is_uuid(candidate):
        return None
    # Direct profile match
    row = await q("SELECT user_id FROM profiles WHERE user_id = $1", candidate, one=True)
    if row and row.get("user_id"):
        return row["user_id"]

    # Map via person_profile_map
    mapping = await q(
        """
        SELECT profile_user_id FROM person_profile_map
        WHERE person_id = $1 OR profile_user_id = $1
        """,
        candidate,
        one=True,
    )
    if mapping and mapping.get("profile_user_id"):
        return mapping["profile_user_id"]
    return None


__all__ = ["resolve_person_id"]
