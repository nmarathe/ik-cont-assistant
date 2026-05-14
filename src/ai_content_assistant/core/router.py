"""Routing functions for LangGraph conditional edges.

Design: LangGraph requires conditional edges to return a string (the next node name).
These functions encapsulate routing logic at key decision points in the workflow.
A whitelist of valid nodes prevents invalid routing from typos or unexpected state.
Error checks at each routing point ensure failures gracefully exit to error_handler."""

import logging
from langgraph.graph import END
from ai_content_assistant.workflow.state_management import AgentState

logger = logging.getLogger(__name__)

# Whitelist of valid agent node names. Prevents typos/invalid routing from breaking the graph.
_VALID_NODES = {"research", "blog", "linkedin", "image", "content_strategist"}


def route_after_query_handler(state: AgentState) -> str:
    """Route from query handler to the appropriate content agent.

    Validates next_agent against the whitelist. Defaults to research if
    next_agent is missing or invalid (graceful degradation). If an error
    occurred during query classification, route to error_handler instead.
    """
    agent = state.get("next_agent", "research")
    if agent not in _VALID_NODES:
        logger.warning("Unknown next_agent '%s'; routing to research", agent)
        return "research"
    if state.get("error"):
        return "error_handler"
    return str(agent)


def route_after_research(state: AgentState) -> str:
    """Route after research completes.

    If content_type is "strategy", pass research output to content_strategist
    for formatting into a strategic content plan. Otherwise end (research result
    is the final output). Error checks before each routing decision.
    """
    if state.get("error"):
        return "error_handler"
    if state.get("content_type") == "strategy":
        return "content_strategist"
    return END


def handle_error(state: AgentState) -> AgentState:
    """Format errors into a user-friendly final_content message.

    Catches errors from any agent and surfaces them gracefully to the user.
    Clears the error flag so the workflow can terminate cleanly.
    """
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
