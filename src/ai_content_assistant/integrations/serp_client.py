"""SERP API client with in-memory TTL caching."""

import hashlib
import logging
from typing import Any

import httpx
from cachetools import TTLCache

from ai_content_assistant.core.config import settings

logger = logging.getLogger(__name__)


class SearchResult(dict):
    """TypedDict-compatible dict with title, url, snippet keys."""


class SerpClient:
    """Async SERP API wrapper with 1-hour result caching."""

    _BASE_URL = "https://serpapi.com/search.json"
    _TIMEOUT = 30.0

    def __init__(self) -> None:
        self._cache: TTLCache[str, list[dict[str, Any]]] = TTLCache(
            maxsize=100, ttl=3600
        )

    def _cache_key(self, query: str, num_results: int) -> str:
        raw = f"{query}:{num_results}"
        return hashlib.md5(raw.encode()).hexdigest()

    async def search(
        self, query: str, num_results: int | None = None
    ) -> list[dict[str, Any]]:
        """Return a list of {title, url, snippet} dicts."""
        n = num_results or settings.max_research_results
        key = self._cache_key(query, n)

        if key in self._cache:
            logger.debug("SERP cache hit for query: %s", query)
            return self._cache[key]

        logger.info("SERP API search: %s", query)
        params = {
            "q": query,
            "num": n,
            "api_key": settings.serp_api_key,
            "engine": "google",
        }
        async with httpx.AsyncClient(timeout=self._TIMEOUT, verify=False) as client:
            response = await client.get(self._BASE_URL, params=params)
            response.raise_for_status()
            data = response.json()

        results = [
            {
                "title": r.get("title", ""),
                "url": r.get("link", ""),
                "snippet": r.get("snippet", ""),
            }
            for r in data.get("organic_results", [])[:n]
        ]
        self._cache[key] = results
        return results


serp_client = SerpClient()
