"""LinkedIn Post Writer Agent — generates posts with hashtags and tone variants."""

import json
import logging
from typing import Optional

from ai_content_assistant.agents.linkedin_prompts import HASHTAG_SYSTEM, LINKEDIN_SYSTEM, VARIANTS_SYSTEM
from ai_content_assistant.core.config import settings
from ai_content_assistant.integrations.openai_client import openai_client
from ai_content_assistant.workflow.state_management import AgentState

logger = logging.getLogger(__name__)


def _truncate_to_last_sentence(text: str, max_chars: int) -> str:
    """Truncate to max_chars at the last sentence boundary."""
    if len(text) <= max_chars:
        return text
    truncated = text[:max_chars]
    last_period = max(truncated.rfind(". "), truncated.rfind(".\n"), truncated.rfind("!"), truncated.rfind("?"))
    return truncated[: last_period + 1] if last_period > 0 else truncated


class LinkedInWriter:
    """Generates LinkedIn posts optimized for professional engagement."""

    async def write_post(self, topic: str, tone: str = "professional") -> str:
        """Generate a single LinkedIn post with the given tone."""
        system = LINKEDIN_SYSTEM.format(tone=tone, max_chars=settings.linkedin_max_chars)
        content, _ = await openai_client.chat_complete(
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": f"Topic: {topic}"},
            ],
            model=settings.default_model,
            temperature=0.7,
            max_tokens=600,
        )
        return _truncate_to_last_sentence(content, settings.linkedin_max_chars)

    async def generate_hashtags(self, topic: str) -> list[str]:
        """Return 5-8 relevant hashtags using the fast model."""
        text, _ = await openai_client.chat_complete(
            messages=[
                {"role": "system", "content": HASHTAG_SYSTEM},
                {"role": "user", "content": f"Topic: {topic}"},
            ],
            model=settings.fast_model,
            temperature=0.5,
            max_tokens=100,
            json_mode=True,
        )
        try:
            return json.loads(text).get("hashtags", [])
        except json.JSONDecodeError:
            return []

    async def generate_variants(self, topic: str) -> dict:
        """Generate all 3 tone variants in a single GPT call."""
        text, _ = await openai_client.chat_complete(
            messages=[
                {"role": "system", "content": VARIANTS_SYSTEM},
                {"role": "user", "content": f"Topic: {topic}"},
            ],
            model=settings.default_model,
            temperature=0.7,
            max_tokens=1500,
            json_mode=True,
        )
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            logger.warning("LinkedInWriter: failed to parse variants JSON")
            return {}

    async def run(self, state: AgentState) -> AgentState:
        """Generate LinkedIn post, hashtags, and tone variants."""
        topic = state["user_message"]
        tone = (state.get("metadata") or {}).get("tone", "professional")
        logger.info("LinkedInWriter generating post for: %s (tone=%s)", topic[:80], tone)

        post, hashtags, variants = await _gather(
            self.write_post(topic, tone),
            self.generate_hashtags(topic),
            self.generate_variants(topic),
        )

        hashtag_str = " ".join(hashtags)
        final = f"{post}\n\n{hashtag_str}" if hashtag_str else post

        return {
            **state,
            "final_content": final,
            "metadata": {
                **(state.get("metadata") or {}),
                "hashtags": hashtags,
                "variants": variants,
            },
        }


async def _gather(*coros):
    """Run coroutines concurrently."""
    import asyncio
    return await asyncio.gather(*coros)
