"""OpenAI client wrapper with retry logic, streaming, and token logging.

All HTTP calls use the synchronous OpenAI client via asyncio.run_in_executor so
they execute on a thread-pool worker. This sidesteps an async httpx/SSL issue on
Windows where verify=False is not honoured inside the ProactorEventLoop that
Streamlit's tornado server installs in the main thread.
"""

import asyncio
import logging
from collections.abc import AsyncIterator
from typing import Any

import httpx
from openai import OpenAI, RateLimitError
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from ai_content_assistant.core.config import settings

logger = logging.getLogger(__name__)


def _make_sync_client() -> tuple["OpenAI", "httpx.Client"]:
    """Return (OpenAI, httpx.Client) — caller must close the httpx client."""
    http = httpx.Client(verify=False)
    return OpenAI(api_key=settings.openai_api_key, http_client=http), http


class OpenAIClient:
    """Async wrapper around the sync OpenAI SDK, run via executor."""

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

        def _call() -> Any:
            client, http = _make_sync_client()
            with http:
                return client.chat.completions.create(**kwargs)

        response = await asyncio.get_running_loop().run_in_executor(None, _call)
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
        return response.choices[0].message.content or "", usage_dict

    async def chat_stream(
        self,
        messages: list[dict[str, str]],
        model: str | None = None,
        max_tokens: int = 3500,
    ) -> AsyncIterator[str]:
        """Yield content chunks. Collected synchronously in executor, then yielded."""

        def _collect() -> list[str]:
            client, http = _make_sync_client()
            chunks: list[str] = []
            with http:
                with client.chat.completions.create(
                    model=model or settings.default_model,
                    messages=messages,
                    max_tokens=max_tokens,
                    stream=True,
                ) as stream:
                    for chunk in stream:
                        delta = chunk.choices[0].delta.content
                        if delta:
                            chunks.append(delta)
            return chunks

        for chunk in await asyncio.get_running_loop().run_in_executor(None, _collect):
            yield chunk

    async def generate_image(
        self,
        prompt: str,
        size: str = "1024x1024",
        quality: str = "auto",
    ) -> dict[str, str]:
        """Generate an image and return {url, revised_prompt}.

        gpt-image-1 returns base64 only; dall-e-3 returns a URL.
        """
        model = settings.image_model
        use_b64 = model == "gpt-image-1"
        kwargs: dict[str, Any] = {
            "model": model,
            "prompt": prompt,
            "size": size,
            "n": 1,
        }
        if use_b64:
            kwargs["output_format"] = "png"
        else:
            kwargs["quality"] = quality  # type: ignore[assignment]

        def _call() -> Any:
            client, http = _make_sync_client()
            with http:
                return client.images.generate(**kwargs)

        response = await asyncio.get_running_loop().run_in_executor(None, _call)
        item = response.data[0]
        if use_b64:
            # Strip whitespace/newlines: some encoders wrap base64, and stray
            # newlines break both the data-URI prefix check and URL parsing.
            b64 = "".join((item.b64_json or "").split())
            url = f"data:image/png;base64,{b64}"
            revised = prompt
        else:
            url = (item.url or "").strip()
            revised = item.revised_prompt or prompt  # type: ignore[attr-defined]

        return {"url": url, "revised_prompt": revised}


openai_client = OpenAIClient()
