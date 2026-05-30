"""Image Generator Agent — DALL-E 3 with GPT-4o-mini prompt expansion and Stability AI fallback."""

import logging

from ai_content_assistant.agents.image_prompts import PROMPT_OPTIMIZER_SYSTEM
from ai_content_assistant.core.config import settings
from ai_content_assistant.integrations.image_clients import stability_client
from ai_content_assistant.integrations.openai_client import openai_client
from ai_content_assistant.utils.guardrails import async_check_moderation, check_image_prompt
from ai_content_assistant.workflow.state_management import AgentState

logger = logging.getLogger(__name__)


class ImageGenerator:
    """Generates images via DALL-E 3 with optional Stability AI fallback."""

    async def optimize_prompt(self, user_intent: str) -> str:
        """Expand a brief intent into a detailed DALL-E prompt."""
        content, _ = await openai_client.chat_complete(
            messages=[
                {"role": "system", "content": PROMPT_OPTIMIZER_SYSTEM},
                {"role": "user", "content": user_intent},
            ],
            model=settings.fast_model,
            temperature=0.7,
            max_tokens=300,
        )
        return content.strip()

    async def generate(self, prompt: str) -> dict:
        """Generate an image; return {url, revised_prompt, source}."""
        try:
            result = await openai_client.generate_image(prompt)
            return {**result, "source": settings.image_model}
        except Exception as exc:
            logger.warning("%s failed (%s); trying Stability AI", settings.image_model, exc)
            if settings.stability_api_key:
                b64 = await stability_client.generate(prompt)
                return {
                    "url": f"data:image/png;base64,{b64}",
                    "revised_prompt": prompt,
                    "source": "stability-ai",
                }
            raise RuntimeError("Image generation failed and no fallback available") from exc

    async def run(self, state: AgentState) -> AgentState:
        """Optimize prompt and generate image."""
        intent = state["user_message"]
        print(f"[ImageGenerator] run() called, intent={intent[:40]!r}", flush=True)
        logger.info("ImageGenerator processing: %s", intent[:80])

        try:
            optimized = await self.optimize_prompt(intent)
            print(f"[ImageGenerator] optimize_prompt OK: {optimized[:60]!r}", flush=True)
            logger.info("ImageGenerator: optimize_prompt OK")
        except Exception as exc:
            print(f"[ImageGenerator] optimize_prompt FAILED {type(exc).__name__}: {exc}", flush=True)
            logger.error("ImageGenerator: optimize_prompt FAILED %s: %s", type(exc).__name__, exc)
            raise

        check_image_prompt(optimized)

        try:
            await async_check_moderation(optimized)
            logger.info("ImageGenerator: moderation OK")
        except Exception as exc:
            logger.error("ImageGenerator: moderation FAILED %s: %s", type(exc).__name__, exc)
            raise

        try:
            result = await self.generate(optimized)
            logger.info("ImageGenerator: generate OK, url len=%d", len(result.get("url", "")))
        except Exception as exc:
            logger.error("ImageGenerator: generate FAILED %s: %s", type(exc).__name__, exc)
            raise

        return {
            **state,
            "final_content": result["url"],
            "metadata": {
                **(state.get("metadata") or {}),
                "image_url": result["url"],
                "prompt_used": result["revised_prompt"],
                "image_source": result["source"],
            },
        }
