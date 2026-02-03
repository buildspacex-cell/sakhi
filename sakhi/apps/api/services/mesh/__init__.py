"""
Sakhi Mesh Service
------------------
Sakhi-to-Sakhi coordination infrastructure.

Your Sakhi talks to other Sakhis so you don't have to
coordinate manually. Share availability, propose times,
and let your Sakhis figure out when to meet.

Now also supports:
- Business/service entities
- Transactions & inquiries
- Reviews & feedback

Components:
- entities.py: Entity management (people & businesses)
- connections.py: Connection and trust management
- coordination.py: Scheduling coordination protocol
- availability.py: Privacy-respecting availability sharing
"""

# New unified entity model
from sakhi.apps.api.services.mesh.entities import (
    EntityType,
    SakhiEntity,
    CreateEntityRequest,
    UpdateEntityRequest,
    get_entity,
    get_entity_by_person,
    create_entity,
    update_entity,
    find_by_handle,
    search_entities,
    search_businesses,
    add_auto_accept,
    remove_auto_accept,
    update_last_active,
)

# Backward compatibility: alias old profile names to new entity names
SakhiProfile = SakhiEntity
CreateProfileRequest = CreateEntityRequest
UpdateProfileRequest = UpdateEntityRequest
get_profile = get_entity_by_person
create_profile = create_entity
update_profile = update_entity
search_profiles = search_entities

from sakhi.apps.api.services.mesh.connections import (
    TrustLevel,
    ConnectionStatus,
    ConnectionType,
    SakhiConnection,
    ConnectRequest,
    get_connection,
    are_connected,
    get_trust_level,
    request_connection,
    accept_connection,
    decline_connection,
    update_trust_level,
    disconnect,
    block,
    get_connections,
    get_pending_requests,
    link_relationship,
)

from sakhi.apps.api.services.mesh.coordination import (
    CoordinationType,
    CoordinationStatus,
    MessageType,
    CoordinationThread,
    CoordinationMessage,
    ProposalRequest,
    ProposalResponse,
    initiate_coordination,
    respond_to_proposal,
    get_pending_proposals,
    get_active_threads,
)

from sakhi.apps.api.services.mesh.availability import (
    AvailabilityDetail,
    TimeSlot,
    SharedAvailability,
    compute_shareable_availability,
    cache_shared_availability,
    find_overlapping_times,
)

__all__ = [
    # Entities (new)
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
    # Backward compatibility (old names)
    "SakhiProfile",
    "CreateProfileRequest",
    "UpdateProfileRequest",
    "get_profile",
    "create_profile",
    "update_profile",
    "search_profiles",
    # Connections
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
    # Coordination
    "CoordinationType",
    "CoordinationStatus",
    "MessageType",
    "CoordinationThread",
    "CoordinationMessage",
    "ProposalRequest",
    "ProposalResponse",
    "initiate_coordination",
    "respond_to_proposal",
    "get_pending_proposals",
    "get_active_threads",
    # Privacy & Availability
    "AvailabilityDetail",
    "TimeSlot",
    "SharedAvailability",
    "compute_shareable_availability",
    "cache_shared_availability",
    "find_overlapping_times",
]
