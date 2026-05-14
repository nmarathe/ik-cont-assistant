"""Content optimization utilities: keyword density, readability, meta generation."""

import re
from typing import Optional

from ai_content_assistant.core.config import settings
from ai_content_assistant.integrations.openai_client import openai_client


def calculate_keyword_density(text: str, keyword: str) -> float:
    """Return keyword frequency as a percentage of total word count."""
    if not text or not keyword:
        return 0.0
    words = re.findall(r"\b\w+\b", text.lower())
    if not words:
        return 0.0
    kw_words = re.findall(r"\b\w+\b", keyword.lower())
    kw_str = " ".join(kw_words)
    count = len(re.findall(re.escape(kw_str), text.lower()))
    return round((count / len(words)) * 100, 2)


def _count_syllables(word: str) -> int:
    """Heuristic syllable count — avoids heavy NLP dependencies."""
    word = word.lower().strip(".,!?;:")
    if not word:
        return 0
    vowel_groups = re.findall(r"[aeiou]+", word)
    count = len(vowel_groups)
    if word.endswith("e") and count > 1:
        count -= 1
    return max(1, count)


def score_readability(text: str) -> dict:
    """Return Flesch-Kincaid grade level and average sentence length."""
    sentences = re.split(r"[.!?]+", text)
    sentences = [s.strip() for s in sentences if s.strip()]
    if not sentences:
        return {"flesch_kincaid_grade": 0.0, "avg_sentence_length": 0.0}

    words = re.findall(r"\b\w+\b", text)
    syllables = sum(_count_syllables(w) for w in words)
    num_words = len(words)
    num_sentences = len(sentences)

    if num_sentences == 0 or num_words == 0:
        return {"flesch_kincaid_grade": 0.0, "avg_sentence_length": 0.0}

    asl = num_words / num_sentences
    asw = syllables / num_words
    fk_grade = 0.39 * asl + 11.8 * asw - 15.59
    return {
        "flesch_kincaid_grade": round(fk_grade, 1),
        "avg_sentence_length": round(asl, 1),
    }


def suggest_headings(content: str) -> list[str]:
    """Extract existing H2/H3 headings and suggest additional ones."""
    existing = re.findall(r"^#{2,3} (.+)$", content, re.MULTILINE)
    return existing


async def generate_meta_description(content: str, keyword: Optional[str] = None) -> str:
    """Generate a max-160-char meta description using the fast model."""
    kw_hint = f" Include the keyword: {keyword}." if keyword else ""
    text, _ = await openai_client.chat_complete(
        messages=[
            {
                "role": "system",
                "content": (
                    "Write a compelling meta description for the following content."
                    f"{kw_hint} Max 160 characters. Return ONLY the description text."
                ),
            },
            {"role": "user", "content": content[:2000]},
        ],
        model=settings.fast_model,
        temperature=0.5,
        max_tokens=60,
    )
    return text.strip()[:160]
