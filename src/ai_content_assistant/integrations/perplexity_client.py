"""Perplexity Sonar client via OpenAI-compatible API — used as SERP fallback."""

import logging
import re

import httpx
import certifi
from openai import AsyncOpenAI

from ai_content_assistant.core.config import settings

logger = logging.getLogger(__name__)

_PERPLEXITY_BASE = "https://api.perplexity.ai"
_MODEL = "sonar-pro"


class PerplexityClient:
    """Research client backed by Perplexity Sonar."""

    def __init__(self) -> None:
        self._api_key = settings.perplexity_api_key or "not-configured"

    async def research(self, query: str) -> tuple[str, list[str]]:
        """Return (answer_text, source_urls). Falls back gracefully if key is missing."""
        if not settings.perplexity_api_key:
            logger.warning("Perplexity API key not set; returning empty research")
            return "", []

        logger.info("Perplexity research: %s", query)
        async with httpx.AsyncClient(verify=certifi.where()) as http:
            client = AsyncOpenAI(
                base_url=_PERPLEXITY_BASE,
                api_key=self._api_key,
                http_client=http,
            )
            response = await client.chat.completions.create(
                model=_MODEL,
                messages=[{"role": "user", "content": query}],
                max_tokens=1500,
            )
        answer = response.choices[0].message.content or ""
        urls = self._extract_urls(answer)
        return answer, urls

    def _extract_urls(self, text: str) -> list[str]:
        return re.findall(r"https?://[^\s\)\]\"']+", text)


perplexity_client = PerplexityClient()
