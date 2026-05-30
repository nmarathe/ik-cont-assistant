"""Thin facade over the LangGraph workflow — called by the Streamlit app."""

import logging

from ai_content_assistant.workflow.langgraph_workflow import run_workflow, stream_workflow
from ai_content_assistant.workflow.state_management import AgentState

logger = logging.getLogger(__name__)


async def process_request(user_message: str, session_state: dict) -> AgentState:
    """
    Run the multi-agent workflow for a user message.

    Threads conversation history and sidebar settings from Streamlit session_state.
    """
    history = session_state.get("messages", [])[-5:]
    metadata = {
        "tone": session_state.get("tone", "professional"),
        "word_count": session_state.get("word_count", 2000),
        "keywords": session_state.get("keywords", ""),
        "content_type_hint": session_state.get("content_type", ""),
    }
    logger.info("process_request: message=%s", user_message[:80])
    return await run_workflow(
        user_message=user_message,
        conversation_history=history,
        metadata=metadata,
    )


async def stream_request(user_message: str, session_state: dict):
    """Async generator streaming (node_name, state_delta) as each node completes."""
    history = session_state.get("messages", [])[-5:]
    metadata = {
        "tone": session_state.get("tone", "professional"),
        "word_count": session_state.get("word_count", 2000),
        "keywords": session_state.get("keywords", ""),
        "content_type_hint": session_state.get("content_type", ""),
    }
    async for node, delta in stream_workflow(user_message, history, metadata):
        yield node, delta
