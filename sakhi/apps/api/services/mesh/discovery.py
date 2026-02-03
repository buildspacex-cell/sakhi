"""
A.6 Sakhi Discovery
-------------------
Enhanced Sakhi discovery with handle lookup, caching, and batch operations.

Enables finding another Sakhi by:
- sakhi_id (direct lookup)
- person_id (owner lookup)
- @handle (social-style lookup)
- Full-text search (discoverable entities)
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union
from functools import lru_cache

from pydantic import BaseModel

from sakhi.apps.api.core.db import q as dbfetch, exec as dbexec
from sakhi.apps.api.services.mesh.inter_sakhi import (
    SakhiEndpoint,
    lookup_sakhi_endpoint,
    lookup_sakhi_by_person,
)
from sakhi.apps.api.services.mesh.entities import (
    SakhiEntity,
    EntityType,
    get_entity,
    get_entity_by_person,
)

LOGGER = logging.getLogger(__name__)


# =============================================================================
# Models
# =============================================================================

class DiscoveryResult(BaseModel):
    """Result of a Sakhi discovery lookup."""
    found: bool
    sakhi_id: Optional[str] = None
    person_id: Optional[str] = None
    endpoint_url: Optional[str] = None
    display_name: Optional[str] = None
    handle: Optional[str] = None
    entity_type: Optional[str] = None
    is_online: bool = False
    public_key: Optional[str] = None
    capabilities: Dict[str, bool] = {}
    lookup_method: str = "unknown"  # sakhi_id, person_id, handle, search


class DiscoveryIndex(BaseModel):
    """A discoverable Sakhi in the index."""
    sakhi_id: str
    person_id: str
    handle: Optional[str]
    display_name: str
    entity_type: str
    endpoint_url: Optional[str]
    is_online: bool
    verified: bool
    last_seen: Optional[datetime]


# =============================================================================
# Core Discovery Functions
# =============================================================================

async def discover_sakhi(identifier: str) -> Optional[DiscoveryResult]:
    """
    Discover a Sakhi by any identifier (sakhi_id, person_id, or @handle).

    Args:
        identifier: Can be:
            - sakhi_id (UUID-like string)
            - person_id (UUID)
            - @handle (starts with @)
            - handle (without @)

    Returns:
        DiscoveryResult with endpoint info or None if not found
    """
    # Normalize handle
    if identifier.startswith("@"):
        identifier = identifier[1:]

    # Try by handle first (most common use case)
    result = await _lookup_by_handle(identifier)
    if result:
        return result

    # Try by sakhi_id
    result = await _lookup_by_sakhi_id(identifier)
    if result:
        return result

    # Try by person_id
    result = await _lookup_by_person_id(identifier)
    if result:
        return result

    LOGGER.debug("[discovery] No Sakhi found for identifier: %s", identifier)
    return None


async def _lookup_by_handle(handle: str) -> Optional[DiscoveryResult]:
    """Look up Sakhi by handle."""
    # Check sakhi_entities for handle
    row = await dbfetch(
        """
        SELECT e.id, e.person_id, e.sakhi_handle, e.display_name, e.entity_type,
               e.capabilities, e.verified,
               ep.sakhi_id, ep.endpoint_url, ep.public_key, ep.last_seen
        FROM sakhi_entities e
        LEFT JOIN mesh_endpoints ep ON ep.person_id = e.person_id
        WHERE LOWER(e.sakhi_handle) = LOWER($1)
          AND e.active = TRUE
          AND e.discoverable = TRUE
        """,
        handle,
        one=True,
    )

    if not row:
        return None

    is_online = _check_online(row.get("last_seen"))

    return DiscoveryResult(
        found=True,
        sakhi_id=row.get("sakhi_id"),
        person_id=row["person_id"],
        endpoint_url=row.get("endpoint_url"),
        display_name=row["display_name"],
        handle=row.get("sakhi_handle"),
        entity_type=row["entity_type"],
        is_online=is_online,
        public_key=row.get("public_key"),
        capabilities=row.get("capabilities") or {},
        lookup_method="handle",
    )


async def _lookup_by_sakhi_id(sakhi_id: str) -> Optional[DiscoveryResult]:
    """Look up by direct sakhi_id."""
    endpoint = await lookup_sakhi_endpoint(sakhi_id)
    if not endpoint:
        return None

    # Get entity info too
    entity = await get_entity_by_person(endpoint.person_id)

    return DiscoveryResult(
        found=True,
        sakhi_id=endpoint.sakhi_id,
        person_id=endpoint.person_id,
        endpoint_url=endpoint.endpoint_url,
        display_name=endpoint.display_name or (entity.display_name if entity else None),
        handle=entity.sakhi_handle if entity else None,
        entity_type=entity.entity_type.value if entity else "personal",
        is_online=endpoint.is_online,
        public_key=endpoint.public_key,
        capabilities=entity.capabilities if entity else {},
        lookup_method="sakhi_id",
    )


async def _lookup_by_person_id(person_id: str) -> Optional[DiscoveryResult]:
    """Look up by person_id (owner)."""
    endpoint = await lookup_sakhi_by_person(person_id)
    entity = await get_entity_by_person(person_id)

    if not endpoint and not entity:
        return None

    return DiscoveryResult(
        found=True,
        sakhi_id=endpoint.sakhi_id if endpoint else None,
        person_id=person_id,
        endpoint_url=endpoint.endpoint_url if endpoint else None,
        display_name=(endpoint.display_name if endpoint else None) or (entity.display_name if entity else None),
        handle=entity.sakhi_handle if entity else None,
        entity_type=entity.entity_type.value if entity else "personal",
        is_online=endpoint.is_online if endpoint else False,
        public_key=endpoint.public_key if endpoint else None,
        capabilities=entity.capabilities if entity else {},
        lookup_method="person_id",
    )


def _check_online(last_seen: Optional[datetime]) -> bool:
    """Check if a Sakhi is online based on last_seen."""
    if not last_seen:
        return False
    if isinstance(last_seen, str):
        last_seen = datetime.fromisoformat(last_seen.replace("Z", "+00:00"))
    # Handle timezone-aware comparison
    now = datetime.utcnow()
    if last_seen.tzinfo is not None:
        from datetime import timezone
        now = now.replace(tzinfo=timezone.utc)
    return (now - last_seen) < timedelta(minutes=5)


# =============================================================================
# Batch Discovery
# =============================================================================

async def discover_sakhis_batch(
    identifiers: List[str],
) -> Dict[str, DiscoveryResult]:
    """
    Batch lookup for multiple Sakhis.

    Args:
        identifiers: List of sakhi_ids, person_ids, or @handles

    Returns:
        Dict mapping identifier -> DiscoveryResult (only found entries)
    """
    results = {}

    # Separate by type for efficient querying
    handles = []
    ids = []

    for identifier in identifiers:
        if identifier.startswith("@"):
            handles.append(identifier[1:])
        else:
            ids.append(identifier)

    # Batch lookup handles
    if handles:
        rows = await dbfetch(
            """
            SELECT e.id, e.person_id, e.sakhi_handle, e.display_name, e.entity_type,
                   e.capabilities, e.verified,
                   ep.sakhi_id, ep.endpoint_url, ep.public_key, ep.last_seen
            FROM sakhi_entities e
            LEFT JOIN mesh_endpoints ep ON ep.person_id = e.person_id
            WHERE LOWER(e.sakhi_handle) = ANY($1)
              AND e.active = TRUE
              AND e.discoverable = TRUE
            """,
            [h.lower() for h in handles],
        )

        for row in rows or []:
            handle = row.get("sakhi_handle")
            is_online = _check_online(row.get("last_seen"))

            results[f"@{handle}"] = DiscoveryResult(
                found=True,
                sakhi_id=row.get("sakhi_id"),
                person_id=row["person_id"],
                endpoint_url=row.get("endpoint_url"),
                display_name=row["display_name"],
                handle=handle,
                entity_type=row["entity_type"],
                is_online=is_online,
                public_key=row.get("public_key"),
                capabilities=row.get("capabilities") or {},
                lookup_method="handle",
            )

    # Batch lookup IDs (could be sakhi_id or person_id)
    if ids:
        rows = await dbfetch(
            """
            SELECT ep.sakhi_id, ep.person_id, ep.endpoint_url, ep.display_name,
                   ep.public_key, ep.last_seen,
                   e.sakhi_handle, e.entity_type, e.capabilities
            FROM mesh_endpoints ep
            LEFT JOIN sakhi_entities e ON e.person_id = ep.person_id
            WHERE ep.sakhi_id = ANY($1) OR ep.person_id::text = ANY($1)
            """,
            ids,
        )

        for row in rows or []:
            is_online = _check_online(row.get("last_seen"))

            result = DiscoveryResult(
                found=True,
                sakhi_id=row["sakhi_id"],
                person_id=row["person_id"],
                endpoint_url=row["endpoint_url"],
                display_name=row.get("display_name"),
                handle=row.get("sakhi_handle"),
                entity_type=row.get("entity_type", "personal"),
                is_online=is_online,
                public_key=row.get("public_key"),
                capabilities=row.get("capabilities") or {},
                lookup_method="batch",
            )

            # Add to results by both IDs if present
            results[row["sakhi_id"]] = result
            results[row["person_id"]] = result

    return results


# =============================================================================
# Discovery Index Operations
# =============================================================================

async def register_for_discovery(
    person_id: str,
    handle: str,
    display_name: str,
    entity_type: EntityType = EntityType.PERSONAL,
) -> bool:
    """
    Register a Sakhi for discovery (create or update entity).

    Args:
        person_id: Owner's person ID
        handle: Unique @handle (will be lowercased)
        display_name: Display name
        entity_type: Type of entity

    Returns:
        True if registered successfully
    """
    try:
        # Check if handle is taken
        existing = await dbfetch(
            """
            SELECT id FROM sakhi_entities
            WHERE LOWER(sakhi_handle) = LOWER($1) AND person_id != $2
            """,
            handle.lower(),
            person_id,
            one=True,
        )

        if existing:
            LOGGER.warning("[discovery] Handle @%s already taken", handle)
            return False

        # Upsert entity
        await dbexec(
            """
            INSERT INTO sakhi_entities (person_id, sakhi_handle, display_name, entity_type, discoverable)
            VALUES ($1, $2, $3, $4, TRUE)
            ON CONFLICT (person_id) DO UPDATE
            SET sakhi_handle = COALESCE($2, sakhi_entities.sakhi_handle),
                display_name = COALESCE($3, sakhi_entities.display_name),
                discoverable = TRUE
            """,
            person_id,
            handle.lower(),
            display_name,
            entity_type.value,
        )

        LOGGER.info("[discovery] Registered @%s for %s", handle, person_id[:8])
        return True

    except Exception as e:
        LOGGER.exception("[discovery] Failed to register: %s", e)
        return False


async def unregister_from_discovery(person_id: str) -> bool:
    """Remove a Sakhi from discovery index."""
    try:
        await dbexec(
            "UPDATE sakhi_entities SET discoverable = FALSE WHERE person_id = $1",
            person_id,
        )
        return True
    except Exception as e:
        LOGGER.exception("[discovery] Failed to unregister: %s", e)
        return False


# =============================================================================
# Search
# =============================================================================

async def search_discoverable(
    query: str,
    entity_type: Optional[EntityType] = None,
    limit: int = 20,
) -> List[DiscoveryIndex]:
    """
    Search for discoverable Sakhis by name or handle.

    Args:
        query: Search text
        entity_type: Optional filter by type
        limit: Max results

    Returns:
        List of discoverable Sakhis
    """
    type_filter = ""
    params: List[Any] = [f"%{query}%", limit]

    if entity_type:
        type_filter = "AND e.entity_type = $3"
        params.append(entity_type.value)

    rows = await dbfetch(
        f"""
        SELECT e.id, e.person_id, e.sakhi_handle, e.display_name,
               e.entity_type, e.verified,
               ep.sakhi_id, ep.endpoint_url, ep.last_seen
        FROM sakhi_entities e
        LEFT JOIN mesh_endpoints ep ON ep.person_id = e.person_id
        WHERE e.active = TRUE
          AND e.discoverable = TRUE
          AND (
            e.display_name ILIKE $1
            OR e.sakhi_handle ILIKE $1
            OR e.bio ILIKE $1
          )
          {type_filter}
        ORDER BY e.verified DESC, e.display_name
        LIMIT $2
        """,
        *params,
    )

    results = []
    for row in rows or []:
        results.append(DiscoveryIndex(
            sakhi_id=row.get("sakhi_id") or str(row["id"]),
            person_id=row["person_id"],
            handle=row.get("sakhi_handle"),
            display_name=row["display_name"],
            entity_type=row["entity_type"],
            endpoint_url=row.get("endpoint_url"),
            is_online=_check_online(row.get("last_seen")),
            verified=row.get("verified", False),
            last_seen=row.get("last_seen"),
        ))

    return results


async def search_businesses(
    query: Optional[str] = None,
    business_type: Optional[str] = None,
    category: Optional[str] = None,
    location: Optional[str] = None,
    limit: int = 20,
) -> List[DiscoveryIndex]:
    """
    Search for business Sakhis.

    Args:
        query: Optional text search
        business_type: Filter by type (restaurant, retail, service)
        category: Filter by category
        location: Filter by location
        limit: Max results

    Returns:
        List of business Sakhis
    """
    conditions = ["e.entity_type = 'business'", "e.active = TRUE", "e.discoverable = TRUE"]
    params: List[Any] = []
    param_count = 0

    if query:
        param_count += 1
        conditions.append(f"(e.display_name ILIKE ${param_count} OR e.business_name ILIKE ${param_count})")
        params.append(f"%{query}%")

    if business_type:
        param_count += 1
        conditions.append(f"e.business_type = ${param_count}")
        params.append(business_type)

    if category:
        param_count += 1
        conditions.append(f"${param_count} = ANY(e.business_category)")
        params.append(category)

    if location:
        param_count += 1
        conditions.append(f"e.location_name ILIKE ${param_count}")
        params.append(f"%{location}%")

    param_count += 1
    params.append(limit)

    where_clause = " AND ".join(conditions)

    rows = await dbfetch(
        f"""
        SELECT e.id, e.person_id, e.sakhi_handle, e.display_name,
               e.entity_type, e.verified, e.business_name, e.business_type,
               ep.sakhi_id, ep.endpoint_url, ep.last_seen
        FROM sakhi_entities e
        LEFT JOIN mesh_endpoints ep ON ep.person_id = e.person_id
        WHERE {where_clause}
        ORDER BY e.verified DESC, e.display_name
        LIMIT ${param_count}
        """,
        *params,
    )

    results = []
    for row in rows or []:
        results.append(DiscoveryIndex(
            sakhi_id=row.get("sakhi_id") or str(row["id"]),
            person_id=row["person_id"],
            handle=row.get("sakhi_handle"),
            display_name=row.get("business_name") or row["display_name"],
            entity_type=row["entity_type"],
            endpoint_url=row.get("endpoint_url"),
            is_online=_check_online(row.get("last_seen")),
            verified=row.get("verified", False),
            last_seen=row.get("last_seen"),
        ))

    return results


# =============================================================================
# Statistics
# =============================================================================

async def get_discovery_stats() -> Dict[str, Any]:
    """Get stats about the discovery network."""
    row = await dbfetch(
        """
        SELECT
            COUNT(*) FILTER (WHERE entity_type = 'personal') as personal_count,
            COUNT(*) FILTER (WHERE entity_type = 'business') as business_count,
            COUNT(*) FILTER (WHERE verified = TRUE) as verified_count,
            COUNT(*) as total_count
        FROM sakhi_entities
        WHERE active = TRUE AND discoverable = TRUE
        """,
        one=True,
    )

    online_count = await dbfetch(
        """
        SELECT COUNT(*) as cnt FROM mesh_endpoints
        WHERE last_seen > NOW() - INTERVAL '5 minutes'
        """,
        one=True,
    )

    return {
        "total_discoverable": row["total_count"] if row else 0,
        "personal": row["personal_count"] if row else 0,
        "business": row["business_count"] if row else 0,
        "verified": row["verified_count"] if row else 0,
        "online_now": online_count["cnt"] if online_count else 0,
    }


__all__ = [
    "DiscoveryResult",
    "DiscoveryIndex",
    "discover_sakhi",
    "discover_sakhis_batch",
    "register_for_discovery",
    "unregister_from_discovery",
    "search_discoverable",
    "search_businesses",
    "get_discovery_stats",
]
