"""Centralised settings loaded from environment / .env file."""

import logging
from typing import Optional

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # API keys
    openai_api_key: str
    serp_api_key: str
    perplexity_api_key: Optional[str] = None
    stability_api_key: Optional[str] = None

    # Model selection (two-tier for token efficiency)
    default_model: str = "gpt-4o"
    fast_model: str = "gpt-4o-mini"
    image_model: str = "dall-e-3"

    # Content defaults
    max_research_results: int = 10
    blog_target_word_count: int = 2000
    linkedin_max_chars: int = 3000

    # Runtime
    env: str = "development"
    log_level: str = "INFO"

    @field_validator("openai_api_key", "serp_api_key")
    @classmethod
    def must_not_be_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("API key must not be empty")
        return v


settings = Settings()


def configure_logging() -> None:
    """Configure root logger using the level from settings."""
    level = getattr(logging, settings.log_level.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )
