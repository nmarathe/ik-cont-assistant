"""E2E smoke test — verifies the Streamlit app renders without exceptions."""

import pytest


def test_streamlit_app_imports():
    """Verify the app module can be imported without errors."""
    try:
        import ai_content_assistant.web_app.streamlit_app  # noqa: F401
        import ai_content_assistant.web_app.components.sidebar  # noqa: F401
        import ai_content_assistant.web_app.components.chat_panel  # noqa: F401
        import ai_content_assistant.web_app.components.content_preview  # noqa: F401
    except ImportError as exc:
        pytest.fail(f"App module import failed: {exc}")


def test_all_agents_importable():
    """Verify all 6 agents can be imported and instantiated."""
    from ai_content_assistant.agents.blog_writer import BlogWriter
    from ai_content_assistant.agents.content_strategist import ContentStrategist
    from ai_content_assistant.agents.image_generator import ImageGenerator
    from ai_content_assistant.agents.linkedin_writer import LinkedInWriter
    from ai_content_assistant.agents.query_handler import QueryHandler
    from ai_content_assistant.agents.research_agent import ResearchAgent

    for cls in (QueryHandler, ResearchAgent, BlogWriter, LinkedInWriter, ImageGenerator, ContentStrategist):
        instance = cls()
        assert hasattr(instance, "run")


def test_workflow_graph_builds():
    """Verify the LangGraph graph compiles without errors."""
    from ai_content_assistant.workflow.langgraph_workflow import build_graph
    graph = build_graph()
    assert graph is not None
