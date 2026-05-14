"""Main Streamlit application entry point."""

import asyncio
import logging

import nest_asyncio
import streamlit as st

from ai_content_assistant.core.config import configure_logging
from ai_content_assistant.core.workflow import process_request
from ai_content_assistant.web_app.components.chat_panel import render_chat_history, render_input_area
from ai_content_assistant.web_app.components.content_preview import render_preview
from ai_content_assistant.web_app.components.sidebar import render_sidebar
from ai_content_assistant.workflow.state_management import append_to_history

# Allow asyncio.run() inside Streamlit's existing event loop
nest_asyncio.apply()
configure_logging()
logger = logging.getLogger(__name__)


def initialize_session_state() -> None:
    """Set default values for Streamlit session state on first load."""
    defaults = {
        "messages": [],          # conversation history for UI display
        "agent_history": [],     # conversation history passed to agents
        "current_state": None,   # last AgentState result
        "tone": "professional",
        "word_count": 2000,
        "keywords": "",
        "content_type": "",
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def _run_workflow(user_message: str) -> dict:
    """Synchronously invoke the async workflow from Streamlit."""
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(
        process_request(user_message, dict(st.session_state))
    )


def main() -> None:
    st.set_page_config(
        page_title="AI Content Assistant",
        page_icon="🤖",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    initialize_session_state()

    # Sidebar settings
    sidebar_settings = render_sidebar()
    st.session_state.update(sidebar_settings)

    # Header
    st.title("🤖 AI Content Assistant")
    st.caption("Multi-agent AI for research, blog posts, LinkedIn content, and images.")

    # Two-column layout
    chat_col, preview_col = st.columns([1, 1], gap="medium")

    with chat_col:
        st.subheader("Chat")
        render_chat_history(st.session_state.messages)
        user_input = render_input_area()

    with preview_col:
        render_preview(st.session_state.current_state)

    # Process new input
    if user_input:
        # Show user message immediately
        st.session_state.messages.append({"role": "user", "content": user_input})

        with st.spinner("Generating content…"):
            try:
                result = _run_workflow(user_input)
                st.session_state.current_state = result

                # Add assistant response to chat
                assistant_msg = result.get("final_content") or "I couldn't generate a response. Please try again."
                # For non-image content, show a short preview in chat
                if result.get("content_type") == "image":
                    preview_msg = f"✅ Image generated! See the preview panel →\n\n*Prompt used:* {(result.get('metadata') or {}).get('prompt_used', '')[:100]}"
                else:
                    preview_msg = assistant_msg[:300] + ("…" if len(assistant_msg) > 300 else "")

                st.session_state.messages.append({"role": "assistant", "content": preview_msg})

                # Update agent conversation history (last 5)
                agent_hist = append_to_history(
                    {"conversation_history": st.session_state.agent_history,
                     "user_message": user_input,
                     "next_agent": None, "research_output": None,
                     "sources": None, "final_content": None,
                     "content_type": None, "error": None, "metadata": None},
                    "user",
                    user_input,
                )
                agent_hist = append_to_history(agent_hist, "assistant", assistant_msg[:500])
                st.session_state.agent_history = agent_hist["conversation_history"]

            except Exception as exc:
                logger.error("Workflow error: %s", exc, exc_info=True)
                error_msg = f"An error occurred: {exc}"
                st.session_state.messages.append({"role": "assistant", "content": error_msg})

        st.rerun()


if __name__ == "__main__":
    main()
