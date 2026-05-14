"""Content Strategist Agent — formats research into strategic content and plans."""

import logging
from typing import Optional

from ai_content_assistant.agents.strategist_prompts import CONTENT_PLAN_SYSTEM, FORMAT_RESEARCH_SYSTEM
from ai_content_assistant.core.config import settings
from ai_content_assistant.integrations.openai_client import openai_client
from ai_content_assistant.workflow.state_management import AgentState

logger = logging.getLogger(__name__)


class ContentStrategist:
    """Transforms research or topic requests into strategic content documents."""

    async def format_research(self, raw: str) -> str:
        """Structure raw research into strategic Markdown."""
        content, _ = await openai_client.chat_complete(
            messages=[
                {"role": "system", "content": FORMAT_RESEARCH_SYSTEM},
                {"role": "user", "content": raw[:4000]},
            ],
            model=settings.default_model,
            temperature=0.4,
            max_tokens=1500,
        )
        return content

    async def create_content_plan(self, topic: str, research: Optional[str] = None) -> str:
        """Generate a content calendar and strategy document."""
        user_msg = f"Topic: {topic}"
        if research:
            user_msg += f"\n\nResearch context:\n{research[:2000]}"

        content, _ = await openai_client.chat_complete(
            messages=[
                {"role": "system", "content": CONTENT_PLAN_SYSTEM},
                {"role": "user", "content": user_msg},
            ],
            model=settings.default_model,
            temperature=0.4,
            max_tokens=1500,
        )
        return content

    async def run(self, state: AgentState) -> AgentState:
        """Generate strategic content; use research if available."""
        topic = state["user_message"]
        logger.info("ContentStrategist processing: %s", topic[:80])

        if state.get("research_output"):
            output = await self.format_research(state["research_output"])
        else:
            output = await self.create_content_plan(topic, state.get("research_output"))

        return {**state, "final_content": output}
