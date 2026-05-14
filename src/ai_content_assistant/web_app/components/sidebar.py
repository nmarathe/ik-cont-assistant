"""Sidebar component — content settings and configuration controls."""

import streamlit as st


def render_sidebar() -> dict:
    """Render sidebar controls and return their current values."""
    with st.sidebar:
        st.title("⚙️ Settings")
        st.divider()

        content_type = st.selectbox(
            "Content Type",
            options=["Auto-detect", "Research", "Blog Post", "LinkedIn Post", "Image", "Content Strategy"],
            index=0,
            help="Force a specific content type, or let the AI decide.",
        )

        tone = st.select_slider(
            "Tone",
            options=["Formal", "Professional", "Conversational", "Casual"],
            value="Professional",
        )

        word_count = st.number_input(
            "Target Word Count (Blog)",
            min_value=500,
            max_value=5000,
            value=2000,
            step=100,
        )

        keywords = st.text_area(
            "Target Keywords",
            placeholder="ai, machine learning, content marketing",
            help="Comma-separated keywords for SEO optimization.",
            height=80,
        )

        st.divider()
        st.caption("💡 **Tips**")
        st.caption("• Ask for research first, then request a blog post to use that research.")
        st.caption("• Use 'refine' or 'make it more...' to iterate on the last result.")
        st.caption("• Image requests work best with descriptive prompts.")

    type_map = {
        "Auto-detect": "",
        "Research": "research",
        "Blog Post": "blog",
        "LinkedIn Post": "linkedin",
        "Image": "image",
        "Content Strategy": "strategy",
    }
    return {
        "content_type": type_map.get(content_type, ""),
        "tone": tone.lower(),
        "word_count": word_count,
        "keywords": keywords,
    }
