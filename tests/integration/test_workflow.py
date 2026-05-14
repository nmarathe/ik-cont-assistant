"""Integration tests — full LangGraph workflow with all API clients mocked."""

import json
from unittest.mock import AsyncMock, patch

import pytest

from ai_content_assistant.workflow.langgraph_workflow import run_workflow

_BLOG_CONTENT = "# Test Blog\n\n## Intro\n\n" + "word " * 1600


async def _mock_stream(*args, **kwargs):
    yield _BLOG_CONTENT


@pytest.fixture
def mock_all_clients():
    """Patch all external API calls.

    All modules share the same openai_client singleton, so we patch the method
    once on the shared object using side_effect to handle multiple call sequences.
    """
    _meta = json.dumps({"title": "Test", "meta_description": "desc", "keywords": ["ai"], "slug": "test"})

    async def _chat_complete_side_effect(messages, model=None, temperature=0.7, max_tokens=1000, json_mode=False):
        # Classification call uses max_tokens=10; meta generation uses max_tokens=200
        if max_tokens == 10:
            return (json.dumps({"intent": "blog"}), {})
        return (_meta, {})

    with (
        patch(
            "ai_content_assistant.integrations.openai_client.openai_client.chat_complete",
            side_effect=_chat_complete_side_effect,
        ),
        patch(
            "ai_content_assistant.integrations.openai_client.openai_client.chat_stream",
            side_effect=_mock_stream,
        ),
    ):
        yield


async def test_blog_workflow_end_to_end(mock_all_clients):
    result = await run_workflow("Write a blog post about AI content marketing")
    assert result["final_content"] is not None
    assert result["error"] is None
    assert result["content_type"] == "blog"


async def test_workflow_error_is_handled():
    """Workflow should return an error message rather than raising."""
    with patch(
        "ai_content_assistant.agents.query_handler.openai_client.chat_complete",
        new_callable=AsyncMock,
        side_effect=Exception("API unavailable"),
    ):
        result = await run_workflow("Write something")
        # error_handler converts the error to final_content
        assert result["final_content"] is not None
        assert "error" in result["final_content"].lower() or result["error"] is None


async def test_research_workflow():
    """Research agent runs and sets research_output."""
    with (
        patch(
            "ai_content_assistant.agents.query_handler.openai_client.chat_complete",
            new_callable=AsyncMock,
            return_value=(json.dumps({"intent": "research"}), {}),
        ),
        patch(
            "ai_content_assistant.integrations.serp_client.serp_client.search",
            new_callable=AsyncMock,
            return_value=[
                {"title": "AI News", "url": "https://example.com", "snippet": "AI is growing fast."}
            ],
        ),
        patch(
            "ai_content_assistant.agents.research_agent.openai_client.chat_complete",
            new_callable=AsyncMock,
            return_value=("## Executive Summary\nAI is growing.", {}),
        ),
    ):
        result = await run_workflow("Research AI trends")
        assert result["research_output"] is not None
        assert result["error"] is None
