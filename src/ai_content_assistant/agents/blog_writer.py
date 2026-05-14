"""SEO Blog Writer Agent — produces long-form Markdown blog posts with streaming."""

import json
import logging
from collections.abc import AsyncIterator
from typing import Optional

from ai_content_assistant.agents.blog_prompts import BLOG_SYSTEM, META_SYSTEM
from ai_content_assistant.core.config import settings
from ai_content_assistant.integrations.openai_client import openai_client
from ai_content_assistant.workflow.state_management import AgentState

logger = logging.getLogger(__name__)


class BlogWriter:
    """Generates SEO-optimized blog posts; uses streaming for long output."""

    async def write_blog(
        self, topic: str, research: Optional[str] = None
    ) -> AsyncIterator[str]:
        """Yield streamed Markdown chunks for the blog post."""
        system = BLOG_SYSTEM.format(word_count=settings.blog_target_word_count)
        user_content = f"Topic: {topic}"
        if research:
            user_content += f"\n\nResearch context:\n{research[:3000]}"

        async for chunk in openai_client.chat_stream(
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_content},
            ],
            model=settings.default_model,
            max_tokens=3500,
        ):
            yield chunk

    async def generate_meta(self, content: str) -> dict:
        """Extract SEO metadata from the blog post using the fast model."""
        text, _ = await openai_client.chat_complete(
            messages=[
                {"role": "system", "content": META_SYSTEM},
                {"role": "user", "content": content[:4000]},
            ],
            model=settings.fast_model,
            temperature=0.0,
            max_tokens=200,
            json_mode=True,
        )
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            logger.warning("BlogWriter: failed to parse meta JSON")
            return {"title": "", "meta_description": "", "keywords": [], "slug": ""}

    async def run(self, state: AgentState) -> AgentState:
        """Generate blog post, collect streamed output, attach metadata."""
        topic = state["user_message"]
        logger.info("BlogWriter generating post for: %s", topic[:80])

        chunks: list[str] = []
        async for chunk in self.write_blog(topic, state.get("research_output")):
            chunks.append(chunk)
        blog_content = "".join(chunks)

        meta = await self.generate_meta(blog_content)
        return {
            **state,
            "final_content": blog_content,
            "metadata": {**(state.get("metadata") or {}), **meta},
        }
