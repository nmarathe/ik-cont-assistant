"""Unit tests for Settings configuration."""

import pytest
from pydantic import ValidationError


def test_settings_defaults(monkeypatch):
    """Default model values are applied when not overridden."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("SERP_API_KEY", "serp-test")

    # Re-import to pick up monkeypatched env
    from importlib import reload
    import ai_content_assistant.core.config as config_module

    reload(config_module)

    s = config_module.Settings()
    assert s.default_model == "gpt-4o"
    assert s.fast_model == "gpt-4o-mini"
    assert s.image_model == "gpt-image-1"
    assert s.blog_target_word_count == 2000
    assert s.linkedin_max_chars == 3000


def test_settings_missing_openai_key(monkeypatch):
    """ValidationError raised when openai_api_key is absent."""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("SERP_API_KEY", "serp-test")

    from importlib import reload
    import ai_content_assistant.core.config as config_module

    reload(config_module)
    # _env_file=None disables .env loading so a local .env can't satisfy the
    # required key and mask the validation we're asserting on.
    with pytest.raises((ValidationError, Exception)):
        config_module.Settings(_env_file=None)


def test_settings_optional_keys_default_none(monkeypatch):
    """Optional API keys default to None when not set."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("SERP_API_KEY", "serp-test")
    monkeypatch.delenv("PERPLEXITY_API_KEY", raising=False)
    monkeypatch.delenv("STABILITY_API_KEY", raising=False)

    from importlib import reload
    import ai_content_assistant.core.config as config_module

    reload(config_module)

    # _env_file=None disables .env loading so optional keys actually default to
    # None instead of being populated from a local .env.
    s = config_module.Settings(_env_file=None)
    assert s.perplexity_api_key is None
    assert s.stability_api_key is None
