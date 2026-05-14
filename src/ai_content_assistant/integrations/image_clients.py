"""Stability AI fallback image client for when DALL-E is unavailable."""

import base64
import logging

import httpx

from ai_content_assistant.core.config import settings

logger = logging.getLogger(__name__)

_STABILITY_URL = "https://api.stability.ai/v1/generation/stable-diffusion-xl-1024-v1-0/text-to-image"


class StabilityClient:
    """Stability AI image generation — active only when stability_api_key is set."""

    async def generate(
        self, prompt: str, width: int = 1024, height: int = 1024
    ) -> str:
        """Return base64-encoded PNG image data."""
        if not settings.stability_api_key:
            raise RuntimeError("Stability AI API key not configured")

        logger.info("Stability AI generate: %s", prompt[:80])
        payload = {
            "text_prompts": [{"text": prompt, "weight": 1.0}],
            "cfg_scale": 7,
            "height": height,
            "width": width,
            "samples": 1,
            "steps": 30,
        }
        headers = {
            "Authorization": f"Bearer {settings.stability_api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(_STABILITY_URL, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()

        image_data = data["artifacts"][0]["base64"]
        return image_data


stability_client = StabilityClient()
