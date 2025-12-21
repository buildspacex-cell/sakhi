from __future__ import annotations

import logging
from typing import Any, Dict, Iterable, List

LOGGER = logging.getLogger(__name__)

_IN_MEMORY_TABLES: Dict[str, list[Dict[str, Any]]] = {}


def db_fetch(table: str, filters: Dict[str, Any]) -> Dict[str, Any]:
    """
    Development stub for fetching the first matching record.
    """
    rows = _IN_MEMORY_TABLES.get(table, [])
    for row in rows:
        if all(row.get(key) == value for key, value in filters.items()):
            return dict(row)
    return {}


def db_upsert(table: str, record: Dict[str, Any]) -> None:
    """
    Insert or update a record in the in-memory store.
    """
    rows = _IN_MEMORY_TABLES.setdefault(table, [])
    key_fields = [key for key in ("id", "person_id") if key in record]
    match_indices: Iterable[int]
    if key_fields:
        match_indices = [
            idx
            for idx, row in enumerate(rows)
            if all(row.get(field) == record.get(field) for field in key_fields)
        ]
    else:
        match_indices = []

    try:
        index = next(iter(match_indices))
    except StopIteration:
        rows.append(dict(record))
    else:
        rows[index] = dict(record)

    LOGGER.debug("db_upsert table=%s record=%s", table, record)


def db_insert(table: str, record: Dict[str, Any]) -> str:
    """
    Append a record to the in-memory table, returning its id if present.
    """
    rows = _IN_MEMORY_TABLES.setdefault(table, [])
    rows.append(dict(record))
    LOGGER.debug("db_insert table=%s record=%s", table, record)
    return str(record.get("id", len(rows)))


def db_update(table: str, filters: Dict[str, Any], updates: Dict[str, Any]) -> None:
    """
    Update rows in place that match the provided filters.
    """
    rows = _IN_MEMORY_TABLES.get(table, [])
    for row in rows:
        if all(row.get(key) == value for key, value in filters.items()):
            row.update(updates)
            LOGGER.debug("db_update table=%s filters=%s updates=%s", table, filters, updates)


def db_find(table: str, filters: Dict[str, Any] | None = None, *, limit: int | None = None, order_by: str | None = None) -> List[Dict[str, Any]]:
    """
    Return all records that match the provided filters.
    """
    rows = _IN_MEMORY_TABLES.get(table, [])
    if not filters:
        return [dict(row) for row in rows]
    filtered: List[Dict[str, Any]] = []
    for row in rows:
        if all(row.get(key) == value for key, value in filters.items()):
            filtered.append(dict(row))
    if order_by:
        filtered.sort(key=lambda item: item.get(order_by))
    if limit is not None:
        return filtered[:limit]
    return filtered


__all__ = ["db_fetch", "db_upsert", "db_insert", "db_update", "db_find"]
