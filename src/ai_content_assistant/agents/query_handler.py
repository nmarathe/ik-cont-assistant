"""Query Handler Agent — classifies intent and routes to the right agent."""

import asyncio
import json
import logging

from ai_content_assistant.agents.query_prompts import (
    CLASSIFICATION_SYSTEM,
    FOLLOWUP_SYSTEM,
    RESOLVE_FOLLOWUP_SYSTEM,
)
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
                {
                    "role": "user",
                    "content": f"Conversation so far:\n{context}\n\nNew message: {state['user_message']}",
                },
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

    async def resolve_followup(self, state: AgentState) -> str:
        """Rewrite a follow-up message into a self-contained request using history."""
        history = state["conversation_history"]
        context = "\n".join(f"{m['role']}: {m['content']}" for m in history[-3:])
        content, _ = await openai_client.chat_complete(
            messages=[
                {"role": "system", "content": RESOLVE_FOLLOWUP_SYSTEM},
                {
                    "role": "user",
                    "content": f"Conversation so far:\n{context}\n\nFollow-up message: {state['user_message']}",
                },
            ],
            model=settings.fast_model,
            temperature=0.0,
            max_tokens=200,
        )
        return content.strip()

    async def run(self, state: AgentState) -> AgentState:
        """Classify intent, detect follow-ups, set next_agent and content_type."""
        logger.info("QueryHandler processing: %s", state["user_message"][:80])

        hint = (state.get("metadata") or {}).get("content_type_hint", "")
        if hint in _VALID_AGENTS:
            intent = hint
            is_followup = await self.detect_followup(state)
            logger.info("QueryHandler honoring sidebar hint: %s", intent)
        else:
            intent, is_followup = await asyncio.gather(
                self.classify_intent(state["user_message"]),
                self.detect_followup(state),
            )

        # Resolve follow-up references so downstream agents get a self-contained message
        user_message = state["user_message"]
        if is_followup and state.get("conversation_history"):
            user_message = await self.resolve_followup(state)
            logger.info(
                "QueryHandler resolved follow-up: %r → %r",
                state["user_message"][:60],
                user_message[:60],
            )

        # Map strategy intent to content_strategist node
        next_agent = "content_strategist" if intent == "strategy" else intent
        logger.info(
            "QueryHandler → next_agent=%s is_followup=%s", next_agent, is_followup
        )

        return {
            **state,
            "user_message": user_message,
            "next_agent": next_agent,
            "content_type": intent,  # type: ignore[typeddict-item]
            "metadata": {**(state.get("metadata") or {}), "is_followup": is_followup},
        }
