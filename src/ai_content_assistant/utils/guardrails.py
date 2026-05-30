"""Input and output guardrails for user safety and content policy."""

import logging
import re

import httpx
import certifi

from ai_content_assistant.core.config import settings

logger = logging.getLogger(__name__)


class InputTooLongError(ValueError):
    pass


class ContentFlaggedError(ValueError):
    pass


class ImageSafetyError(ValueError):
    pass


_PII_PATTERNS: dict[str, re.Pattern[str]] = {
    "email address": re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"),
    "phone number":  re.compile(r"(\+?1[\s.-]?)?\(?\d{3}\)?[\s.-]\d{3}[\s.-]\d{4}"),
    "SSN":           re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    "credit card":   re.compile(r"\b(?:\d[ -]?){13,16}\b"),
}

_IMAGE_DENY_KEYWORDS: frozenset[str] = frozenset([
    "nude", "naked", "nsfw", "explicit", "pornographic",
    "violence", "gore", "weapon", "bomb",
    "child", "minor", "underage",
])

_MODERATION_URL = "https://api.openai.com/v1/moderations"


def check_input_length(text: str) -> None:
    """Raise InputTooLongError if text exceeds the configured maximum."""
    if len(text) > settings.max_input_length:
        raise InputTooLongError(
            f"Your message is too long ({len(text):,} chars). "
            f"Please keep it under {settings.max_input_length:,} characters."
        )


def detect_pii(text: str) -> list[str]:
    """Return a list of PII type names found in text (does not raise)."""
    return [name for name, pattern in _PII_PATTERNS.items() if pattern.search(text)]


def check_moderation(text: str) -> None:
    """Call the OpenAI Moderation API (sync); raise ContentFlaggedError if flagged.

    Network/SSL failures are logged as warnings and treated as passed — the app
    must not crash because an optional safety check cannot reach its endpoint.
    """
    try:
        response = httpx.post(
            _MODERATION_URL,
            headers={"Authorization": f"Bearer {settings.openai_api_key}"},
            json={"input": text},
            timeout=10.0,
            verify=certifi.where(),
        )
        response.raise_for_status()
    except (httpx.ConnectError, httpx.TimeoutException, httpx.HTTPStatusError) as exc:
        logger.warning("Moderation API unavailable (%s); skipping check", exc)
        return
    output = response.json()["results"][0]
    if output["flagged"]:
        cats = [k for k, v in output["categories"].items() if v]
        logger.warning("Moderation flagged input: %s", cats)
        raise ContentFlaggedError(
            "Your request contains content that violates our usage policy "
            f"({', '.join(cats)}). Please revise and try again."
        )


async def async_check_moderation(text: str) -> None:
    """Async Moderation API call for use inside async agent methods."""
    try:
        async with httpx.AsyncClient(timeout=10.0, verify=certifi.where()) as client:
            response = await client.post(
                _MODERATION_URL,
                headers={"Authorization": f"Bearer {settings.openai_api_key}"},
                json={"input": text},
            )
            response.raise_for_status()
    except ContentFlaggedError:
        raise
    except Exception as exc:
        logger.warning("Moderation API unavailable (%s); skipping check", exc)
        return
    output = response.json()["results"][0]
    if output["flagged"]:
        cats = [k for k, v in output["categories"].items() if v]
        logger.warning("Moderation flagged image prompt: %s", cats)
        raise ContentFlaggedError(f"Image prompt flagged: {', '.join(cats)}")


def check_image_prompt(prompt: str) -> None:
    """Raise ImageSafetyError if the prompt contains a keyword from the deny-list."""
    lower = prompt.lower()
    for kw in _IMAGE_DENY_KEYWORDS:
        if kw in lower:
            raise ImageSafetyError(
                "Image prompt contains unsafe content. Please revise your request."
            )
