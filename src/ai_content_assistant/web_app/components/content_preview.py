"""Content preview panel — displays generated content with quality metrics and download options."""

import streamlit as st

from ai_content_assistant.utils.export_tools import generate_filename, to_markdown, to_plain_text
from ai_content_assistant.utils.quality_validation import score_content


def render_preview(state: dict | None) -> None:
    """Render the right-side content preview panel."""
    st.subheader("Content Preview")

    if not state or not state.get("final_content"):
        st.info("Generated content will appear here once you submit a request.")
        return

    content = state["final_content"]
    content_type = state.get("content_type", "")
    metadata = state.get("metadata") or {}

    # Image output
    if content_type == "image" or metadata.get("image_url"):
        _render_image_preview(state, metadata)
        return

    # Quality score badge
    if content_type in ("blog", "linkedin"):
        quality = score_content(content, content_type)
        col1, col2, col3 = st.columns(3)
        col1.metric("Quality Score", f"{quality}/100")
        if content_type == "blog" and metadata.get("title"):
            col2.metric("Title", metadata["title"][:30] + "…" if len(metadata.get("title", "")) > 30 else metadata.get("title", ""))
        if content_type == "linkedin" and metadata.get("hashtags"):
            col3.metric("Hashtags", len(metadata["hashtags"]))

    # Sources for research
    sources = state.get("sources")
    if sources:
        with st.expander(f"📚 Sources ({len(sources)})"):
            for url in sources:
                if url:
                    st.markdown(f"- {url}")

    # LinkedIn variants
    if content_type == "linkedin" and metadata.get("variants"):
        with st.expander("🎭 Tone Variants"):
            variants = metadata["variants"]
            for tone, text in variants.items():
                st.markdown(f"**{tone.replace('_', ' ').title()}**")
                st.text_area("", value=text, height=120, key=f"variant_{tone}", disabled=True)

    # Main content display
    st.markdown("---")
    st.markdown(content)

    # Export buttons
    _render_export_buttons(content, content_type, metadata)


def _render_image_preview(state: dict, metadata: dict) -> None:
    image_url = metadata.get("image_url", state.get("final_content", ""))
    prompt_used = metadata.get("prompt_used", "")
    source = metadata.get("image_source", "")

    if image_url.startswith("data:image"):
        # base64 image from Stability AI
        st.image(image_url, caption=f"Generated via {source}", use_container_width=True)
    elif image_url:
        st.image(image_url, caption=f"Generated via {source}", use_container_width=True)
    else:
        st.warning("Image URL not available")

    if prompt_used:
        with st.expander("🔍 Prompt used"):
            st.text(prompt_used)


def _render_export_buttons(content: str, content_type: str, metadata: dict) -> None:
    st.divider()
    st.caption("Export")
    filename = generate_filename(content_type or "content", metadata.get("slug") or "output")

    col1, col2 = st.columns(2)
    md_content = to_markdown(content, metadata)
    col1.download_button(
        "⬇ Download .md",
        data=md_content,
        file_name=f"{filename}.md",
        mime="text/markdown",
    )
    col2.download_button(
        "⬇ Download .txt",
        data=to_plain_text(content),
        file_name=f"{filename}.txt",
        mime="text/plain",
    )
