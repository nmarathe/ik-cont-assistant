"""Centralised settings loaded from environment / .env file.

Design: All configuration is centralized here as a singleton. Agents import
`settings` directly, ensuring consistent config across the system and fail-fast
validation at startup. Pydantic Settings auto-reads from .env without boilerplate.
"""

import logging
from typing import Optional

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Load and validate all app configuration from environment."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",  # Ignore unknown env vars — prevents startup friction
    )

    # Required API keys: app cannot start without these
    openai_api_key: str
    serp_api_key: str
    # Optional fallback integrations: if missing, the app gracefully degrades
    perplexity_api_key: Optional[str] = None
    stability_api_key: Optional[str] = None

    # Two-tier model strategy: heavy lifting uses default_model, routing/classification
    # use fast_model (cheaper, faster). Reduces token spend and latency for lightweight tasks.
    default_model: str = "gpt-4o"
    fast_model: str = "gpt-4o-mini"
    image_model: str = "dall-e-3"

    # Content generation defaults used by agents
    max_research_results: int = 10
    blog_target_word_count: int = 2000
    linkedin_max_chars: int = 3000

    # Runtime environment control
    env: str = "development"
    log_level: str = "INFO"

    @field_validator("openai_api_key", "serp_api_key")
    @classmethod
    def must_not_be_empty(cls, v: str) -> str:
        """Fail at startup if required keys are present but empty strings."""
        if not v.strip():
            raise ValueError("API key must not be empty")
        return v


# Module-level singleton: all agents share this one validated config instance.
# Import it as: from src.ai_content_assistant.core.config import settings
settings = Settings()


def configure_logging() -> None:
    """Configure root logger using the level from settings."""
    level = getattr(logging, settings.log_level.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )
