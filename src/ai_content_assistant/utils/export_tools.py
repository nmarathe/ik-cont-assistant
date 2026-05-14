"""Export utilities for downloading generated content."""

import re
from datetime import datetime


def to_markdown(content: str, metadata: dict | None = None) -> str:
    """Ensure content has YAML frontmatter; prepend it if missing."""
    if content.strip().startswith("---"):
        return content

    meta = metadata or {}
    title = meta.get("title", "")
    description = meta.get("meta_description", "")
    keywords = ", ".join(meta.get("keywords", []))
    slug = meta.get("slug", "")

    frontmatter_lines = ["---"]
    if title:
        frontmatter_lines.append(f"title: \"{title}\"")
    if description:
        frontmatter_lines.append(f"meta_description: \"{description}\"")
    if keywords:
        frontmatter_lines.append(f"keywords: [{keywords}]")
    if slug:
        frontmatter_lines.append(f"slug: {slug}")
    frontmatter_lines.append("---\n")

    return "\n".join(frontmatter_lines) + content if len(frontmatter_lines) > 2 else content


def to_plain_text(content: str) -> str:
    """Strip Markdown syntax from content."""
    # Remove frontmatter
    text = re.sub(r"^---[\s\S]*?---\n", "", content, count=1)
    # Remove headings markers
    text = re.sub(r"^#{1,6} ", "", text, flags=re.MULTILINE)
    # Remove bold/italic
    text = re.sub(r"\*{1,3}(.+?)\*{1,3}", r"\1", text)
    # Remove links, keep label
    text = re.sub(r"\[(.+?)\]\(.+?\)", r"\1", text)
    # Remove inline code
    text = re.sub(r"`(.+?)`", r"\1", text)
    # Collapse multiple blank lines
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def generate_filename(content_type: str, topic: str) -> str:
    """Return a slugified filename with timestamp prefix."""
    slug = re.sub(r"[^a-z0-9]+", "-", topic.lower()).strip("-")[:40]
    ts = datetime.now().strftime("%Y%m%d_%H%M")
    return f"{ts}_{content_type}_{slug}"
