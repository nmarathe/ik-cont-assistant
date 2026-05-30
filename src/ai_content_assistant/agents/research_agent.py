"""Deep Research Agent — web search + GPT synthesis with result caching."""

import hashlib
import logging
from typing import Any

from cachetools import TTLCache

from ai_content_assistant.agents.research_prompts import QUERY_EXTRACTION_SYSTEM, SYNTHESIS_SYSTEM
from ai_content_assistant.core.config import settings
from ai_content_assistant.integrations.openai_client import openai_client
from ai_content_assistant.integrations.perplexity_client import perplexity_client
from ai_content_assistant.integrations.serp_client import serp_client
from ai_content_assistant.workflow.state_management import AgentState

logger = logging.getLogger(__name__)

# Module-level cache: synthesis_key → synthesised_text (TTL=1 hr, max 200 entries)
_synthesis_cache: TTLCache[str, str] = TTLCache(maxsize=200, ttl=3600)


class ResearchAgent:
    """Conducts web research and synthesises findings into a structured report."""

    async def extract_search_query(self, user_message: str) -> str:
        """Distill a raw user message into a clean SERP query using the fast model."""
        content, _ = await openai_client.chat_complete(
            messages=[
                {"role": "system", "content": QUERY_EXTRACTION_SYSTEM},
                {"role": "user", "content": user_message},
            ],
            model=settings.fast_model,
            temperature=0.0,
            max_tokens=30,
        )
        query = content.strip()
        logger.debug("ResearchAgent: extracted query=%r from message=%r", query, user_message[:60])
        return query or user_message

    async def search(self, query: str) -> list[dict[str, Any]]:
        """Try SERP first; fall back to Perplexity on failure."""
        try:
            results = await serp_client.search(query)
            if results:
                return results
        except Exception as exc:
            logger.warning("SERP search failed (%s); falling back to Perplexity", exc)

        answer, urls = await perplexity_client.research(query)
        if answer:
            return [{"title": "Perplexity Research", "url": u, "snippet": answer[:300]} for u in (urls or [""])]
        return []

    async def synthesize(self, query: str, results: list[dict[str, Any]]) -> str:
        """Synthesize search results into a report; cached by result-set hash."""
        cache_key = hashlib.md5(
            query.encode() + "".join(r.get("url", "") for r in results).encode()
        ).hexdigest()

        if cache_key in _synthesis_cache:
            logger.debug("Synthesis cache hit")
            return _synthesis_cache[cache_key]

        formatted = "\n\n".join(
            f"[{i + 1}] {r['title']}\nURL: {r['url']}\n{r['snippet']}"
            for i, r in enumerate(results)
        )
        user_msg = f"Research query: {query}\n\nSearch results:\n{formatted}"

        content, _ = await openai_client.chat_complete(
            messages=[
                {"role": "system", "content": SYNTHESIS_SYSTEM},
                {"role": "user", "content": user_msg},
            ],
            model=settings.default_model,
            temperature=0.3,
            max_tokens=1500,
        )
        _synthesis_cache[cache_key] = content
        return content

    async def run(self, state: AgentState) -> AgentState:
        """Search and synthesize; reuse existing research on follow-up."""
        meta = state.get("metadata") or {}
        if meta.get("is_followup") and state.get("research_output"):
            logger.info("ResearchAgent: reusing existing research for follow-up")
            return state

        query = await self.extract_search_query(state["user_message"])
        logger.info("ResearchAgent searching: %s", query)

        results = await self.search(query)
        sources = [r.get("url", "") for r in results if r.get("url")]
        report = await self.synthesize(query, results)

        return {**state, "research_output": report, "sources": sources}
