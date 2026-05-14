"""Chat panel components — history display and input area."""

from typing import Optional

import streamlit as st


def render_chat_history(messages: list[dict]) -> None:
    """Render conversation history using st.chat_message."""
    for msg in messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])


def render_input_area() -> Optional[str]:
    """Render the chat input and return submitted text, or None."""
    return st.chat_input("Ask me to write a blog, LinkedIn post, research a topic, or generate an image...")
