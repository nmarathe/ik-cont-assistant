"""Content quality validation and scoring."""

import re


def validate_blog(content: str) -> dict:
    """Validate a blog post and return {passed, score, issues}."""
    issues: list[str] = []
    score = 100

    # Word count
    words = re.findall(r"\b\w+\b", content)
    if len(words) < 1500:
        issues.append(f"Word count {len(words)} is below minimum 1500")
        score -= 20

    # H1
    if not re.search(r"^# .+$", content, re.MULTILINE):
        issues.append("Missing H1 heading")
        score -= 15

    # H2 count
    h2_count = len(re.findall(r"^## .+$", content, re.MULTILINE))
    if h2_count < 3:
        issues.append(f"Only {h2_count} H2 headings; minimum is 3")
        score -= 15

    # Frontmatter
    if not content.strip().startswith("---"):
        issues.append("Missing YAML frontmatter")
        score -= 10

    return {"passed": not issues, "score": max(0, score), "issues": issues}


def validate_linkedin(content: str) -> dict:
    """Validate a LinkedIn post and return {passed, score, issues}."""
    issues: list[str] = []
    score = 100

    # Length
    if len(content) > 3000:
        issues.append(f"Post length {len(content)} exceeds 3000 character limit")
        score -= 20

    # Hashtags
    hashtags = re.findall(r"#\w+", content)
    if len(hashtags) < 3:
        issues.append(f"Only {len(hashtags)} hashtags; recommend 5-8")
        score -= 15
    elif len(hashtags) > 10:
        issues.append(f"{len(hashtags)} hashtags may reduce reach; keep 5-8")
        score -= 5

    # Hook (first line should be non-empty and engaging)
    first_line = content.strip().split("\n")[0]
    if len(first_line) < 20:
        issues.append("First line (hook) appears too short")
        score -= 10

    return {"passed": not issues, "score": max(0, score), "issues": issues}


def score_content(content: str, content_type: str) -> int:
    """Return a 0-100 quality score based on content type validation."""
    if content_type == "blog":
        return validate_blog(content)["score"]
    if content_type == "linkedin":
        return validate_linkedin(content)["score"]
    # Default: basic non-empty check
    return 80 if len(content.strip()) > 100 else 40
