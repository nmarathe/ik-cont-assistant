"""Unit tests for AgentState helpers."""

from ai_content_assistant.workflow.state_management import (
    append_to_history,
    create_initial_state,
)


def test_create_initial_state():
    state = create_initial_state("hello world")
    assert state["user_message"] == "hello world"
    assert state["conversation_history"] == []
    assert state["next_agent"] is None
    assert state["error"] is None


def test_append_to_history_adds_message():
    state = create_initial_state("test")
    updated = append_to_history(state, "user", "hello")
    assert len(updated["conversation_history"]) == 1
    assert updated["conversation_history"][0]["role"] == "user"
    assert updated["conversation_history"][0]["content"] == "hello"


def test_append_to_history_caps_at_five():
    state = create_initial_state("test")
    for i in range(8):
        state = append_to_history(state, "user", f"message {i}")
    assert len(state["conversation_history"]) == 5
    assert state["conversation_history"][-1]["content"] == "message 7"


def test_append_to_history_does_not_mutate_original():
    state = create_initial_state("test")
    original_history = state["conversation_history"]
    append_to_history(state, "user", "new message")
    assert state["conversation_history"] is original_history
