"""
Relationships Service
---------------------
Manages rich relationship data for people in the user's life.

This service provides:
- Relationship CRUD operations
- Extraction of relationships from journal entries
- Enrichment of relationship context from conversations
- Scheduling-aware relationship queries
"""

from sakhi.apps.api.services.relationships.repository import (
    get_relationship,
    get_all_relationships,
    upsert_relationship,
    update_relationship_contact,
    get_relationships_needing_attention,
    get_relationship_for_scheduling,
)

from sakhi.apps.api.services.relationships.extraction import (
    extract_people_from_text,
    extract_relationship_signals,
)

from sakhi.apps.api.services.relationships.enrichment import (
    enrich_relationship_from_entry,
    enrich_relationship_context,
    process_entry_for_relationships,
)

__all__ = [
    # Repository
    "get_relationship",
    "get_all_relationships",
    "upsert_relationship",
    "update_relationship_contact",
    "get_relationships_needing_attention",
    "get_relationship_for_scheduling",
    # Extraction
    "extract_people_from_text",
    "extract_relationship_signals",
    # Enrichment
    "enrich_relationship_from_entry",
    "enrich_relationship_context",
    "process_entry_for_relationships",
]
