"""
Research Service
----------------
Multi-turn research sessions for Sakhi.
"""

from __future__ import annotations

import logging
import json
from typing import Any, Dict, List, Optional

from pydantic import BaseModel

from sakhi.apps.api.core.db import q as dbfetch, exec as dbexec

LOGGER = logging.getLogger(__name__)


class ResearchSource(BaseModel):
    """A source gathered during research."""
    url: str
    title: str
    summary: str
    relevance: float = 0.5
    content_preview: Optional[str] = None


class ResearchSession(BaseModel):
    """A multi-turn research session."""
    id: str
    person_id: str
    topic: str
    question: Optional[str] = None
    sources: List[ResearchSource] = []
    findings: List[str] = []
    synthesis: Optional[str] = None
    status: str = "active"


async def start_research(
    person_id: str,
    topic: str,
    question: Optional[str] = None,
    auto_search: bool = True,
) -> ResearchSession:
    """
    Start a new research session.

    Args:
        person_id: User ID
        topic: Research topic
        question: Specific question to answer
        auto_search: Automatically perform initial search

    Returns:
        ResearchSession
    """
    row = await dbfetch(
        """
        INSERT INTO research_sessions (person_id, topic, question, status)
        VALUES ($1, $2, $3, 'active')
        RETURNING id
        """,
        person_id,
        topic,
        question,
        one=True,
    )

    session = ResearchSession(
        id=str(row["id"]),
        person_id=person_id,
        topic=topic,
        question=question,
    )

    # Perform initial search
    if auto_search:
        from sakhi.apps.api.services.agentic.search import web_search

        query = question or topic
        results = await web_search(query, max_results=5)

        for r in results.results:
            await add_research_source(
                session_id=session.id,
                url=r.url,
                title=r.title,
                summary=r.snippet,
                relevance=r.relevance_score,
            )
            session.sources.append(ResearchSource(
                url=r.url,
                title=r.title,
                summary=r.snippet,
                relevance=r.relevance_score,
            ))

        LOGGER.info("[research] Started session %s with %d sources", session.id, len(session.sources))

    return session


async def get_research_session(session_id: str) -> Optional[ResearchSession]:
    """Get a research session by ID."""
    row = await dbfetch(
        "SELECT * FROM research_sessions WHERE id = $1",
        session_id,
        one=True,
    )

    if not row:
        return None

    sources = [ResearchSource(**s) for s in (row.get("sources") or [])]
    findings = row.get("findings") or []

    return ResearchSession(
        id=str(row["id"]),
        person_id=row["person_id"],
        topic=row["topic"],
        question=row.get("question"),
        sources=sources,
        findings=findings,
        synthesis=row.get("synthesis"),
        status=row["status"],
    )


async def add_research_source(
    session_id: str,
    url: str,
    title: str,
    summary: str,
    relevance: float = 0.5,
    content_preview: Optional[str] = None,
) -> bool:
    """Add a source to a research session."""
    source = {
        "url": url,
        "title": title,
        "summary": summary,
        "relevance": relevance,
        "content_preview": content_preview,
    }

    await dbexec(
        """
        UPDATE research_sessions
        SET sources = sources || $2::jsonb,
            updated_at = NOW()
        WHERE id = $1
        """,
        session_id,
        json.dumps([source]),
    )

    return True


async def add_research_finding(
    session_id: str,
    finding: str,
) -> bool:
    """Add a finding to a research session."""
    await dbexec(
        """
        UPDATE research_sessions
        SET findings = findings || $2::jsonb,
            updated_at = NOW()
        WHERE id = $1
        """,
        session_id,
        json.dumps([finding]),
    )

    return True


async def expand_research(
    session_id: str,
    follow_up_query: str,
) -> ResearchSession:
    """
    Expand research with a follow-up query.

    Searches for more information and adds to session.
    """
    from sakhi.apps.api.services.agentic.search import web_search

    session = await get_research_session(session_id)
    if not session:
        raise ValueError(f"Session not found: {session_id}")

    # Search for more information
    results = await web_search(follow_up_query, max_results=5)

    for r in results.results:
        # Check if we already have this source
        existing_urls = [s.url for s in session.sources]
        if r.url not in existing_urls:
            await add_research_source(
                session_id=session_id,
                url=r.url,
                title=r.title,
                summary=r.snippet,
                relevance=r.relevance_score,
            )
            session.sources.append(ResearchSource(
                url=r.url,
                title=r.title,
                summary=r.snippet,
                relevance=r.relevance_score,
            ))

    return session


async def synthesize_research(
    session_id: str,
) -> str:
    """
    Synthesize all research into a comprehensive answer.

    Uses LLM to combine sources and findings.
    """
    from sakhi.apps.api.core.llm import get_router

    session = await get_research_session(session_id)
    if not session:
        raise ValueError(f"Session not found: {session_id}")

    # Build context from sources
    sources_text = "\n\n".join([
        f"Source: {s.title}\nURL: {s.url}\nSummary: {s.summary}"
        for s in session.sources[:10]  # Limit to top 10
    ])

    findings_text = "\n".join([f"- {f}" for f in session.findings]) if session.findings else "No specific findings yet."

    prompt = f"""You are a research synthesizer. Based on the gathered sources and findings, provide a comprehensive answer.

Topic: {session.topic}
Question: {session.question or "General research on the topic"}

Sources:
{sources_text}

Findings so far:
{findings_text}

Provide a well-organized synthesis that:
1. Answers the question/covers the topic thoroughly
2. Cites sources where relevant
3. Highlights key insights
4. Notes any limitations or areas needing more research

Be comprehensive but clear."""

    try:
        router = get_router()
        response = await router.chat(
            messages=[{"role": "user", "content": prompt}],
            model="claude-sonnet-4-20250514",
            max_tokens=1500,
        )
        synthesis = response.content[0].text if response.content else "Unable to synthesize research."

    except Exception as e:
        LOGGER.error("[research] Synthesis failed: %s", e)
        synthesis = "Research synthesis failed. Please review sources manually."

    # Save synthesis
    await dbexec(
        """
        UPDATE research_sessions
        SET synthesis = $2,
            status = 'completed',
            updated_at = NOW()
        WHERE id = $1
        """,
        session_id,
        synthesis,
    )

    return synthesis


async def get_active_research(person_id: str) -> List[ResearchSession]:
    """Get active research sessions for a user."""
    rows = await dbfetch(
        """
        SELECT * FROM research_sessions
        WHERE person_id = $1 AND status = 'active'
        ORDER BY updated_at DESC
        LIMIT 5
        """,
        person_id,
    )

    return [
        ResearchSession(
            id=str(row["id"]),
            person_id=row["person_id"],
            topic=row["topic"],
            question=row.get("question"),
            sources=[ResearchSource(**s) for s in (row.get("sources") or [])],
            findings=row.get("findings") or [],
            synthesis=row.get("synthesis"),
            status=row["status"],
        )
        for row in (rows or [])
    ]


__all__ = [
    "ResearchSource",
    "ResearchSession",
    "start_research",
    "get_research_session",
    "add_research_source",
    "add_research_finding",
    "expand_research",
    "synthesize_research",
    "get_active_research",
]
