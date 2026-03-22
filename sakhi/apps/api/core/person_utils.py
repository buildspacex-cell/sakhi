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


async def resolve_journal_owner_ids(candidate: str) -> tuple[Optional[str], Optional[str]]:
    """
    Resolve a journal writer into canonical (person_id, user_id) columns.

    Legacy rows often wrote only ``user_id`` while newer continuity/debug
    surfaces read either ``person_id`` or ``user_id``. Journal writes should
    populate both columns consistently so downstream loaders do not depend on
    fallback OR conditions forever.
    """
    if not candidate or not _is_uuid(candidate):
        return None, None

    mapping = await q(
        """
        SELECT person_id, profile_user_id
        FROM person_profile_map
        WHERE person_id = $1 OR profile_user_id = $1
        LIMIT 1
        """,
        candidate,
        one=True,
    )
    if mapping:
        person_id = str(mapping.get("person_id") or candidate)
        user_id = str(mapping.get("profile_user_id") or person_id)
        return person_id, user_id

    row = await q("SELECT user_id FROM profiles WHERE user_id = $1", candidate, one=True)
    if row and row.get("user_id"):
        resolved = str(row["user_id"])
        return resolved, resolved

    return None, None


async def resolve_person_id(candidate: str) -> Optional[str]:
    """
    Resolve a provided identifier to a profiles.user_id.
    Falls back to person_profile_map if necessary.
    """
    _, user_id = await resolve_journal_owner_ids(candidate)
    return user_id


__all__ = ["resolve_person_id", "resolve_journal_owner_ids"]
