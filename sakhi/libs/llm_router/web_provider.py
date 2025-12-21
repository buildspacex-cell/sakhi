from __future__ import annotations

import logging
import os
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class WebProvider:
    """Lightweight web search provider with DuckDuckGo fallback and optional Brave."""

    def __init__(self) -> None:
        self.timeout = 20.0
        self.brave_key = os.getenv("BRAVE_API_KEY")

    async def search(self, query: str) -> str:
        if self.brave_key:
            return await self._brave_search(query)
        return await self._duckduckgo_search(query)

    async def _duckduckgo_search(self, query: str) -> str:
        url = "https://api.duckduckgo.com/"
        params = {"q": query, "format": "json", "no_redirect": 1, "no_html": 1}
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                data: dict[str, Any] = response.json()
        except Exception as exc:  # pragma: no cover - network path
            logger.warning("duckduckgo search error: %s", exc)
            return "Web search temporarily unavailable."

        abstract = (data.get("AbstractText") or "").strip()
        heading = (data.get("Heading") or "").strip()
        bullets = [
            item.get("Text", "").strip()
            for item in data.get("RelatedTopics", [])
            if isinstance(item, dict) and item.get("Text")
        ]
        parts = [p for p in (heading, abstract) if p]
        if bullets:
            parts.append("\n".join(bullets[:5]))
        text = "\n\n".join(parts).strip()
        return text or "No clear summary found."

    async def _brave_search(self, query: str) -> str:
        url = "https://api.search.brave.com/res/v1/web/search"
        headers = {"X-Subscription-Token": self.brave_key}
        params = {"q": query, "count": 5, "country": "in", "safesearch": "moderate"}
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, headers=headers, params=params)
                response.raise_for_status()
                data: dict[str, Any] = response.json()
        except Exception as exc:  # pragma: no cover - network path
            logger.warning("brave search error: %s", exc)
            return "Web search temporarily unavailable."

        results = (data.get("web", {}) or {}).get("results", []) or []
        lines: list[str] = []
        for item in results[:5]:
            if not isinstance(item, dict):
                continue
            title = (item.get("title") or "").strip()
            description = (item.get("description") or "").strip()
            source = (item.get("source") or item.get("url") or "").strip()
            if title or description:
                lines.append(f"{title}\n{description}\n— {source}")
        return "\n\n".join(lines).strip() or "No clear results."


__all__ = ["WebProvider"]
