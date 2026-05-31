"""Unit tests for the LinkedIn Writer agent."""

import json
from unittest.mock import patch

import pytest

from ai_content_assistant.agents.linkedin_writer import LinkedInWriter
from ai_content_assistant.workflow.state_management import create_initial_state


@pytest.fixture
def writer():
    return LinkedInWriter()


def _make_chat(captured: dict):
    """Return a chat_complete stub that records the post system prompt."""

    async def _chat(messages, model=None, temperature=0.7, max_tokens=1000, json_mode=False):
        system = messages[0]["content"]
        if "LinkedIn content expert" in system:
            captured["system"] = system
            return ("Hook line.\n\nValue body.\n\nCTA.", {})
        if json_mode:
            return (
                json.dumps(
                    {
                        "hashtags": ["#AI", "#Tech", "#Marketing", "#Content", "#SEO"],
                        "professional": "p",
                        "conversational": "c",
                        "thought_leadership": "t",
                    }
                ),
                {},
            )
        return ("text", {})

    return _chat


@pytest.mark.parametrize("tone", ["formal", "professional", "conversational", "casual"])
async def test_linkedin_writer_uses_every_tone(writer, tone):
    """Every Tone selector value must be injected into the LinkedIn system prompt."""
    captured: dict = {}
    with patch(
        "ai_content_assistant.agents.linkedin_writer.openai_client.chat_complete",
        side_effect=_make_chat(captured),
    ):
        state = create_initial_state("LinkedIn post about AI")
        state["metadata"] = {"tone": tone}
        result = await writer.run(state)

    assert f"Tone: {tone}" in captured["system"]
    assert result["final_content"]
    assert result["metadata"]["hashtags"]


async def test_linkedin_writer_defaults_to_professional(writer):
    """With no tone in metadata, the writer falls back to professional."""
    captured: dict = {}
    with patch(
        "ai_content_assistant.agents.linkedin_writer.openai_client.chat_complete",
        side_effect=_make_chat(captured),
    ):
        state = create_initial_state("LinkedIn post about AI")
        await writer.run(state)

    assert "Tone: professional" in captured["system"]
