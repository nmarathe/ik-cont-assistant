"""Shared AgentState TypedDict and helpers used across all agents."""

from typing import Annotated, Literal, Optional
from typing_extensions import TypedDict

ContentType = Literal["blog", "linkedin", "image", "research", "strategy"]

# Sliding-window cap: limits how many turns are sent as LLM context to avoid
# runaway token costs on long sessions.
_MAX_HISTORY = 5


class ConversationMessage(TypedDict):
    role: str
    content: str


def _merge_history(
    existing: list[ConversationMessage],
    new: list[ConversationMessage],
) -> list[ConversationMessage]:
    """Reducer: append incoming messages and enforce the sliding-window cap."""
    return (existing + new)[-_MAX_HISTORY:]


class AgentState(TypedDict):
    user_message: str
    # LangGraph calls _merge_history(old, delta) automatically on each update,
    # so agents return only the new messages, not the full list.
    conversation_history: Annotated[list[ConversationMessage], _merge_history]
    # Consumed by LangGraph's conditional router to select the next node.
    next_agent: Optional[str]
    # Written by ResearchAgent; read by BlogWriter, ContentStrategist, etc.
    research_output: Optional[str]
    sources: Optional[list[str]]
    # Terminal field — whichever agent runs last writes the user-facing output here.
    final_content: Optional[str]
    content_type: Optional[ContentType]
    # Any agent can set this; the error-handler node checks it to short-circuit routing.
    error: Optional[str]
    # Catch-all for agent-specific extras: SEO meta, image URL, hashtags, etc.
    metadata: Optional[dict]


def create_initial_state(user_message: str) -> AgentState:
    """Return a fresh AgentState for a new user message."""
    return AgentState(
        user_message=user_message,
        conversation_history=[],
        next_agent=None,
        research_output=None,
        sources=None,
        final_content=None,
        content_type=None,
        error=None,
        metadata=None,
    )
