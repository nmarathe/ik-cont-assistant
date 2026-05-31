"""Unit tests for the Blog Writer agent."""

import json
from unittest.mock import AsyncMock, patch

import pytest

from ai_content_assistant.agents.blog_writer import BlogWriter
from ai_content_assistant.workflow.state_management import create_initial_state

_SAMPLE_BLOG = """---
title: "Test Blog"
meta_description: "A test post"
keywords: [ai, test]
slug: test-blog
---

# Test Blog

## Introduction
This is a test blog post about AI. """ + "word " * 1500


async def _mock_stream(*args, **kwargs):
    yield _SAMPLE_BLOG


@pytest.fixture
def writer():
    return BlogWriter()


async def test_blog_writer_populates_final_content(writer):
    with patch(
        "ai_content_assistant.agents.blog_writer.openai_client.chat_stream",
        side_effect=_mock_stream,
    ), patch(
        "ai_content_assistant.agents.blog_writer.openai_client.chat_complete",
        new_callable=AsyncMock,
        return_value=(
            json.dumps({"title": "Test", "meta_description": "desc", "keywords": ["ai"], "slug": "test"}),
            {},
        ),
    ):
        state = create_initial_state("Write a blog about AI")
        result = await writer.run(state)

    assert result["final_content"] is not None
    assert len(result["final_content"]) > 0
    assert result["metadata"]["title"] == "Test"


@pytest.mark.parametrize("tone", ["formal", "professional", "conversational", "casual"])
async def test_blog_writer_uses_every_tone(writer, tone):
    """Every Tone selector value must be injected into the blog system prompt."""
    captured: dict = {}

    async def _capture_stream(messages, model=None, max_tokens=None):
        captured["system"] = messages[0]["content"]
        yield _SAMPLE_BLOG

    with patch(
        "ai_content_assistant.agents.blog_writer.openai_client.chat_stream",
        side_effect=_capture_stream,
    ), patch(
        "ai_content_assistant.agents.blog_writer.openai_client.chat_complete",
        new_callable=AsyncMock,
        return_value=(json.dumps({"title": "T", "meta_description": "d", "keywords": ["ai"], "slug": "t"}), {}),
    ):
        state = create_initial_state("Write a blog about AI")
        state["metadata"] = {"tone": tone, "word_count": 1500, "keywords": "ai"}
        result = await writer.run(state)

    assert f"Tone: {tone}" in captured["system"]
    assert result["final_content"]


async def test_blog_writer_generates_meta(writer):
    with patch(
        "ai_content_assistant.agents.blog_writer.openai_client.chat_complete",
        new_callable=AsyncMock,
        return_value=(
            json.dumps({"title": "AI Guide", "meta_description": "Intro to AI", "keywords": ["ai"], "slug": "ai-guide"}),
            {},
        ),
    ):
        meta = await writer.generate_meta("sample blog content here")

    assert meta["title"] == "AI Guide"
    assert meta["slug"] == "ai-guide"
