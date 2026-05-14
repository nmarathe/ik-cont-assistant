"""Routing functions for LangGraph conditional edges."""

import logging

from langgraph.graph import END

from ai_content_assistant.workflow.state_management import AgentState

logger = logging.getLogger(__name__)

_VALID_NODES = {"research", "blog", "linkedin", "image", "content_strategist"}


def route_after_query_handler(state: AgentState) -> str:
    """Map next_agent value to a graph node name."""
    agent = state.get("next_agent", "research")
    if agent not in _VALID_NODES:
        logger.warning("Unknown next_agent '%s'; routing to research", agent)
        return "research"
    if state.get("error"):
        return "error_handler"
    return str(agent)


def route_after_research(state: AgentState) -> str:
    """After research: go to content_strategist for strategy type, else end."""
    if state.get("error"):
        return "error_handler"
    if state.get("content_type") == "strategy":
        return "content_strategist"
    return END


def handle_error(state: AgentState) -> AgentState:
    """Format the error into a user-friendly final_content message."""
    error = state.get("error", "An unexpected error occurred.")
    logger.error("Workflow error: %s", error)
    return {
        **state,
        "final_content": (
            f"I'm sorry, I ran into an issue processing your request.\n\n"
            f"**Error:** {error}\n\n"
            "Please try again or rephrase your request."
        ),
        "error": None,
    }
