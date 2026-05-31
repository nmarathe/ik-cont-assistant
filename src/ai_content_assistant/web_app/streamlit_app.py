"""Main Streamlit application entry point."""

import asyncio
import logging
import queue as queue_module
import threading
import time

import streamlit as st

from ai_content_assistant.core.config import configure_logging, settings
from ai_content_assistant.core.workflow import stream_request
from ai_content_assistant.utils.guardrails import (
    ContentFlaggedError,
    InputTooLongError,
    check_input_length,
    check_moderation,
    detect_pii,
)
from ai_content_assistant.web_app.components.chat_panel import (
    render_chat_history,
    render_input_area,
)
from ai_content_assistant.web_app.components.content_preview import render_preview
from ai_content_assistant.web_app.components.sidebar import render_sidebar
from ai_content_assistant.workflow.state_management import append_to_history

configure_logging()
logger = logging.getLogger(__name__)


def initialize_session_state() -> None:
    """Set default values for Streamlit session state on first load."""
    defaults = {
        "messages": [],  # conversation history for UI display
        "agent_history": [],  # conversation history passed to agents
        "current_state": None,  # last AgentState result
        "tone": "professional",
        "word_count": 2000,
        "keywords": "",
        "content_type": "",
        "request_count": 0,
        "rate_window_start": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def _validate_input(text: str) -> bool:
    """Run all pre-workflow guards. Returns False (and shows st.error) if blocked."""
    now = time.time()
    if (
        st.session_state.rate_window_start is None
        or now - st.session_state.rate_window_start > 3600
    ):
        st.session_state.request_count = 0
        st.session_state.rate_window_start = now

    if st.session_state.request_count >= settings.max_requests_per_hour:
        st.error(
            f"Rate limit reached ({settings.max_requests_per_hour} requests/hour). "
            "Please wait before sending another request."
        )
        return False

    try:
        check_input_length(text)
    except InputTooLongError as exc:
        st.error(str(exc))
        return False

    try:
        check_moderation(text)
    except ContentFlaggedError as exc:
        st.error(str(exc))
        return False
    except Exception as exc:
        logger.warning("Moderation check unavailable (%s); continuing", exc)

    pii_types = detect_pii(text)
    if pii_types:
        st.warning(
            f"Your message appears to contain sensitive information "
            f"({', '.join(pii_types)}). It will be sent to external AI services."
        )

    st.session_state.request_count += 1
    return True


def _run_workflow(user_message: str) -> dict:
    """Run the async workflow in a dedicated thread; stream per-node progress."""
    result_queue: queue_module.Queue = queue_module.Queue()
    session_copy = dict(st.session_state)

    async def _collect() -> None:
        final_state: dict = {}
        async for node_name, delta in stream_request(user_message, session_copy):
            result_queue.put(("step", node_name, delta))
            final_state.update(delta)
        result_queue.put(("done", None, final_state))

    threading.Thread(target=lambda: asyncio.run(_collect()), daemon=True).start()

    final_state: dict = {}
    with st.status("Processing your request…") as status:
        while True:
            msg = result_queue.get(timeout=120)
            if msg[0] == "done":
                final_state = msg[2]
                status.update(label="Done!", state="complete")
                break
            _, node_name, _ = msg
            status.update(label=f"Running: {node_name.replace('_', ' ').title()}…")
    return final_state


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
        _state = st.session_state.current_state
        _meta = (_state or {}).get("metadata") or {}
        _image_url = _meta.get("image_url") or ""
        if _image_url.startswith("data:image"):
            import base64 as _b64

            st.subheader("Content Preview")
            try:
                _img_bytes = _b64.b64decode(_image_url.split(",", 1)[1])
                st.image(
                    _img_bytes,
                    caption=f"Generated via {_meta.get('image_source', 'gpt-image-1')}",
                    use_container_width=True,
                )
            except Exception as _exc:
                st.warning(f"Could not render image: {_exc}")
            if _meta.get("prompt_used"):
                with st.expander("🔍 Prompt used"):
                    st.text(_meta["prompt_used"])
        else:
            render_preview(_state)

    # Process new input
    if user_input:
        st.session_state.messages.append({"role": "user", "content": user_input})

        if not _validate_input(user_input):
            st.rerun()

        try:
            result = _run_workflow(user_input)
            st.session_state.current_state = result

            # Add assistant response to chat
            assistant_msg = (
                result.get("final_content")
                or "I couldn't generate a response. Please try again."
            )
            # For non-image content, show a short preview in chat
            if result.get("content_type") == "image":
                preview_msg = f"✅ Image generated! See the preview panel →\n\n*Prompt used:* {(result.get('metadata') or {}).get('prompt_used', '')[:100]}"
            else:
                preview_msg = assistant_msg[:300] + (
                    "…" if len(assistant_msg) > 300 else ""
                )

            st.session_state.messages.append(
                {"role": "assistant", "content": preview_msg}
            )

            # Update agent conversation history (last 5)
            agent_hist = append_to_history(
                {
                    "conversation_history": st.session_state.agent_history,
                    "user_message": user_input,
                    "next_agent": None,
                    "research_output": None,
                    "sources": None,
                    "final_content": None,
                    "content_type": None,
                    "error": None,
                    "metadata": None,
                },
                "user",
                user_input,
            )
            agent_hist = append_to_history(agent_hist, "assistant", assistant_msg[:500])
            st.session_state.agent_history = agent_hist["conversation_history"]

        except Exception as exc:
            logger.error("Workflow error: %s", exc, exc_info=True)
            error_msg = f"An error occurred: {exc}"
            st.session_state.messages.append(
                {"role": "assistant", "content": error_msg}
            )

        st.rerun()


if __name__ == "__main__":
    main()
