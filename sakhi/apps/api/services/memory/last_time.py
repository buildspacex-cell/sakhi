"""
Last Time Lookup Service
------------------------
Answers "when was the last time..." questions across all memory sources.

This is a key feature of Sakhi's reflective intelligence:
- "When was the last time I saw Mom?"
- "When was the last time I ate pizza?"
- "When was the last time I exercised?"
- "When was the last time I went to a movie?"

Searches across:
- Food experiences (what you ate, where)
- Journal entries (general life events)
- Calendar events (scheduled activities)
- Episodic memory (significant moments)
- Relationship interactions (time with people)
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta

from sakhi.apps.api.core.db import q as dbfetch

LOGGER = logging.getLogger(__name__)


# =============================================================================
# Result Types
# =============================================================================

class LastTimeResult:
    """Result of a 'last time' query."""

    def __init__(
        self,
        found: bool,
        when: Optional[datetime] = None,
        what: Optional[str] = None,
        context: Optional[str] = None,
        source: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.found = found
        self.when = when
        self.what = what
        self.context = context
        self.source = source
        self.details = details or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "found": self.found,
            "when": self.when.isoformat() if self.when else None,
            "when_relative": self._relative_time() if self.when else None,
            "what": self.what,
            "context": self.context,
            "source": self.source,
            "details": self.details,
        }

    def _relative_time(self) -> str:
        """Convert to human-readable relative time."""
        if not self.when:
            return ""

        now = datetime.utcnow()
        diff = now - self.when

        if diff.days == 0:
            if diff.seconds < 3600:
                mins = diff.seconds // 60
                return f"{mins} minutes ago" if mins > 1 else "just now"
            hours = diff.seconds // 3600
            return f"{hours} hours ago" if hours > 1 else "1 hour ago"
        elif diff.days == 1:
            return "yesterday"
        elif diff.days < 7:
            return f"{diff.days} days ago"
        elif diff.days < 30:
            weeks = diff.days // 7
            return f"{weeks} weeks ago" if weeks > 1 else "1 week ago"
        elif diff.days < 365:
            months = diff.days // 30
            return f"{months} months ago" if months > 1 else "1 month ago"
        else:
            years = diff.days // 365
            return f"{years} years ago" if years > 1 else "1 year ago"


# =============================================================================
# Main Lookup Function
# =============================================================================

async def last_time(
    person_id: str,
    query: str,
) -> LastTimeResult:
    """
    Find when the user last did something.

    This is the main entry point - it determines the query type
    and searches the appropriate memory sources.

    Args:
        person_id: User's person ID
        query: Natural language query (e.g., "ate pizza", "saw Mom", "exercised")

    Returns:
        LastTimeResult with when, what, and context
    """
    query_lower = query.lower().strip()

    # Determine query type and search appropriate sources
    # Food-related queries
    if any(word in query_lower for word in ["ate", "eat", "had", "order", "food", "restaurant"]):
        return await _search_food(person_id, query_lower)

    # People/relationship queries
    if any(word in query_lower for word in ["saw", "met", "visited", "called", "talked"]):
        return await _search_people(person_id, query_lower)

    # Activity queries
    if any(word in query_lower for word in ["went", "did", "played", "watched", "exercised", "workout"]):
        return await _search_activities(person_id, query_lower)

    # Default: search across all sources
    return await _search_all(person_id, query_lower)


# =============================================================================
# Specialized Search Functions
# =============================================================================

async def _search_food(person_id: str, query: str) -> LastTimeResult:
    """Search food experiences."""
    # Extract what they're looking for
    keywords = _extract_keywords(query)

    # Try food_experiences table first
    for keyword in keywords:
        row = await dbfetch(
            """
            SELECT * FROM food_experiences
            WHERE person_id = $1
              AND (
                LOWER(dish_name) LIKE LOWER($2)
                OR LOWER(cuisine) LIKE LOWER($2)
                OR LOWER(restaurant_name) LIKE LOWER($2)
              )
            ORDER BY experience_date DESC
            LIMIT 1
            """,
            person_id,
            f"%{keyword}%",
            one=True,
        )

        if row:
            return LastTimeResult(
                found=True,
                when=row.get("experience_date"),
                what=row.get("dish_name"),
                context=f"at {row.get('restaurant_name')}" if row.get("restaurant_name") else "at home",
                source="food_experiences",
                details={
                    "dish": row.get("dish_name"),
                    "restaurant": row.get("restaurant_name"),
                    "cuisine": row.get("cuisine"),
                    "rating": row.get("rating"),
                },
            )

    # Fall back to journal entries with food context
    return await _search_journals(person_id, query, context_type="food")


async def _search_people(person_id: str, query: str) -> LastTimeResult:
    """Search for last time interacting with a person."""
    keywords = _extract_keywords(query)

    # Try to extract person name (usually after "saw", "met", etc.)
    person_name = None
    for keyword in keywords:
        if keyword.istitle() or keyword in ["mom", "dad", "brother", "sister"]:
            person_name = keyword
            break

    if person_name:
        # Search journal entries for mentions
        row = await dbfetch(
            """
            SELECT id, content, created_at
            FROM journal_entries
            WHERE user_id = $1
              AND LOWER(content) LIKE LOWER($2)
            ORDER BY created_at DESC
            LIMIT 1
            """,
            person_id,
            f"%{person_name}%",
            one=True,
        )

        if row:
            return LastTimeResult(
                found=True,
                when=row.get("created_at"),
                what=f"mentioned {person_name}",
                context=_extract_context(row.get("content", ""), person_name),
                source="journal_entries",
                details={"entry_id": str(row.get("id"))},
            )

        # Search calendar events
        row = await dbfetch(
            """
            SELECT * FROM calendar_events
            WHERE user_id = $1
              AND (
                LOWER(title) LIKE LOWER($2)
                OR LOWER(description) LIKE LOWER($2)
              )
              AND start_time < NOW()
            ORDER BY start_time DESC
            LIMIT 1
            """,
            person_id,
            f"%{person_name}%",
            one=True,
        )

        if row:
            return LastTimeResult(
                found=True,
                when=row.get("start_time"),
                what=row.get("title"),
                context=row.get("location"),
                source="calendar_events",
                details={
                    "event_id": str(row.get("id")),
                    "title": row.get("title"),
                    "location": row.get("location"),
                },
            )

    return LastTimeResult(found=False, what=query)


async def _search_activities(person_id: str, query: str) -> LastTimeResult:
    """Search for last time doing an activity."""
    keywords = _extract_keywords(query)

    # Search calendar events first (most structured)
    for keyword in keywords:
        row = await dbfetch(
            """
            SELECT * FROM calendar_events
            WHERE user_id = $1
              AND (
                LOWER(title) LIKE LOWER($2)
                OR LOWER(description) LIKE LOWER($2)
              )
              AND start_time < NOW()
            ORDER BY start_time DESC
            LIMIT 1
            """,
            person_id,
            f"%{keyword}%",
            one=True,
        )

        if row:
            return LastTimeResult(
                found=True,
                when=row.get("start_time"),
                what=row.get("title"),
                context=row.get("location"),
                source="calendar_events",
                details={
                    "event_id": str(row.get("id")),
                    "title": row.get("title"),
                    "location": row.get("location"),
                    "duration_minutes": row.get("duration_minutes"),
                },
            )

    # Fall back to journal entries
    return await _search_journals(person_id, query, context_type="activity")


async def _search_journals(
    person_id: str,
    query: str,
    context_type: Optional[str] = None,
) -> LastTimeResult:
    """Search journal entries as fallback."""
    keywords = _extract_keywords(query)

    for keyword in keywords:
        row = await dbfetch(
            """
            SELECT id, content, created_at,
                ts_rank(to_tsvector('english', content), plainto_tsquery('english', $2)) as rank
            FROM journal_entries
            WHERE user_id = $1
              AND to_tsvector('english', content) @@ plainto_tsquery('english', $2)
            ORDER BY rank DESC, created_at DESC
            LIMIT 1
            """,
            person_id,
            keyword,
            one=True,
        )

        if row:
            return LastTimeResult(
                found=True,
                when=row.get("created_at"),
                what=f"mentioned {keyword}",
                context=_extract_context(row.get("content", ""), keyword),
                source="journal_entries",
                details={"entry_id": str(row.get("id"))},
            )

    return LastTimeResult(found=False, what=query)


async def _search_all(person_id: str, query: str) -> LastTimeResult:
    """Search all sources when query type is unclear."""
    # Try each source in order of structure
    result = await _search_food(person_id, query)
    if result.found:
        return result

    result = await _search_people(person_id, query)
    if result.found:
        return result

    result = await _search_activities(person_id, query)
    if result.found:
        return result

    return await _search_journals(person_id, query)


# =============================================================================
# Convenience Functions
# =============================================================================

async def last_time_with_person(
    person_id: str,
    person_name: str,
) -> LastTimeResult:
    """
    Find the last time the user interacted with a specific person.

    Args:
        person_id: User's person ID
        person_name: Name of the person to search for

    Returns:
        LastTimeResult with interaction details
    """
    return await last_time(person_id, f"saw {person_name}")


async def last_time_at_place(
    person_id: str,
    place_name: str,
) -> LastTimeResult:
    """
    Find the last time the user visited a place.

    Args:
        person_id: User's person ID
        place_name: Name of the place

    Returns:
        LastTimeResult with visit details
    """
    # Check food experiences (restaurants)
    row = await dbfetch(
        """
        SELECT * FROM food_experiences
        WHERE person_id = $1 AND LOWER(restaurant_name) LIKE LOWER($2)
        ORDER BY experience_date DESC
        LIMIT 1
        """,
        person_id,
        f"%{place_name}%",
        one=True,
    )

    if row:
        return LastTimeResult(
            found=True,
            when=row.get("experience_date"),
            what=f"visited {row.get('restaurant_name')}",
            context=f"had {row.get('dish_name')}",
            source="food_experiences",
            details={
                "place": row.get("restaurant_name"),
                "dish": row.get("dish_name"),
            },
        )

    # Check calendar events
    row = await dbfetch(
        """
        SELECT * FROM calendar_events
        WHERE user_id = $1 AND LOWER(location) LIKE LOWER($2)
        AND start_time < NOW()
        ORDER BY start_time DESC
        LIMIT 1
        """,
        person_id,
        f"%{place_name}%",
        one=True,
    )

    if row:
        return LastTimeResult(
            found=True,
            when=row.get("start_time"),
            what=row.get("title"),
            context=row.get("location"),
            source="calendar_events",
            details={"event_id": str(row.get("id"))},
        )

    return LastTimeResult(found=False, what=f"visited {place_name}")


async def last_time_doing(
    person_id: str,
    activity: str,
) -> LastTimeResult:
    """
    Find the last time the user did a specific activity.

    Args:
        person_id: User's person ID
        activity: The activity (e.g., "exercised", "meditated", "watched movie")

    Returns:
        LastTimeResult with activity details
    """
    return await last_time(person_id, f"did {activity}")


async def days_since(
    person_id: str,
    query: str,
) -> Optional[int]:
    """
    Get the number of days since something happened.

    Args:
        person_id: User's person ID
        query: What to search for

    Returns:
        Number of days since, or None if not found
    """
    result = await last_time(person_id, query)
    if result.found and result.when:
        delta = datetime.utcnow() - result.when
        return delta.days
    return None


# =============================================================================
# Helper Functions
# =============================================================================

def _extract_keywords(query: str) -> List[str]:
    """Extract searchable keywords from query."""
    # Remove common words
    stopwords = {
        "i", "the", "a", "an", "to", "was", "were", "is", "are",
        "last", "time", "when", "did", "ate", "eat", "had", "went",
        "saw", "met", "visited", "talked", "called",
    }

    words = query.lower().split()
    keywords = [w for w in words if w not in stopwords and len(w) > 2]

    # Also include the original query for phrase matching
    if len(keywords) > 1:
        keywords.append(" ".join(keywords))

    return keywords


def _extract_context(content: str, keyword: str) -> str:
    """Extract relevant context around a keyword in text."""
    if not content or not keyword:
        return ""

    content_lower = content.lower()
    keyword_lower = keyword.lower()

    idx = content_lower.find(keyword_lower)
    if idx == -1:
        return content[:100] + "..." if len(content) > 100 else content

    # Get context window around the keyword
    start = max(0, idx - 50)
    end = min(len(content), idx + len(keyword) + 50)

    context = content[start:end]

    if start > 0:
        context = "..." + context
    if end < len(content):
        context = context + "..."

    return context


__all__ = [
    "LastTimeResult",
    "last_time",
    "last_time_with_person",
    "last_time_at_place",
    "last_time_doing",
    "days_since",
]
