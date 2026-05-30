"""Query Handler Agent — classifies intent and routes to the right agent."""

import asyncio
import json
import logging

from ai_content_assistant.agents.query_prompts import CLASSIFICATION_SYSTEM, FOLLOWUP_SYSTEM
from ai_content_assistant.core.config import settings
from ai_content_assistant.integrations.openai_client import openai_client
from ai_content_assistant.workflow.state_management import AgentState

logger = logging.getLogger(__name__)

_VALID_AGENTS = {"research", "blog", "linkedin", "image", "strategy"}


class QueryHandler:
    """Classifies the user request and sets state['next_agent']."""

    async def classify_intent(self, user_message: str) -> str:
        """Return the target agent name for the given message."""
        content, _ = await openai_client.chat_complete(
            messages=[
                {"role": "system", "content": CLASSIFICATION_SYSTEM},
                {"role": "user", "content": user_message},
            ],
            model=settings.fast_model,
            temperature=0.0,
            max_tokens=10,
            json_mode=True,
        )
        try:
            intent = json.loads(content).get("intent", "research")
        except (json.JSONDecodeError, AttributeError):
            logger.warning("QueryHandler: failed to parse intent from: %s", content)
            intent = "research"

        return intent if intent in _VALID_AGENTS else "research"

    async def detect_followup(self, state: AgentState) -> bool:
        """Return True if the current message is a refinement of the prior turn."""
        history = state["conversation_history"]
        if not history:
            return False

        context = "\n".join(f"{m['role']}: {m['content']}" for m in history[-3:])
        content, _ = await openai_client.chat_complete(
            messages=[
                {"role": "system", "content": FOLLOWUP_SYSTEM},
                {"role": "user", "content": f"Conversation so far:\n{context}\n\nNew message: {state['user_message']}"},
            ],
            model=settings.fast_model,
            temperature=0.0,
            max_tokens=20,
            json_mode=True,
        )
        try:
            return bool(json.loads(content).get("is_followup", False))
        except (json.JSONDecodeError, AttributeError):
            return False

    async def run(self, state: AgentState) -> AgentState:
        """Classify intent, detect follow-ups, set next_agent and content_type."""
        logger.info("QueryHandler processing: %s", state["user_message"][:80])
        intent, is_followup = await asyncio.gather(
            self.classify_intent(state["user_message"]),
            self.detect_followup(state),
        )

        # Map strategy intent to content_strategist node
        next_agent = "content_strategist" if intent == "strategy" else intent
        logger.info("QueryHandler → next_agent=%s is_followup=%s", next_agent, is_followup)

        return {
            **state,
            "next_agent": next_agent,
            "content_type": intent,  # type: ignore[typeddict-item]
            "metadata": {**(state.get("metadata") or {}), "is_followup": is_followup},
        }
