"""
Sakhi Entity Service
--------------------
Unified entity management for people AND businesses.

Replaces the old profiles.py - now handles:
- Personal Sakhi profiles
- Business profiles
- Service provider profiles
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from enum import Enum

from pydantic import BaseModel

from sakhi.apps.api.core.db import q as dbfetch, exec as dbexec

LOGGER = logging.getLogger(__name__)


class EntityType(str, Enum):
    """Types of Sakhi entities."""
    PERSONAL = "personal"
    BUSINESS = "business"
    SERVICE = "service"


class SakhiEntity(BaseModel):
    """A Sakhi entity (person or business)."""
    id: str
    person_id: str  # Owner
    entity_type: EntityType
    display_name: str
    sakhi_handle: Optional[str] = None
    bio: Optional[str] = None

    # Business fields
    business_name: Optional[str] = None
    business_type: Optional[str] = None
    business_category: Optional[List[str]] = None
    location_name: Optional[str] = None
    operating_hours: Optional[Dict[str, Any]] = None

    # Capabilities
    capabilities: Dict[str, bool] = {
        "scheduling": True,
        "transactions": False,
        "inquiries": False,
        "bookings": False,
    }

    # Sharing preferences
    share_availability: bool = True
    availability_detail: str = "windows"
    auto_accept_from: List[str] = []
    require_confirmation: bool = True
    auto_respond_inquiries: bool = False

    # Discovery
    discoverable: bool = True
    verified: bool = False
    active: bool = True


class CreateEntityRequest(BaseModel):
    """Request to create a Sakhi entity."""
    person_id: str
    entity_type: EntityType = EntityType.PERSONAL
    display_name: str
    sakhi_handle: Optional[str] = None
    bio: Optional[str] = None

    # Business fields (optional)
    business_name: Optional[str] = None
    business_type: Optional[str] = None
    business_category: Optional[List[str]] = None
    location_name: Optional[str] = None
    operating_hours: Optional[Dict[str, Any]] = None

    # Preferences
    capabilities: Optional[Dict[str, bool]] = None
    share_availability: bool = True
    availability_detail: str = "windows"
    discoverable: bool = True


class UpdateEntityRequest(BaseModel):
    """Request to update a Sakhi entity."""
    display_name: Optional[str] = None
    sakhi_handle: Optional[str] = None
    bio: Optional[str] = None
    business_name: Optional[str] = None
    business_type: Optional[str] = None
    business_category: Optional[List[str]] = None
    location_name: Optional[str] = None
    operating_hours: Optional[Dict[str, Any]] = None
    capabilities: Optional[Dict[str, bool]] = None
    share_availability: Optional[bool] = None
    availability_detail: Optional[str] = None
    require_confirmation: Optional[bool] = None
    auto_respond_inquiries: Optional[bool] = None
    discoverable: Optional[bool] = None


def _row_to_entity(row: Dict[str, Any]) -> SakhiEntity:
    """Convert a database row to a SakhiEntity."""
    return SakhiEntity(
        id=str(row["id"]),
        person_id=row["person_id"],
        entity_type=EntityType(row["entity_type"]),
        display_name=row["display_name"],
        sakhi_handle=row.get("sakhi_handle"),
        bio=row.get("bio"),
        business_name=row.get("business_name"),
        business_type=row.get("business_type"),
        business_category=row.get("business_category"),
        location_name=row.get("location_name"),
        operating_hours=row.get("operating_hours"),
        capabilities=row.get("capabilities") or {},
        share_availability=row.get("share_availability", True),
        availability_detail=row.get("availability_detail", "windows"),
        auto_accept_from=row.get("auto_accept_from") or [],
        require_confirmation=row.get("require_confirmation", True),
        auto_respond_inquiries=row.get("auto_respond_inquiries", False),
        discoverable=row.get("discoverable", True),
        verified=row.get("verified", False),
        active=row.get("active", True),
    )


# =============================================================================
# Core CRUD
# =============================================================================

async def get_entity(entity_id: str) -> Optional[SakhiEntity]:
    """Get entity by ID."""
    row = await dbfetch(
        "SELECT * FROM sakhi_entities WHERE id = $1 AND active = TRUE",
        entity_id,
        one=True,
    )
    return _row_to_entity(row) if row else None


async def get_entity_by_person(person_id: str) -> Optional[SakhiEntity]:
    """Get entity by person_id (owner)."""
    row = await dbfetch(
        "SELECT * FROM sakhi_entities WHERE person_id = $1 AND active = TRUE",
        person_id,
        one=True,
    )
    return _row_to_entity(row) if row else None


async def create_entity(request: CreateEntityRequest) -> SakhiEntity:
    """Create a new Sakhi entity."""
    import json

    capabilities = request.capabilities or {
        "scheduling": True,
        "transactions": request.entity_type != EntityType.PERSONAL,
        "inquiries": request.entity_type != EntityType.PERSONAL,
        "bookings": request.entity_type != EntityType.PERSONAL,
    }

    row = await dbfetch(
        """
        INSERT INTO sakhi_entities (
            person_id, entity_type, display_name, sakhi_handle, bio,
            business_name, business_type, business_category, location_name, operating_hours,
            capabilities, share_availability, availability_detail, discoverable
        )
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10::jsonb, $11::jsonb, $12, $13, $14)
        RETURNING *
        """,
        request.person_id,
        request.entity_type.value,
        request.display_name,
        request.sakhi_handle,
        request.bio,
        request.business_name,
        request.business_type,
        request.business_category,
        request.location_name,
        json.dumps(request.operating_hours) if request.operating_hours else None,
        json.dumps(capabilities),
        request.share_availability,
        request.availability_detail,
        request.discoverable,
        one=True,
    )

    LOGGER.info("[entity] Created entity %s for %s", row["id"], request.person_id)
    return _row_to_entity(row)


async def update_entity(
    entity_id: str,
    request: UpdateEntityRequest,
) -> Optional[SakhiEntity]:
    """Update an existing entity."""
    import json

    # Build update fields dynamically
    updates = []
    params = [entity_id]
    param_idx = 2

    if request.display_name is not None:
        updates.append(f"display_name = ${param_idx}")
        params.append(request.display_name)
        param_idx += 1

    if request.sakhi_handle is not None:
        updates.append(f"sakhi_handle = ${param_idx}")
        params.append(request.sakhi_handle)
        param_idx += 1

    if request.bio is not None:
        updates.append(f"bio = ${param_idx}")
        params.append(request.bio)
        param_idx += 1

    if request.business_name is not None:
        updates.append(f"business_name = ${param_idx}")
        params.append(request.business_name)
        param_idx += 1

    if request.business_type is not None:
        updates.append(f"business_type = ${param_idx}")
        params.append(request.business_type)
        param_idx += 1

    if request.business_category is not None:
        updates.append(f"business_category = ${param_idx}")
        params.append(request.business_category)
        param_idx += 1

    if request.location_name is not None:
        updates.append(f"location_name = ${param_idx}")
        params.append(request.location_name)
        param_idx += 1

    if request.operating_hours is not None:
        updates.append(f"operating_hours = ${param_idx}::jsonb")
        params.append(json.dumps(request.operating_hours))
        param_idx += 1

    if request.capabilities is not None:
        updates.append(f"capabilities = ${param_idx}::jsonb")
        params.append(json.dumps(request.capabilities))
        param_idx += 1

    if request.share_availability is not None:
        updates.append(f"share_availability = ${param_idx}")
        params.append(request.share_availability)
        param_idx += 1

    if request.availability_detail is not None:
        updates.append(f"availability_detail = ${param_idx}")
        params.append(request.availability_detail)
        param_idx += 1

    if request.require_confirmation is not None:
        updates.append(f"require_confirmation = ${param_idx}")
        params.append(request.require_confirmation)
        param_idx += 1

    if request.auto_respond_inquiries is not None:
        updates.append(f"auto_respond_inquiries = ${param_idx}")
        params.append(request.auto_respond_inquiries)
        param_idx += 1

    if request.discoverable is not None:
        updates.append(f"discoverable = ${param_idx}")
        params.append(request.discoverable)
        param_idx += 1

    if not updates:
        return await get_entity(entity_id)

    query = f"""
        UPDATE sakhi_entities
        SET {', '.join(updates)}
        WHERE id = $1
        RETURNING *
    """

    row = await dbfetch(query, *params, one=True)
    return _row_to_entity(row) if row else None


# =============================================================================
# Discovery
# =============================================================================

async def find_by_handle(handle: str) -> Optional[SakhiEntity]:
    """Find entity by @handle."""
    # Normalize handle
    handle = handle.lstrip("@").lower()

    row = await dbfetch(
        """
        SELECT * FROM sakhi_entities
        WHERE LOWER(sakhi_handle) = $1
          AND active = TRUE
          AND discoverable = TRUE
        """,
        handle,
        one=True,
    )
    return _row_to_entity(row) if row else None


async def search_entities(
    query: str,
    entity_type: Optional[EntityType] = None,
    limit: int = 10,
) -> List[SakhiEntity]:
    """Search for discoverable entities."""
    base_query = """
        SELECT * FROM sakhi_entities
        WHERE active = TRUE
          AND discoverable = TRUE
          AND (
            LOWER(display_name) LIKE $1
            OR LOWER(sakhi_handle) LIKE $1
            OR LOWER(business_name) LIKE $1
          )
    """
    params = [f"%{query.lower()}%"]

    if entity_type:
        base_query += " AND entity_type = $2"
        params.append(entity_type.value)

    base_query += f" LIMIT {limit}"

    rows = await dbfetch(base_query, *params)
    return [_row_to_entity(r) for r in (rows or [])]


async def search_businesses(
    query: str,
    business_type: Optional[str] = None,
    category: Optional[str] = None,
    limit: int = 10,
) -> List[SakhiEntity]:
    """Search for business entities."""
    base_query = """
        SELECT * FROM sakhi_entities
        WHERE active = TRUE
          AND discoverable = TRUE
          AND entity_type = 'business'
          AND (
            LOWER(display_name) LIKE $1
            OR LOWER(business_name) LIKE $1
          )
    """
    params = [f"%{query.lower()}%"]
    param_idx = 2

    if business_type:
        base_query += f" AND business_type = ${param_idx}"
        params.append(business_type)
        param_idx += 1

    if category:
        base_query += f" AND $${param_idx} = ANY(business_category)"
        params.append(category)
        param_idx += 1

    base_query += f" LIMIT {limit}"

    rows = await dbfetch(base_query, *params)
    return [_row_to_entity(r) for r in (rows or [])]


# =============================================================================
# Auto-accept Management
# =============================================================================

async def add_auto_accept(entity_id: str, target_person_id: str) -> bool:
    """Add someone to auto-accept list."""
    try:
        await dbexec(
            """
            UPDATE sakhi_entities
            SET auto_accept_from = array_append(
                COALESCE(auto_accept_from, '{}'),
                $2
            )
            WHERE id = $1
              AND NOT ($2 = ANY(COALESCE(auto_accept_from, '{}')))
            """,
            entity_id,
            target_person_id,
        )
        return True
    except Exception as e:
        LOGGER.error("[entity] Failed to add auto-accept: %s", e)
        return False


async def remove_auto_accept(entity_id: str, target_person_id: str) -> bool:
    """Remove someone from auto-accept list."""
    try:
        await dbexec(
            """
            UPDATE sakhi_entities
            SET auto_accept_from = array_remove(
                COALESCE(auto_accept_from, '{}'),
                $2
            )
            WHERE id = $1
            """,
            entity_id,
            target_person_id,
        )
        return True
    except Exception as e:
        LOGGER.error("[entity] Failed to remove auto-accept: %s", e)
        return False


async def update_last_active(entity_id: str) -> bool:
    """Update last active timestamp."""
    try:
        await dbexec(
            "UPDATE sakhi_entities SET last_active_at = NOW() WHERE id = $1",
            entity_id,
        )
        return True
    except Exception:
        return False


__all__ = [
    "EntityType",
    "SakhiEntity",
    "CreateEntityRequest",
    "UpdateEntityRequest",
    "get_entity",
    "get_entity_by_person",
    "create_entity",
    "update_entity",
    "find_by_handle",
    "search_entities",
    "search_businesses",
    "add_auto_accept",
    "remove_auto_accept",
    "update_last_active",
]
