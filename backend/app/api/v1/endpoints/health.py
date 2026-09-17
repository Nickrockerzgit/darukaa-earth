"""Liveness and readiness probes."""

from __future__ import annotations

from typing import Literal
from urllib.parse import urlsplit

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import text

from app.api.deps import DbSession
from app.core.config import settings
from app.core.logging import get_logger

router = APIRouter(tags=["health"])
logger = get_logger(__name__)


def _database_target() -> str:
    """Host and database name from the configured URL, with the password removed.

    Knowing *which* database the instance is pointed at is usually the answer,
    and it must never be logged with credentials attached.
    """
    url = urlsplit(settings.sqlalchemy_url)
    return f"{url.hostname or '?'}{url.path or ''}"


class HealthStatus(BaseModel):
    """Probe response body."""

    status: Literal["ok", "degraded"]
    environment: str
    database: Literal["up", "down"]
    postgis: str | None = None


@router.get("/health", summary="Liveness probe")
async def health() -> HealthStatus:
    """Report that the process is running. Never touches the database."""
    return HealthStatus(status="ok", environment=settings.environment.value, database="up")


@router.get("/health/ready", summary="Readiness probe")
async def readiness(session: DbSession) -> JSONResponse:
    """Verify the database answers and PostGIS is installed.

    Returns 503 when the dependency is unavailable, so the platform holds
    traffic off an instance that cannot serve it.
    """
    try:
        version = await session.scalar(text("SELECT PostGIS_Lib_Version()"))
    except Exception as exc:  # noqa: BLE001 - any failure here means "not ready"
        # The response stays deliberately vague, since this endpoint is public
        # and the reason can name hosts and drivers. The log is where an
        # operator looks, and a probe that only says "down" costs them an hour.
        logger.error(
            "health.database_unreachable",
            error_type=type(exc).__name__,
            error=str(exc),
            database=_database_target(),
        )
        body = HealthStatus(
            status="degraded", environment=settings.environment.value, database="down"
        )
        return JSONResponse(
            content=body.model_dump(), status_code=status.HTTP_503_SERVICE_UNAVAILABLE
        )

    body = HealthStatus(
        status="ok",
        environment=settings.environment.value,
        database="up",
        postgis=str(version),
    )
    return JSONResponse(content=body.model_dump(), status_code=status.HTTP_200_OK)
