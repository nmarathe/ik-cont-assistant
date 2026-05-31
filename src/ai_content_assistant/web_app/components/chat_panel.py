"""Chat panel components — history display and input area."""

import json
from typing import Optional

import streamlit as st
import streamlit.components.v1 as components


def render_chat_history(messages: list[dict]) -> None:
    """Render conversation history using st.chat_message."""
    for msg in messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])


def render_input_area() -> Optional[str]:
    """Render the chat input and return submitted text, or None.

    `st.chat_input` cannot be pre-filled natively, so when a prior prompt is queued
    in ``st.session_state.carry_forward`` we inject it into the widget's textarea —
    the prompt is carried forward and auto-populated, ready to be re-submitted.
    """
    submitted = st.chat_input(
        "Ask me to write a blog, LinkedIn post, research a topic, or generate an image..."
    )

    carry = st.session_state.get("carry_forward")
    if carry:
        _prefill_chat_input(carry)
        st.session_state.carry_forward = ""  # inject once, don't fight user edits

    return submitted


def _prefill_chat_input(text: str) -> None:
    """Inject JS that populates Streamlit's chat-input textarea with ``text``."""
    payload = json.dumps(text)
    components.html(
        f"""
        <script>
        const doc = window.parent.document;
        const ta = doc.querySelector('[data-testid="stChatInputTextArea"]')
                || doc.querySelector('[data-testid="stChatInput"] textarea');
        if (ta) {{
            const setter = Object.getOwnPropertyDescriptor(
                window.parent.HTMLTextAreaElement.prototype, 'value').set;
            setter.call(ta, {payload});
            ta.dispatchEvent(new Event('input', {{ bubbles: true }}));
            ta.focus();
        }}
        </script>
        """,
        height=0,
    )
