"""
Visual Memory Service
---------------------
Long-term memory learned from visual content.

Sakhi remembers what it sees and learns from visual patterns.
"""

from __future__ import annotations

import logging
import json
from typing import Any, Dict, List, Optional

from pydantic import BaseModel

from sakhi.apps.api.core.db import q as dbfetch, exec as dbexec

LOGGER = logging.getLogger(__name__)


class LearnedFact(BaseModel):
    """A fact learned from visual content."""
    fact: str
    confidence: float = 0.7
    source_media_id: Optional[str] = None


class VisualMemory(BaseModel):
    """A visual memory entry."""
    id: str
    person_id: str
    memory_type: str  # 'place', 'person', 'object', 'document', 'preference'
    subject: str
    learned_facts: List[LearnedFact] = []
    confidence: float = 0.5
    times_seen: int = 1


async def learn_from_image(
    person_id: str,
    media_id: str,
    analysis: Dict[str, Any],
    description: str,
) -> List[VisualMemory]:
    """
    Extract and store learnings from an analyzed image.

    Looks for:
    - Objects/items the user has
    - Places the user goes
    - Preferences (UI themes, styles, etc.)
    - People (if identifiable from context)
    """
    memories_created = []

    # Extract tags/objects
    objects = analysis.get("objects", [])
    tags = analysis.get("tags", [])

    # Learn about objects
    for obj in objects:
        if len(obj) > 2:  # Skip very short labels
            memory = await _create_or_update_memory(
                person_id=person_id,
                media_id=media_id,
                memory_type="object",
                subject=obj,
                fact=f"User has or uses: {obj}",
                description=description,
            )
            if memory:
                memories_created.append(memory)

    # Learn from document types
    doc_type = analysis.get("document_type")
    if doc_type:
        key_info = analysis.get("key_information", {})
        for key, value in key_info.items():
            if value:
                memory = await _create_or_update_memory(
                    person_id=person_id,
                    media_id=media_id,
                    memory_type="document",
                    subject=f"{doc_type}_{key}",
                    fact=f"From {doc_type}: {key} = {value}",
                    description=description,
                )
                if memory:
                    memories_created.append(memory)

    # Learn preferences from screenshots
    if analysis.get("sentiment"):
        # Could infer preferences from what user shows
        pass

    LOGGER.info(
        "[visual_memory] Learned %d facts from image %s",
        len(memories_created),
        media_id,
    )

    return memories_created


async def _create_or_update_memory(
    person_id: str,
    media_id: str,
    memory_type: str,
    subject: str,
    fact: str,
    description: str,
    confidence: float = 0.7,
) -> Optional[VisualMemory]:
    """Create or update a visual memory."""
    # Check if similar memory exists
    existing = await dbfetch(
        """
        SELECT * FROM vision_memory
        WHERE person_id = $1
          AND memory_type = $2
          AND LOWER(subject) = LOWER($3)
        """,
        person_id,
        memory_type,
        subject,
        one=True,
    )

    if existing:
        # Update existing memory
        learned_facts = existing.get("learned_facts") or []

        # Don't add duplicate facts
        fact_texts = [f.get("fact", "") for f in learned_facts]
        if fact not in fact_texts:
            learned_facts.append({
                "fact": fact,
                "confidence": confidence,
                "source_media_id": media_id,
            })

        # Increase confidence with repeated sightings
        new_confidence = min(0.95, existing.get("confidence", 0.5) + 0.1)

        await dbexec(
            """
            UPDATE vision_memory
            SET learned_facts = $4::jsonb,
                confidence = $5,
                times_seen = times_seen + 1,
                last_confirmed_at = NOW(),
                media_id = $3
            WHERE id = $2
            """,
            person_id,
            existing["id"],
            media_id,
            json.dumps(learned_facts),
            new_confidence,
        )

        return VisualMemory(
            id=str(existing["id"]),
            person_id=person_id,
            memory_type=memory_type,
            subject=subject,
            learned_facts=[LearnedFact(**f) for f in learned_facts],
            confidence=new_confidence,
            times_seen=existing.get("times_seen", 1) + 1,
        )

    else:
        # Create new memory
        learned_facts = [{
            "fact": fact,
            "confidence": confidence,
            "source_media_id": media_id,
        }]

        row = await dbfetch(
            """
            INSERT INTO vision_memory (
                person_id, media_id, memory_type, subject,
                learned_facts, source_description, confidence
            )
            VALUES ($1, $2, $3, $4, $5::jsonb, $6, $7)
            RETURNING *
            """,
            person_id,
            media_id,
            memory_type,
            subject,
            json.dumps(learned_facts),
            description,
            confidence,
            one=True,
        )

        return VisualMemory(
            id=str(row["id"]),
            person_id=person_id,
            memory_type=memory_type,
            subject=subject,
            learned_facts=[LearnedFact(**f) for f in learned_facts],
            confidence=confidence,
            times_seen=1,
        )


async def recall_visual_memory(
    person_id: str,
    memory_type: Optional[str] = None,
    subject: Optional[str] = None,
    min_confidence: float = 0.3,
    limit: int = 20,
) -> List[VisualMemory]:
    """
    Recall visual memories.

    Args:
        person_id: User ID
        memory_type: Filter by type (place, person, object, etc.)
        subject: Filter by subject (partial match)
        min_confidence: Minimum confidence threshold
        limit: Maximum memories to return
    """
    query = """
        SELECT * FROM vision_memory
        WHERE person_id = $1 AND confidence >= $2
    """
    params = [person_id, min_confidence]
    param_idx = 3

    if memory_type:
        query += f" AND memory_type = ${param_idx}"
        params.append(memory_type)
        param_idx += 1

    if subject:
        query += f" AND LOWER(subject) LIKE ${param_idx}"
        params.append(f"%{subject.lower()}%")
        param_idx += 1

    query += f" ORDER BY confidence DESC, times_seen DESC LIMIT {limit}"

    rows = await dbfetch(query, *params)

    return [
        VisualMemory(
            id=str(row["id"]),
            person_id=row["person_id"],
            memory_type=row["memory_type"],
            subject=row["subject"],
            learned_facts=[
                LearnedFact(**f) for f in (row.get("learned_facts") or [])
            ],
            confidence=row.get("confidence", 0.5),
            times_seen=row.get("times_seen", 1),
        )
        for row in (rows or [])
    ]


async def search_visual_memory(
    person_id: str,
    query: str,
    limit: int = 10,
) -> List[Dict[str, Any]]:
    """
    Search visual memories by text query.

    Searches subjects and learned facts.
    """
    rows = await dbfetch(
        """
        SELECT * FROM vision_memory
        WHERE person_id = $1
          AND (
            LOWER(subject) LIKE $2
            OR learned_facts::text ILIKE $2
            OR source_description ILIKE $2
          )
        ORDER BY confidence DESC, times_seen DESC
        LIMIT $3
        """,
        person_id,
        f"%{query.lower()}%",
        limit,
    )

    return [
        {
            "id": str(row["id"]),
            "memory_type": row["memory_type"],
            "subject": row["subject"],
            "learned_facts": row.get("learned_facts") or [],
            "confidence": row.get("confidence", 0.5),
            "times_seen": row.get("times_seen", 1),
        }
        for row in (rows or [])
    ]


async def get_visual_memory_summary(
    person_id: str,
) -> Dict[str, Any]:
    """
    Get a summary of what Sakhi has learned visually about the user.
    """
    # Count by type
    type_counts = await dbfetch(
        """
        SELECT memory_type, COUNT(*) as count
        FROM vision_memory
        WHERE person_id = $1 AND confidence >= 0.3
        GROUP BY memory_type
        """,
        person_id,
    )

    # Get high-confidence memories
    high_confidence = await dbfetch(
        """
        SELECT subject, memory_type, confidence, times_seen
        FROM vision_memory
        WHERE person_id = $1 AND confidence >= 0.7
        ORDER BY confidence DESC, times_seen DESC
        LIMIT 10
        """,
        person_id,
    )

    return {
        "total_by_type": {
            row["memory_type"]: row["count"]
            for row in (type_counts or [])
        },
        "high_confidence_memories": [
            {
                "subject": row["subject"],
                "type": row["memory_type"],
                "confidence": row["confidence"],
                "times_seen": row["times_seen"],
            }
            for row in (high_confidence or [])
        ],
    }


async def generate_visual_insight(
    person_id: str,
) -> Optional[Dict[str, Any]]:
    """
    Analyze visual memories and generate insights about patterns.

    Called periodically to find patterns across visual content.
    """
    # Get recent visual memories
    memories = await recall_visual_memory(
        person_id=person_id,
        min_confidence=0.4,
        limit=50,
    )

    if len(memories) < 5:
        return None  # Not enough data

    # Count recurring subjects and types
    subject_counts: Dict[str, int] = {}
    type_counts: Dict[str, int] = {}
    all_facts: List[str] = []

    for mem in memories:
        subject_counts[mem.subject] = subject_counts.get(mem.subject, 0) + mem.times_seen
        type_counts[mem.memory_type] = type_counts.get(mem.memory_type, 0) + 1
        for fact in mem.learned_facts:
            all_facts.append(fact.fact)

    # Find recurring patterns
    recurring_objects = [
        subj for subj, count in subject_counts.items()
        if count >= 3
    ][:10]

    if not recurring_objects:
        return None

    # Generate insight
    insight_type = "pattern"
    top_subjects = sorted(subject_counts.items(), key=lambda x: x[1], reverse=True)[:5]

    insight_text = f"From visual content: frequently sees {', '.join([s[0] for s in top_subjects[:3]])}"

    # Check for existing similar insight
    existing = await dbfetch(
        """
        SELECT id, times_confirmed, confidence FROM visual_insights
        WHERE person_id = $1 AND insight_type = $2
        ORDER BY times_confirmed DESC
        LIMIT 1
        """,
        person_id,
        insight_type,
        one=True,
    )

    if existing:
        # Update existing insight
        new_confidence = min(0.95, existing.get("confidence", 0.5) + 0.05)
        await dbexec(
            """
            UPDATE visual_insights
            SET insight = $3,
                confidence = $4,
                patterns = $5::jsonb,
                times_confirmed = times_confirmed + 1,
                last_confirmed_at = NOW(),
                updated_at = NOW()
            WHERE id = $2
            """,
            person_id,
            existing["id"],
            insight_text,
            new_confidence,
            json.dumps({
                "recurring_objects": recurring_objects,
                "type_distribution": type_counts,
            }),
        )
        return {
            "id": str(existing["id"]),
            "insight": insight_text,
            "updated": True,
        }
    else:
        # Create new insight
        row = await dbfetch(
            """
            INSERT INTO visual_insights (
                person_id, insight_type, insight, confidence, patterns
            )
            VALUES ($1, $2, $3, 0.5, $4::jsonb)
            RETURNING id
            """,
            person_id,
            insight_type,
            insight_text,
            json.dumps({
                "recurring_objects": recurring_objects,
                "type_distribution": type_counts,
            }),
            one=True,
        )
        return {
            "id": str(row["id"]) if row else None,
            "insight": insight_text,
            "created": True,
        }


async def get_visual_insights(
    person_id: str,
    min_confidence: float = 0.3,
    limit: int = 10,
) -> List[Dict[str, Any]]:
    """Get visual insights for a person."""
    rows = await dbfetch(
        """
        SELECT id, insight_type, insight, confidence, patterns,
               times_confirmed, first_observed_at
        FROM visual_insights
        WHERE person_id = $1 AND confidence >= $2
        ORDER BY confidence DESC, times_confirmed DESC
        LIMIT $3
        """,
        person_id,
        min_confidence,
        limit,
    )

    return [
        {
            "id": str(row["id"]),
            "insight_type": row["insight_type"],
            "insight": row["insight"],
            "confidence": row.get("confidence", 0.5),
            "patterns": row.get("patterns") or {},
            "times_confirmed": row.get("times_confirmed", 1),
            "first_observed_at": str(row["first_observed_at"]) if row.get("first_observed_at") else None,
        }
        for row in (rows or [])
    ]


__all__ = [
    "LearnedFact",
    "VisualMemory",
    "learn_from_image",
    "recall_visual_memory",
    "search_visual_memory",
    "get_visual_memory_summary",
    "generate_visual_insight",
    "get_visual_insights",
]
