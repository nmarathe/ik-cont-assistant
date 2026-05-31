"""Content preview panel — displays generated content with quality metrics and download options."""

import base64

import httpx
import certifi
import streamlit as st

from ai_content_assistant.utils.export_tools import (
    generate_filename,
    to_markdown,
    to_plain_text,
)
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

    # Image output — only when we actually have an image payload. A failed image
    # request keeps content_type == "image" but has no image_url; let it fall
    # through to text rendering so the error message is shown to the user instead
    # of being (mis)decoded as image bytes.
    if metadata.get("image_url"):
        _render_image_preview(state, metadata)
        return

    # Quality score badge
    if content_type in ("blog", "linkedin"):
        quality = score_content(content, content_type)
        col1, col2, col3 = st.columns(3)
        col1.metric("Quality Score", f"{quality}/100")
        if content_type == "blog" and metadata.get("title"):
            col2.metric(
                "Title",
                metadata["title"][:30] + "…"
                if len(metadata.get("title", "")) > 30
                else metadata.get("title", ""),
            )
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
                st.text_area(
                    "", value=text, height=120, key=f"variant_{tone}", disabled=True
                )

    # Main content display
    st.markdown("---")
    st.markdown(content)

    # Export buttons
    _render_export_buttons(content, content_type, metadata)


def _render_image_preview(state: dict, metadata: dict) -> None:
    image_url = (metadata.get("image_url") or state.get("final_content") or "").strip()
    prompt_used = metadata.get("prompt_used", "")
    source = metadata.get("image_source", "")

    if not image_url:
        st.warning("Image URL not available")
        return

    img_bytes: bytes | None = None
    if image_url.startswith("data:"):
        # st.image() doesn't accept data URIs as strings — decode to bytes first.
        try:
            img_bytes = base64.b64decode(image_url.split(",", 1)[1])
        except Exception as exc:
            st.warning(f"Could not decode image: {exc}")
            return
    elif image_url.startswith(("http://", "https://")):
        try:
            with httpx.Client(verify=certifi.where()) as client:
                img_bytes = client.get(image_url, timeout=30).content
        except Exception as exc:
            st.warning(f"Could not fetch image: {exc}")
            return
    else:
        # Not a scheme'd URL and not a data URI — treat as a raw base64 payload.
        try:
            img_bytes = base64.b64decode(image_url, validate=False)
        except Exception as exc:
            st.warning(f"Could not decode image: {exc}")
            return

    st.image(img_bytes, caption=f"Generated via {source}", use_container_width=True)

    if prompt_used:
        with st.expander("🔍 Prompt used"):
            st.text(prompt_used)


def _render_export_buttons(content: str, content_type: str, metadata: dict) -> None:
    st.divider()
    st.caption("Export")
    filename = generate_filename(
        content_type or "content", metadata.get("slug") or "output"
    )

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
