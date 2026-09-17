"""Tests for settings validation.

The placeholder-secret guard is a security control, not a convenience: signing
JWTs with a value published in .env.example would let anyone mint a valid
token. These tests exist so nobody removes it to make a deploy go green.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.core.config import Environment, Settings

PLACEHOLDER = "change-me-in-production-use-a-48-byte-urlsafe-random-string"
REAL_SECRET = "a-real-secret-that-is-comfortably-longer-than-32-chars"
DB_URL = "postgresql+asyncpg://darukaa:darukaa@localhost:5433/darukaa"


def build(**overrides: object) -> Settings:
    """Construct Settings without reading the ambient .env file."""
    values: dict[str, object] = {
        "database_url": DB_URL,
        "secret_key": REAL_SECRET,
        **overrides,
    }
    return Settings(_env_file=None, **values)  # type: ignore[arg-type]


class TestPlaceholderSecretGuard:
    @pytest.mark.parametrize("environment", [Environment.PRODUCTION, Environment.STAGING])
    def test_refuses_to_boot_on_the_placeholder_when_deployed(self, environment: Environment):
        with pytest.raises(ValidationError, match="SECRET_KEY is still the placeholder"):
            build(environment=environment, secret_key=PLACEHOLDER)

    def test_error_says_how_to_fix_it(self):
        # An error that only says "wrong" costs someone a deploy cycle.
        with pytest.raises(ValidationError) as caught:
            build(environment=Environment.PRODUCTION, secret_key=PLACEHOLDER)
        message = str(caught.value)
        assert "Generate" in message
        assert "token_urlsafe" in message

    def test_the_check_is_case_insensitive(self):
        with pytest.raises(ValidationError):
            build(environment=Environment.PRODUCTION, secret_key=PLACEHOLDER.upper())

    @pytest.mark.parametrize("environment", [Environment.DEVELOPMENT, Environment.TEST])
    def test_local_environments_may_use_the_sample(self, environment: Environment):
        # Otherwise `cp .env.example .env` would not work for a new contributor.
        assert build(environment=environment, secret_key=PLACEHOLDER).secret_key == PLACEHOLDER

    def test_a_real_secret_passes_in_production(self):
        settings = build(environment=Environment.PRODUCTION, secret_key=REAL_SECRET)
        assert settings.is_production


class TestRequiredFields:
    def test_secret_key_must_be_long_enough(self):
        with pytest.raises(ValidationError, match="secret_key"):
            build(secret_key="too-short")

    def test_database_url_is_required(self):
        with pytest.raises(ValidationError, match="database_url"):
            Settings(_env_file=None, secret_key=REAL_SECRET)  # type: ignore[call-arg]


class TestCorsParsing:
    def test_accepts_a_comma_separated_string(self):
        settings = build(cors_origins="https://a.example, https://b.example")
        assert settings.cors_origins == ["https://a.example", "https://b.example"]

    def test_ignores_blank_entries(self):
        assert build(cors_origins="https://a.example,,  ").cors_origins == ["https://a.example"]

    def test_accepts_a_list_unchanged(self):
        assert build(cors_origins=["https://a.example"]).cors_origins == ["https://a.example"]

    def test_defaults_to_empty(self):
        assert build().cors_origins == []
