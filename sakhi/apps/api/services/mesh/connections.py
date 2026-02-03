"""
Sakhi Connection Service
------------------------
Manages connections between Sakhi entities.

Supports different connection types:
- peer: Equal relationship (friends)
- customer: from is customer of to
- vendor: from sells to to
- follower: one-way follow
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from datetime import datetime
from enum import Enum

from pydantic import BaseModel

from sakhi.apps.api.core.db import q as dbfetch, exec as dbexec
from sakhi.apps.api.services.mesh.entities import get_entity_by_person

LOGGER = logging.getLogger(__name__)


class TrustLevel(str, Enum):
    """Trust levels for connections."""
    MINIMAL = "minimal"      # Basic info only
    STANDARD = "standard"    # Normal interactions
    TRUSTED = "trusted"      # Can auto-schedule, see more
    VIP = "vip"              # Priority access

    # Backward compatibility aliases
    ACQUAINTANCE = "minimal"
    FRIEND = "standard"
    CLOSE_FRIEND = "trusted"


class ConnectionStatus(str, Enum):
    """Status of a connection."""
    PENDING = "pending"
    CONNECTED = "connected"
    BLOCKED = "blocked"
    MUTED = "muted"


class ConnectionType(str, Enum):
    """Type of connection relationship."""
    PEER = "peer"          # Equal (friends)
    CUSTOMER = "customer"  # Buyer-seller
    VENDOR = "vendor"      # Seller-buyer
    FOLLOWER = "follower"  # One-way


class SakhiConnection(BaseModel):
    """A connection between two Sakhi entities."""
    id: str
    from_entity_id: str
    to_entity_id: str
    connection_type: ConnectionType
    status: ConnectionStatus
    trust_level: TrustLevel
    permissions: Dict[str, bool] = {}
    custom_label: Optional[str] = None
    notes: Optional[str] = None
    relationship_id: Optional[str] = None
    interaction_count: int = 0
    connected_at: Optional[datetime] = None
    last_interaction_at: Optional[datetime] = None

    # Backward compatibility
    @property
    def from_person_id(self) -> str:
        return self.from_entity_id

    @property
    def to_person_id(self) -> str:
        return self.to_entity_id


class ConnectRequest(BaseModel):
    """Request to connect with another entity."""
    to_entity_id: Optional[str] = None  # If known
    to_person_id: Optional[str] = None  # Lookup by person_id
    connection_type: ConnectionType = ConnectionType.PEER
    trust_level: TrustLevel = TrustLevel.STANDARD
    custom_label: Optional[str] = None
    message: Optional[str] = None


def _row_to_connection(row: Dict[str, Any]) -> SakhiConnection:
    """Convert database row to SakhiConnection."""
    return SakhiConnection(
        id=str(row["id"]),
        from_entity_id=str(row["from_entity_id"]),
        to_entity_id=str(row["to_entity_id"]),
        connection_type=ConnectionType(row.get("connection_type", "peer")),
        status=ConnectionStatus(row["status"]),
        trust_level=TrustLevel(row.get("trust_level", "standard")),
        permissions=row.get("permissions") or {},
        custom_label=row.get("custom_label"),
        notes=row.get("notes"),
        relationship_id=str(row["relationship_id"]) if row.get("relationship_id") else None,
        interaction_count=row.get("interaction_count", 0),
        connected_at=row.get("connected_at"),
        last_interaction_at=row.get("last_interaction_at"),
    )


# =============================================================================
# Connection Queries
# =============================================================================

async def get_connection(connection_id: str) -> Optional[SakhiConnection]:
    """Get connection by ID."""
    row = await dbfetch(
        "SELECT * FROM sakhi_connections WHERE id = $1",
        connection_id,
        one=True,
    )
    return _row_to_connection(row) if row else None


async def are_connected(
    person_a: str,
    person_b: str,
) -> bool:
    """Check if two people are connected (by person_id)."""
    # Get entity IDs
    entity_a = await get_entity_by_person(person_a)
    entity_b = await get_entity_by_person(person_b)

    if not entity_a or not entity_b:
        return False

    row = await dbfetch(
        """
        SELECT 1 FROM sakhi_connections
        WHERE status = 'connected'
          AND (
            (from_entity_id = $1 AND to_entity_id = $2)
            OR (from_entity_id = $2 AND to_entity_id = $1)
          )
        LIMIT 1
        """,
        entity_a.id,
        entity_b.id,
        one=True,
    )
    return bool(row)


async def get_trust_level(
    person_a: str,
    person_b: str,
) -> Optional[TrustLevel]:
    """Get trust level between two people."""
    entity_a = await get_entity_by_person(person_a)
    entity_b = await get_entity_by_person(person_b)

    if not entity_a or not entity_b:
        return None

    row = await dbfetch(
        """
        SELECT trust_level FROM sakhi_connections
        WHERE status = 'connected'
          AND (
            (from_entity_id = $1 AND to_entity_id = $2)
            OR (from_entity_id = $2 AND to_entity_id = $1)
          )
        LIMIT 1
        """,
        entity_a.id,
        entity_b.id,
        one=True,
    )

    if row:
        return TrustLevel(row["trust_level"])
    return None


async def get_connections(
    person_id: str,
    status: Optional[ConnectionStatus] = None,
    connection_type: Optional[ConnectionType] = None,
) -> List[SakhiConnection]:
    """Get all connections for a person."""
    entity = await get_entity_by_person(person_id)
    if not entity:
        return []

    query = """
        SELECT * FROM sakhi_connections
        WHERE (from_entity_id = $1 OR to_entity_id = $1)
    """
    params = [entity.id]
    param_idx = 2

    if status:
        query += f" AND status = ${param_idx}"
        params.append(status.value)
        param_idx += 1

    if connection_type:
        query += f" AND connection_type = ${param_idx}"
        params.append(connection_type.value)
        param_idx += 1

    query += " ORDER BY last_interaction_at DESC NULLS LAST"

    rows = await dbfetch(query, *params)
    return [_row_to_connection(r) for r in (rows or [])]


async def get_pending_requests(person_id: str) -> List[SakhiConnection]:
    """Get pending connection requests sent TO this person."""
    entity = await get_entity_by_person(person_id)
    if not entity:
        return []

    rows = await dbfetch(
        """
        SELECT * FROM sakhi_connections
        WHERE to_entity_id = $1 AND status = 'pending'
        ORDER BY created_at DESC
        """,
        entity.id,
    )
    return [_row_to_connection(r) for r in (rows or [])]


# =============================================================================
# Connection Actions
# =============================================================================

async def request_connection(
    from_person_id: str,
    request: ConnectRequest,
) -> SakhiConnection:
    """Send a connection request."""
    from_entity = await get_entity_by_person(from_person_id)
    if not from_entity:
        raise ValueError("Sender not found on Sakhi mesh")

    # Get target entity
    to_entity_id = request.to_entity_id
    if not to_entity_id and request.to_person_id:
        to_entity = await get_entity_by_person(request.to_person_id)
        if not to_entity:
            raise ValueError("Recipient not found on Sakhi mesh")
        to_entity_id = to_entity.id

    if not to_entity_id:
        raise ValueError("Must specify to_entity_id or to_person_id")

    import json
    default_permissions = {
        "can_schedule": True,
        "can_transact": request.connection_type in (ConnectionType.CUSTOMER, ConnectionType.VENDOR),
        "can_auto_book": False,
        "can_see_prices": True,
    }

    row = await dbfetch(
        """
        INSERT INTO sakhi_connections (
            from_entity_id, to_entity_id, connection_type,
            status, trust_level, permissions, custom_label, notes
        )
        VALUES ($1, $2, $3, 'pending', $4, $5::jsonb, $6, $7)
        ON CONFLICT (from_entity_id, to_entity_id) DO UPDATE
        SET status = 'pending', updated_at = NOW()
        RETURNING *
        """,
        from_entity.id,
        to_entity_id,
        request.connection_type.value,
        request.trust_level.value,
        json.dumps(default_permissions),
        request.custom_label,
        request.message,
        one=True,
    )

    LOGGER.info("[connection] Request sent: %s → %s", from_entity.id, to_entity_id)
    return _row_to_connection(row)


async def accept_connection(
    person_id: str,
    connection_id: str,
    trust_level: TrustLevel = TrustLevel.STANDARD,
) -> Optional[SakhiConnection]:
    """Accept a pending connection request."""
    entity = await get_entity_by_person(person_id)
    if not entity:
        return None

    row = await dbfetch(
        """
        UPDATE sakhi_connections
        SET status = 'connected',
            trust_level = $3,
            connected_at = NOW(),
            first_interaction_at = NOW()
        WHERE id = $2
          AND to_entity_id = $1
          AND status = 'pending'
        RETURNING *
        """,
        entity.id,
        connection_id,
        trust_level.value,
        one=True,
    )

    if row:
        LOGGER.info("[connection] Accepted: %s", connection_id)
        return _row_to_connection(row)
    return None


async def decline_connection(
    person_id: str,
    connection_id: str,
) -> bool:
    """Decline a pending connection request."""
    entity = await get_entity_by_person(person_id)
    if not entity:
        return False

    result = await dbexec(
        """
        DELETE FROM sakhi_connections
        WHERE id = $2
          AND to_entity_id = $1
          AND status = 'pending'
        """,
        entity.id,
        connection_id,
    )
    return True


async def update_trust_level(
    person_id: str,
    connection_id: str,
    trust_level: TrustLevel,
) -> Optional[SakhiConnection]:
    """Update trust level for a connection."""
    entity = await get_entity_by_person(person_id)
    if not entity:
        return None

    row = await dbfetch(
        """
        UPDATE sakhi_connections
        SET trust_level = $3
        WHERE id = $2
          AND (from_entity_id = $1 OR to_entity_id = $1)
          AND status = 'connected'
        RETURNING *
        """,
        entity.id,
        connection_id,
        trust_level.value,
        one=True,
    )

    return _row_to_connection(row) if row else None


async def disconnect(
    person_id: str,
    connection_id: str,
) -> bool:
    """Disconnect from someone."""
    entity = await get_entity_by_person(person_id)
    if not entity:
        return False

    await dbexec(
        """
        DELETE FROM sakhi_connections
        WHERE id = $2
          AND (from_entity_id = $1 OR to_entity_id = $1)
        """,
        entity.id,
        connection_id,
    )
    return True


async def block(
    person_id: str,
    connection_id: str,
) -> bool:
    """Block a connection."""
    entity = await get_entity_by_person(person_id)
    if not entity:
        return False

    await dbexec(
        """
        UPDATE sakhi_connections
        SET status = 'blocked'
        WHERE id = $2
          AND (from_entity_id = $1 OR to_entity_id = $1)
        """,
        entity.id,
        connection_id,
    )
    return True


async def link_relationship(
    person_id: str,
    connection_id: str,
    relationship_id: str,
) -> bool:
    """Link a connection to a relationship record."""
    entity = await get_entity_by_person(person_id)
    if not entity:
        return False

    await dbexec(
        """
        UPDATE sakhi_connections
        SET relationship_id = $3
        WHERE id = $2
          AND (from_entity_id = $1 OR to_entity_id = $1)
        """,
        entity.id,
        connection_id,
        relationship_id,
    )
    return True


async def record_interaction(
    person_id: str,
    connection_id: str,
) -> bool:
    """Record an interaction on a connection."""
    entity = await get_entity_by_person(person_id)
    if not entity:
        return False

    await dbexec(
        """
        UPDATE sakhi_connections
        SET interaction_count = interaction_count + 1,
            last_interaction_at = NOW()
        WHERE id = $2
          AND (from_entity_id = $1 OR to_entity_id = $1)
        """,
        entity.id,
        connection_id,
    )
    return True


__all__ = [
    "TrustLevel",
    "ConnectionStatus",
    "ConnectionType",
    "SakhiConnection",
    "ConnectRequest",
    "get_connection",
    "are_connected",
    "get_trust_level",
    "request_connection",
    "accept_connection",
    "decline_connection",
    "update_trust_level",
    "disconnect",
    "block",
    "get_connections",
    "get_pending_requests",
    "link_relationship",
    "record_interaction",
]
