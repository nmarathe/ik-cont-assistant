"""LangGraph StateGraph definition — wires all agents into a compiled workflow."""

import logging
from typing import Optional

from langgraph.graph import END, START, StateGraph

from ai_content_assistant.agents.blog_writer import BlogWriter
from ai_content_assistant.agents.content_strategist import ContentStrategist
from ai_content_assistant.agents.image_generator import ImageGenerator
from ai_content_assistant.agents.linkedin_writer import LinkedInWriter
from ai_content_assistant.agents.query_handler import QueryHandler
from ai_content_assistant.agents.research_agent import ResearchAgent
from ai_content_assistant.core.router import (
    handle_error,
    route_after_query_handler,
    route_after_research,
)
from ai_content_assistant.workflow.state_management import AgentState

logger = logging.getLogger(__name__)

_compiled_graph: Optional[object] = None


def _make_node(agent_instance):
    """Wrap an agent's run() in a try/except that sets state['error'] on failure."""

    async def node(state: AgentState) -> AgentState:
        try:
            return await agent_instance.run(state)
        except Exception as exc:
            logger.error(
                "%s failed: %s", type(agent_instance).__name__, exc, exc_info=True
            )
            return {**state, "error": f"{type(exc).__name__}: {exc}"}

    node.__name__ = type(agent_instance).__name__
    return node


def build_graph():
    """Build and compile the LangGraph StateGraph."""
    query_handler = QueryHandler()
    research_agent = ResearchAgent()
    blog_writer = BlogWriter()
    linkedin_writer = LinkedInWriter()
    image_generator = ImageGenerator()
    content_strategist = ContentStrategist()

    graph = StateGraph(AgentState)

    # Nodes
    graph.add_node("query_handler", _make_node(query_handler))
    graph.add_node("research", _make_node(research_agent))
    graph.add_node("blog", _make_node(blog_writer))
    graph.add_node("linkedin", _make_node(linkedin_writer))
    graph.add_node("image", _make_node(image_generator))
    graph.add_node("content_strategist", _make_node(content_strategist))
    graph.add_node("error_handler", handle_error)

    # Entry
    graph.add_edge(START, "query_handler")

    # After classification: conditional routing
    graph.add_conditional_edges(
        "query_handler",
        route_after_query_handler,
        {
            "research": "research",
            "blog": "blog",
            "linkedin": "linkedin",
            "image": "image",
            "content_strategist": "content_strategist",
            "error_handler": "error_handler",
        },
    )

    # After research: optionally route to strategist
    graph.add_conditional_edges(
        "research",
        route_after_research,
        {
            "content_strategist": "content_strategist",
            "error_handler": "error_handler",
            END: END,
        },
    )

    # Terminal nodes
    for node in ("blog", "linkedin", "image", "content_strategist", "error_handler"):
        graph.add_edge(node, END)

    return graph.compile()


def get_graph():
    """Lazy singleton accessor for the compiled graph."""
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_graph()
    return _compiled_graph


async def stream_workflow(
    user_message: str,
    conversation_history: list | None = None,
    metadata: dict | None = None,
):
    """Async generator yielding (node_name, state_delta) as each node completes."""
    initial_state = AgentState(
        user_message=user_message,
        conversation_history=conversation_history or [],
        next_agent=None,
        research_output=None,
        sources=None,
        final_content=None,
        content_type=None,
        error=None,
        metadata=metadata or {},
    )
    graph = get_graph()
    async for chunk in graph.astream(initial_state, stream_mode="updates"):
        for node_name, state_delta in chunk.items():
            yield node_name, state_delta


async def run_workflow(
    user_message: str,
    conversation_history: list | None = None,
    metadata: dict | None = None,
) -> AgentState:
    """Run the full workflow for a user message and return the final state."""
    initial_state = AgentState(
        user_message=user_message,
        conversation_history=conversation_history or [],
        next_agent=None,
        research_output=None,
        sources=None,
        final_content=None,
        content_type=None,
        error=None,
        metadata=metadata or {},
    )
    graph = get_graph()
    result = await graph.ainvoke(initial_state)
    return result
