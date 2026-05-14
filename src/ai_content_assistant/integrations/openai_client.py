"""OpenAI client wrapper with retry logic, streaming, and token logging."""

import logging
from collections.abc import AsyncIterator
from typing import Any

from openai import AsyncOpenAI, RateLimitError
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from ai_content_assistant.core.config import settings

logger = logging.getLogger(__name__)


class OpenAIClient:
    """Thin async wrapper around the OpenAI SDK."""

    def __init__(self) -> None:
        self._client = AsyncOpenAI(api_key=settings.openai_api_key)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(RateLimitError),
        reraise=True,
    )
    async def chat_complete(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int = 1000,
        json_mode: bool = False,
    ) -> tuple[str, dict[str, Any]]:
        """Return (content, usage_dict). Use json_mode=True for structured JSON output."""
        kwargs: dict[str, Any] = {
            "model": model or settings.default_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        response = await self._client.chat.completions.create(**kwargs)
        usage = response.usage
        usage_dict = {
            "prompt_tokens": usage.prompt_tokens if usage else 0,
            "completion_tokens": usage.completion_tokens if usage else 0,
            "total_tokens": usage.total_tokens if usage else 0,
        }
        logger.debug(
            "model=%s prompt=%d completion=%d total=%d",
            kwargs["model"],
            usage_dict["prompt_tokens"],
            usage_dict["completion_tokens"],
            usage_dict["total_tokens"],
        )
        content = response.choices[0].message.content or ""
        return content, usage_dict

    async def chat_stream(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
        max_tokens: int = 3500,
    ) -> AsyncIterator[str]:
        """Yield content chunks for streaming long-form outputs."""
        stream = await self._client.chat.completions.create(
            model=model or settings.default_model,
            messages=messages,
            max_tokens=max_tokens,
            stream=True,
        )
        async for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta

    async def generate_image(
        self,
        prompt: str,
        size: str = "1024x1024",
        quality: str = "standard",
    ) -> dict[str, str]:
        """Generate an image and return {url, revised_prompt}."""
        response = await self._client.images.generate(
            model=settings.image_model,
            prompt=prompt,
            size=size,  # type: ignore[arg-type]
            quality=quality,  # type: ignore[arg-type]
            n=1,
        )
        item = response.data[0]
        return {
            "url": item.url or "",
            "revised_prompt": item.revised_prompt or prompt,
        }


openai_client = OpenAIClient()
