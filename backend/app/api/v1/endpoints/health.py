"""Liveness and readiness probes."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import text

from app.api.deps import DbSession
from app.core.config import settings

router = APIRouter(tags=["health"])


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
    except Exception:  # noqa: BLE001 - any failure here means "not ready"
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
