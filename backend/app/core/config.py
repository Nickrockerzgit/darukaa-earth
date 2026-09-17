"""Application configuration loaded from the environment.

Every tunable lives here so that nothing else in the codebase reads
``os.environ`` directly. That keeps configuration testable (override the
settings object) and makes the full surface of required env vars discoverable
in one place.
"""

from __future__ import annotations

from enum import StrEnum
from functools import lru_cache
from typing import Annotated, Literal

from pydantic import Field, PostgresDsn, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Environment(StrEnum):
    """Deployment environment the process is running in."""

    DEVELOPMENT = "development"
    TEST = "test"
    STAGING = "staging"
    PRODUCTION = "production"


#: ``NoDecode`` stops pydantic-settings from trying to JSON-parse the raw env
#: value, so ``CORS_ORIGINS=http://a,http://b`` works without JSON quoting.
CommaSeparatedList = Annotated[list[str], NoDecode]


class Settings(BaseSettings):
    """Runtime settings, populated from environment variables or a ``.env`` file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ---- Application ----
    environment: Environment = Environment.DEVELOPMENT
    debug: bool = False
    project_name: str = "Darukaa.Earth API"
    api_v1_prefix: str = "/api/v1"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    log_json: bool = False

    # ---- Database ----
    database_url: PostgresDsn
    test_database_url: PostgresDsn | None = None
    db_pool_size: int = Field(default=10, ge=1, le=100)
    db_max_overflow: int = Field(default=20, ge=0, le=100)
    db_echo: bool = False

    # ---- Security ----
    secret_key: str = Field(min_length=32)
    access_token_expire_minutes: int = Field(default=15, ge=1)
    refresh_token_expire_days: int = Field(default=7, ge=1)
    jwt_algorithm: str = "HS256"

    # ---- CORS ----
    cors_origins: CommaSeparatedList = Field(default_factory=list)

    # ---- Demo seed ----
    seed_demo_email: str = "admin@darukaa.earth"
    # A published demo credential, not a secret: it is printed in the README.
    seed_demo_password: str = "DarukaaDemo123!"  # noqa: S105

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_csv(cls, value: str | list[str]) -> list[str]:
        """Allow list-valued settings to be given as a comma-separated string."""
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @model_validator(mode="after")
    def _reject_placeholder_secret_in_prod(self) -> Settings:
        """Fail fast if the sample secret key leaks into a deployed environment."""
        if self.is_production and "change-me" in self.secret_key.lower():
            msg = "SECRET_KEY must be overridden in staging and production"
            raise ValueError(msg)
        return self

    @property
    def is_production(self) -> bool:
        """True when running in a deployed, non-development environment."""
        return self.environment in {Environment.STAGING, Environment.PRODUCTION}

    @property
    def sqlalchemy_url(self) -> str:
        """The database URL as a plain string for SQLAlchemy."""
        return str(self.database_url)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the process-wide settings singleton.

    Cached so that env parsing happens once; tests clear the cache when they
    need to inject an alternative configuration.
    """
    return Settings()


settings = get_settings()
