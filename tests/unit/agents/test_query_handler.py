"""Unit tests for the Query Handler agent."""

import json
from unittest.mock import AsyncMock, patch

import pytest

from ai_content_assistant.agents.query_handler import QueryHandler
from ai_content_assistant.workflow.state_management import create_initial_state


@pytest.fixture
def handler():
    return QueryHandler()


@pytest.fixture
def mock_chat_complete():
    with patch(
        "ai_content_assistant.agents.query_handler.openai_client.chat_complete",
        new_callable=AsyncMock,
    ) as mock:
        yield mock


async def test_classify_intent_blog(handler, mock_chat_complete):
    mock_chat_complete.return_value = (json.dumps({"intent": "blog"}), {})
    result = await handler.classify_intent("Write a blog about AI")
    assert result == "blog"


async def test_classify_intent_defaults_to_research_on_unknown(handler, mock_chat_complete):
    mock_chat_complete.return_value = (json.dumps({"intent": "unknown_thing"}), {})
    result = await handler.classify_intent("do something random")
    assert result == "research"


async def test_classify_intent_defaults_to_research_on_parse_error(handler, mock_chat_complete):
    mock_chat_complete.return_value = ("not json at all", {})
    result = await handler.classify_intent("something")
    assert result == "research"


async def test_run_sets_next_agent(handler, mock_chat_complete):
    mock_chat_complete.return_value = (json.dumps({"intent": "linkedin"}), {})
    state = create_initial_state("Write a LinkedIn post")
    result = await handler.run(state)
    assert result["next_agent"] == "linkedin"
    assert result["content_type"] == "linkedin"


async def test_run_maps_strategy_to_content_strategist(handler, mock_chat_complete):
    mock_chat_complete.return_value = (json.dumps({"intent": "strategy"}), {})
    state = create_initial_state("Create a content calendar")
    result = await handler.run(state)
    assert result["next_agent"] == "content_strategist"
    assert result["content_type"] == "strategy"
