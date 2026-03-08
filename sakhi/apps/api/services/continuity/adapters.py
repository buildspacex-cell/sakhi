from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from typing import Any

from sakhi.apps.api.core.db import exec as dbexec
from sakhi.apps.api.core.db import q as dbfetch


def canonicalize_anchor(anchor: str) -> str:
    normalized = re.sub(r"\s+", "_", (anchor or "").strip().lower())
    return normalized


def _parse_json_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            if isinstance(parsed, list):
                return parsed
        except Exception:
            return []
    return []


def _normalize_ts(value: Any) -> datetime | None:
    if not isinstance(value, datetime):
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _parse_json_object(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            return {}
    return {}


async def get_continuity_policy(person_id: str, scope: str) -> dict[str, Any]:
    row = await dbfetch(
        "SELECT enabled, exclusions FROM continuity_surface_policy WHERE person_id = $1 AND scope = $2",
        person_id,
        scope,
        one=True,
    )
    if not row:
        return {"enabled": False, "exclusions": []}
    return {
        "enabled": bool(row.get("enabled")),
        "exclusions": _parse_json_list(row.get("exclusions")),
    }


async def upsert_continuity_policy(
    person_id: str,
    *,
    scope: str,
    enabled: bool,
    exclusions: list[dict[str, Any]],
) -> dict[str, Any]:
    await dbexec(
        """
        INSERT INTO continuity_surface_policy (person_id, scope, enabled, exclusions)
        VALUES ($1, $2, $3, $4::jsonb)
        ON CONFLICT (person_id, scope)
        DO UPDATE SET enabled = EXCLUDED.enabled,
                      exclusions = EXCLUDED.exclusions,
                      updated_at = now()
        """,
        person_id,
        scope,
        enabled,
        json.dumps(exclusions, ensure_ascii=False),
    )
    return {
        "person_id": person_id,
        "scope": scope,
        "enabled": enabled,
        "exclusions": exclusions,
    }


async def upsert_continuity_label(
    person_id: str,
    *,
    source_id: str,
    source_type: str,
    anchor: str,
    facets: list[str],
    entities: list[str],
    scalar: float | None,
    metadata: dict[str, Any],
) -> dict[str, Any]:
    normalized_anchor = canonicalize_anchor(anchor)
    await dbexec(
        """
        INSERT INTO continuity_labels (
            person_id, source_type, source_id, anchor, facets, entities, scalar, metadata
        )
        VALUES ($1, $2, $3, $4, $5::jsonb, $6::jsonb, $7, $8::jsonb)
        ON CONFLICT (person_id, source_type, source_id)
        DO UPDATE SET anchor = EXCLUDED.anchor,
                      facets = EXCLUDED.facets,
                      entities = EXCLUDED.entities,
                      scalar = EXCLUDED.scalar,
                      metadata = EXCLUDED.metadata,
                      updated_at = now()
        """,
        person_id,
        source_type,
        source_id,
        normalized_anchor,
        json.dumps(facets, ensure_ascii=False),
        json.dumps(entities, ensure_ascii=False),
        scalar,
        json.dumps(metadata or {}, ensure_ascii=False),
    )
    return {
        "person_id": person_id,
        "source_type": source_type,
        "source_id": source_id,
        "anchor": normalized_anchor,
        "facets": facets,
        "entities": entities,
        "scalar": scalar,
        "metadata": metadata or {},
    }


async def load_continuity_items(
    person_id: str,
    *,
    anchor: str,
    from_ts: datetime,
    to_ts: datetime,
    exclusions: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    rows = await dbfetch(
        """
        SELECT cl.source_type,
               cl.source_id,
               cl.anchor,
               cl.facets,
               cl.entities,
               cl.scalar,
               cl.metadata,
               je.ts,
               je.person_id,
               je.user_id,
               je.content,
               je.raw_encrypted
        FROM continuity_labels cl
        JOIN journal_entries je
          ON cl.source_type = 'journal'
         AND je.id::text = cl.source_id
         AND (je.person_id = cl.person_id OR je.user_id = cl.person_id)
        WHERE cl.person_id = $1
          AND cl.anchor = $2
          AND je.ts >= $3
          AND je.ts < $4
        ORDER BY je.ts ASC
        """,
        person_id,
        canonicalize_anchor(anchor),
        from_ts,
        to_ts,
    )
    excluded_refs = {
        (str(item.get("source") or ""), str(item.get("id") or ""))
        for item in (exclusions or [])
        if item.get("source") and item.get("id")
    }

    items: list[dict[str, Any]] = []
    for row in rows:
        ref_tuple = (str(row.get("source_type") or ""), str(row.get("source_id") or ""))
        if ref_tuple in excluded_refs:
            continue
        ts = _normalize_ts(row.get("ts"))
        if ts is None:
            continue
        content = (row.get("content") or "").strip()
        items.append(
            {
                "ts": ts,
                "anchor": str(row.get("anchor") or ""),
                "facets": [str(v) for v in _parse_json_list(row.get("facets"))],
                "entities": [str(v) for v in _parse_json_list(row.get("entities"))],
                "scalar": float(row["scalar"]) if row.get("scalar") is not None else None,
                "source_type": str(row.get("source_type") or "journal"),
                "source_id": str(row.get("source_id") or ""),
                "source_ref": f"{row.get('source_type') or 'journal'}:{row.get('source_id')}",
                "content_excerpt": content[:180],
                "metadata": _parse_json_object(row.get("metadata")),
            }
        )
    return items


async def load_journal_entries_for_continuity(
    person_id: str,
    *,
    from_ts: datetime,
    to_ts: datetime,
    exclusions: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    rows = await dbfetch(
        """
        SELECT id,
               person_id,
               user_id,
               ts,
               created_at,
               updated_at,
               content,
               raw_encrypted,
               cleaned,
               title
        FROM journal_entries
        WHERE (person_id = $1 OR user_id = $1)
          AND ts >= $2
          AND ts < $3
        ORDER BY ts ASC, created_at ASC, id ASC
        """,
        person_id,
        from_ts,
        to_ts,
    )
    excluded_ids = {
        str(item.get("id") or "")
        for item in (exclusions or [])
        if str(item.get("source") or "") == "journal" and item.get("id")
    }

    items: list[dict[str, Any]] = []
    for row in rows:
        source_id = str(row.get("id") or "")
        if not source_id or source_id in excluded_ids:
            continue
        ts = _normalize_ts(row.get("ts"))
        if ts is None:
            continue
        items.append(
            {
                "id": source_id,
                "person_id": row.get("person_id"),
                "user_id": row.get("user_id"),
                "ts": ts,
                "created_at": _normalize_ts(row.get("created_at")),
                "updated_at": _normalize_ts(row.get("updated_at")),
                "content": str(row.get("content") or row.get("cleaned") or row.get("title") or "").strip(),
                "title": str(row.get("title") or "").strip(),
            }
        )
    return items
