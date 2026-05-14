"""Unit tests for content optimization utilities."""

from ai_content_assistant.utils.content_optimization import (
    calculate_keyword_density,
    score_readability,
    suggest_headings,
)


def test_keyword_density_basic():
    text = "AI is transforming content marketing. AI tools help marketers. AI is everywhere."
    density = calculate_keyword_density(text, "AI")
    assert density > 0
    assert density < 50


def test_keyword_density_zero_for_missing_keyword():
    text = "This text has no relevant terms."
    assert calculate_keyword_density(text, "blockchain") == 0.0


def test_keyword_density_empty_inputs():
    assert calculate_keyword_density("", "ai") == 0.0
    assert calculate_keyword_density("some text", "") == 0.0


def test_score_readability_returns_dict():
    text = "This is a simple sentence. It has short words. Reading is easy."
    result = score_readability(text)
    assert "flesch_kincaid_grade" in result
    assert "avg_sentence_length" in result
    assert isinstance(result["flesch_kincaid_grade"], float)


def test_score_readability_empty_text():
    result = score_readability("")
    assert result["flesch_kincaid_grade"] == 0.0
    assert result["avg_sentence_length"] == 0.0


def test_suggest_headings_extracts_h2_h3():
    content = """# Main Title

## Section One

Some content here.

### Subsection

## Section Two
"""
    headings = suggest_headings(content)
    assert "Section One" in headings
    assert "Section Two" in headings
    assert "Subsection" in headings
