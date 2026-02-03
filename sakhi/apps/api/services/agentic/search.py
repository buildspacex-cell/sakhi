"""
Web Search Service
------------------
Search the web and fetch URLs for Sakhi.
"""

from __future__ import annotations

import hashlib
import logging
import os
import json
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta

import httpx
from pydantic import BaseModel

from sakhi.apps.api.core.db import q as dbfetch, exec as dbexec

LOGGER = logging.getLogger(__name__)

# Search providers
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
SERP_API_KEY = os.getenv("SERP_API_KEY")
BRAVE_API_KEY = os.getenv("BRAVE_API_KEY")


class SearchResult(BaseModel):
    """A single search result."""
    title: str
    url: str
    snippet: str
    source: Optional[str] = None
    published_date: Optional[str] = None
    relevance_score: float = 0.0


class SearchResponse(BaseModel):
    """Response from a search query."""
    query: str
    results: List[SearchResult] = []
    total_results: int = 0
    search_engine: str = "web"
    cached: bool = False


def _hash_query(query: str) -> str:
    """Create consistent hash for query caching."""
    normalized = query.lower().strip()
    return hashlib.sha256(normalized.encode()).hexdigest()[:32]


async def _get_cached_results(query_hash: str) -> Optional[List[Dict[str, Any]]]:
    """Check cache for existing results."""
    row = await dbfetch(
        """
        UPDATE search_cache
        SET hit_count = hit_count + 1
        WHERE query_hash = $1 AND expires_at > NOW()
        RETURNING results
        """,
        query_hash,
        one=True,
    )
    if row:
        return row.get("results")
    return None


async def _cache_results(
    query: str,
    query_hash: str,
    results: List[Dict[str, Any]],
    search_engine: str = "web",
    ttl_hours: int = 1,
) -> None:
    """Cache search results."""
    await dbexec(
        """
        INSERT INTO search_cache (query_hash, query_text, search_engine, results, result_count, expires_at)
        VALUES ($1, $2, $3, $4::jsonb, $5, NOW() + $6 * INTERVAL '1 hour')
        ON CONFLICT (query_hash) DO UPDATE
        SET results = $4::jsonb,
            result_count = $5,
            expires_at = NOW() + $6 * INTERVAL '1 hour',
            searched_at = NOW()
        """,
        query_hash,
        query,
        search_engine,
        json.dumps(results),
        len(results),
        ttl_hours,
    )


async def _search_tavily(query: str, max_results: int = 5) -> List[SearchResult]:
    """Search using Tavily API."""
    if not TAVILY_API_KEY:
        return []

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": TAVILY_API_KEY,
                    "query": query,
                    "max_results": max_results,
                    "include_answer": False,
                    "search_depth": "basic",
                },
                timeout=30.0,
            )
            response.raise_for_status()
            data = response.json()

            results = []
            for item in data.get("results", []):
                results.append(SearchResult(
                    title=item.get("title", ""),
                    url=item.get("url", ""),
                    snippet=item.get("content", "")[:500],
                    source=item.get("source"),
                    relevance_score=item.get("score", 0.5),
                ))
            return results

        except Exception as e:
            LOGGER.error("[search] Tavily search failed: %s", e)
            return []


async def _search_brave(query: str, max_results: int = 5) -> List[SearchResult]:
    """Search using Brave Search API."""
    if not BRAVE_API_KEY:
        return []

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                "https://api.search.brave.com/res/v1/web/search",
                params={
                    "q": query,
                    "count": max_results,
                },
                headers={
                    "X-Subscription-Token": BRAVE_API_KEY,
                    "Accept": "application/json",
                },
                timeout=30.0,
            )
            response.raise_for_status()
            data = response.json()

            results = []
            for item in data.get("web", {}).get("results", []):
                results.append(SearchResult(
                    title=item.get("title", ""),
                    url=item.get("url", ""),
                    snippet=item.get("description", "")[:500],
                    source=item.get("profile", {}).get("name"),
                    relevance_score=0.7,
                ))
            return results

        except Exception as e:
            LOGGER.error("[search] Brave search failed: %s", e)
            return []


async def _search_fallback(query: str, max_results: int = 5) -> List[SearchResult]:
    """
    Fallback search using DuckDuckGo HTML scraping.
    Note: This is a basic fallback - production should use proper API.
    """
    # For now, return empty - in production, implement DDG or other fallback
    LOGGER.warning("[search] No search API configured, returning empty results")
    return []


async def web_search(
    query: str,
    max_results: int = 5,
    use_cache: bool = True,
) -> SearchResponse:
    """
    Search the web for information.

    Args:
        query: Search query
        max_results: Maximum number of results
        use_cache: Whether to use cached results

    Returns:
        SearchResponse with results
    """
    query_hash = _hash_query(query)

    # Check cache
    if use_cache:
        cached = await _get_cached_results(query_hash)
        if cached:
            LOGGER.info("[search] Cache hit for query: %s", query[:50])
            return SearchResponse(
                query=query,
                results=[SearchResult(**r) for r in cached],
                total_results=len(cached),
                cached=True,
            )

    # Try search providers in order
    results: List[SearchResult] = []

    if TAVILY_API_KEY:
        results = await _search_tavily(query, max_results)
    elif BRAVE_API_KEY:
        results = await _search_brave(query, max_results)
    else:
        results = await _search_fallback(query, max_results)

    # Cache results
    if results:
        await _cache_results(
            query=query,
            query_hash=query_hash,
            results=[r.model_dump() for r in results],
        )

    LOGGER.info("[search] Searched: %s, found %d results", query[:50], len(results))

    return SearchResponse(
        query=query,
        results=results,
        total_results=len(results),
        cached=False,
    )


async def news_search(
    query: str,
    max_results: int = 5,
    days_back: int = 7,
) -> SearchResponse:
    """Search for recent news articles."""
    # Enhance query for news
    news_query = f"{query} news {datetime.now().year}"

    response = await web_search(news_query, max_results)
    response.search_engine = "news"
    return response


async def fetch_url(
    url: str,
    extract_content: bool = True,
    max_length: int = 10000,
) -> Dict[str, Any]:
    """
    Fetch content from a URL.

    Args:
        url: URL to fetch
        extract_content: Whether to extract main content
        max_length: Maximum content length

    Returns:
        Dict with title, content, metadata
    """
    async with httpx.AsyncClient(follow_redirects=True) as client:
        try:
            response = await client.get(
                url,
                headers={
                    "User-Agent": "Mozilla/5.0 (compatible; SakhiBot/1.0)",
                },
                timeout=30.0,
            )
            response.raise_for_status()

            content_type = response.headers.get("content-type", "")

            if "text/html" in content_type:
                html = response.text

                # Basic content extraction
                # In production, use readability or similar library
                title = ""
                content = html

                # Try to extract title
                if "<title>" in html:
                    start = html.find("<title>") + 7
                    end = html.find("</title>")
                    if end > start:
                        title = html[start:end].strip()

                # Basic HTML to text (very basic - use proper library in production)
                import re
                # Remove script and style
                content = re.sub(r'<script[^>]*>.*?</script>', '', content, flags=re.DOTALL | re.IGNORECASE)
                content = re.sub(r'<style[^>]*>.*?</style>', '', content, flags=re.DOTALL | re.IGNORECASE)
                # Remove tags
                content = re.sub(r'<[^>]+>', ' ', content)
                # Clean whitespace
                content = re.sub(r'\s+', ' ', content).strip()
                content = content[:max_length]

                return {
                    "url": url,
                    "title": title,
                    "content": content,
                    "content_type": "html",
                    "length": len(content),
                    "success": True,
                }

            elif "application/json" in content_type:
                return {
                    "url": url,
                    "title": url,
                    "content": response.text[:max_length],
                    "content_type": "json",
                    "length": len(response.text),
                    "success": True,
                }

            else:
                return {
                    "url": url,
                    "title": url,
                    "content": f"Binary content: {content_type}",
                    "content_type": content_type,
                    "success": True,
                }

        except httpx.HTTPStatusError as e:
            return {
                "url": url,
                "error": f"HTTP {e.response.status_code}",
                "success": False,
            }
        except Exception as e:
            LOGGER.error("[search] URL fetch failed: %s - %s", url, e)
            return {
                "url": url,
                "error": str(e),
                "success": False,
            }


async def summarize_search_results(
    results: List[SearchResult],
    query: str,
    max_length: int = 500,
) -> str:
    """
    Summarize search results into a concise answer.

    Uses LLM to synthesize results.
    """
    from sakhi.apps.api.core.llm import get_router

    if not results:
        return f"No results found for: {query}"

    # Build context from results
    context_parts = []
    for i, r in enumerate(results[:5], 1):
        context_parts.append(f"{i}. [{r.title}]({r.url})\n{r.snippet}")

    context = "\n\n".join(context_parts)

    prompt = f"""Based on these search results, provide a concise answer to: "{query}"

Search Results:
{context}

Provide a helpful, accurate summary in 2-3 sentences. Include relevant details from the sources."""

    try:
        router = get_router()
        response = await router.chat(
            messages=[{"role": "user", "content": prompt}],
            model="claude-sonnet-4-20250514",
            max_tokens=300,
        )
        return response.content[0].text if response.content else "Unable to summarize results."
    except Exception as e:
        LOGGER.error("[search] Summarization failed: %s", e)
        # Fallback to first result snippet
        return results[0].snippet if results else "No results found."


__all__ = [
    "SearchResult",
    "SearchResponse",
    "web_search",
    "news_search",
    "fetch_url",
    "summarize_search_results",
]
