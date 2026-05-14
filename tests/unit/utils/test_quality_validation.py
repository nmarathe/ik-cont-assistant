"""Unit tests for quality validation."""

from ai_content_assistant.utils.quality_validation import (
    score_content,
    validate_blog,
    validate_linkedin,
)


def test_validate_blog_passes_good_post():
    content = """---
title: "Test"
meta_description: "desc"
keywords: [ai]
slug: test
---

# Test Blog Post

## Introduction
""" + "word " * 1600 + """

## Section Two

content here

## Section Three

more content

## Conclusion

final words
"""
    result = validate_blog(content)
    assert result["score"] > 60
    assert "Missing H1" not in result["issues"]


def test_validate_blog_fails_short_post():
    content = "# Short Post\n\n## Section\n\nToo short."
    result = validate_blog(content)
    assert result["passed"] is False
    assert any("Word count" in i for i in result["issues"])


def test_validate_linkedin_passes_good_post():
    post = "This is a great hook line!\n\nBody content with value.\n\nCall to action here.\n\n#AI #Marketing #Content #Tech #Innovation"
    result = validate_linkedin(post)
    assert result["score"] > 70


def test_validate_linkedin_fails_long_post():
    post = "x" * 3100
    result = validate_linkedin(post)
    assert result["passed"] is False
    assert any("3000" in i for i in result["issues"])


def test_score_content_returns_int():
    content = "Some content here with enough text to score."
    assert isinstance(score_content(content, "research"), int)
    assert 0 <= score_content(content, "research") <= 100
