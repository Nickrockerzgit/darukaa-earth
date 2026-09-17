"""FastAPI application factory, middleware and error handling."""

from __future__ import annotations

import time
import uuid
from collections.abc import AsyncGenerator, Awaitable, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.gzip import GZipMiddleware

from app.api.v1.endpoints import health
from app.api.v1.router import api_router
from app.core.config import settings
from app.core.exceptions import AppError
from app.core.logging import configure_logging, get_logger, request_id_ctx
from app.db.session import engine
from app.schemas.common import ErrorResponse

REQUEST_ID_HEADER = "X-Request-ID"
#: GeoJSON responses compress extremely well; below this size the CPU cost
#: outweighs the transfer saving.
GZIP_MINIMUM_SIZE = 1024

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None]:
    """Configure logging on startup and dispose of the pool on shutdown."""
    configure_logging(level=settings.log_level, json_output=settings.log_json)
    logger.info(
        "application.startup",
        environment=settings.environment.value,
        docs_enabled=not settings.is_production,
    )
    yield
    await engine.dispose()
    logger.info("application.shutdown")


def create_app() -> FastAPI:
    """Build and configure the FastAPI application."""
    app = FastAPI(
        title=settings.project_name,
        version="0.1.0",
        summary="Geospatial analytics for carbon and biodiversity projects",
        lifespan=lifespan,
        # Interactive docs are a demo feature, not a production surface.
        docs_url=None if settings.is_production else "/docs",
        redoc_url=None if settings.is_production else "/redoc",
        openapi_url=None if settings.is_production else "/openapi.json",
    )

    _register_middleware(app)
    _register_exception_handlers(app)

    app.include_router(health.router)
    app.include_router(api_router, prefix=settings.api_v1_prefix)
    return app


def _register_middleware(app: FastAPI) -> None:
    """Attach CORS, compression and request-tracing middleware."""
    if settings.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
            expose_headers=[REQUEST_ID_HEADER],
        )
    app.add_middleware(GZipMiddleware, minimum_size=GZIP_MINIMUM_SIZE)

    @app.middleware("http")
    async def request_context(
        request: Request, call_next: Callable[[Request], Awaitable[JSONResponse]]
    ) -> JSONResponse:
        """Tag every request with an id and log its outcome and duration."""
        request_id = request.headers.get(REQUEST_ID_HEADER) or str(uuid.uuid4())
        token = request_id_ctx.set(request_id)
        started = time.perf_counter()
        try:
            response = await call_next(request)
        finally:
            request_id_ctx.reset(token)
        duration_ms = round((time.perf_counter() - started) * 1000, 2)
        response.headers[REQUEST_ID_HEADER] = request_id
        logger.info(
            "http.request",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=duration_ms,
        )
        return response


def _register_exception_handlers(app: FastAPI) -> None:
    """Map every failure onto the single ``ErrorResponse`` envelope."""

    @app.exception_handler(AppError)
    async def handle_app_error(_request: Request, exc: AppError) -> JSONResponse:
        """Translate a domain error into its declared HTTP status."""
        logger.warning("app.error", error_code=exc.error_code, message=exc.message)
        payload = ErrorResponse(
            error=exc.error_code,
            message=exc.message,
            details=exc.details or None,
            request_id=request_id_ctx.get(),
        )
        return JSONResponse(status_code=exc.status_code, content=payload.model_dump())

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        _request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        """Return Pydantic's field errors in the same envelope as everything else."""
        payload = ErrorResponse(
            error="validation_error",
            message="Request payload failed validation.",
            details={"errors": _serialisable_errors(exc)},
            request_id=request_id_ctx.get(),
        )
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content=payload.model_dump()
        )

    @app.exception_handler(Exception)
    async def handle_unexpected(_request: Request, exc: Exception) -> JSONResponse:
        """Log the stack trace but never leak internals to the client."""
        logger.exception("unhandled.exception", error=str(exc))
        payload = ErrorResponse(
            error="internal_error",
            message="An unexpected error occurred.",
            request_id=request_id_ctx.get(),
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content=payload.model_dump()
        )


def _serialisable_errors(exc: RequestValidationError) -> list[dict[str, object]]:
    """Strip non-JSON-serialisable context (e.g. the original exception)."""
    return [{key: value for key, value in error.items() if key != "ctx"} for error in exc.errors()]


app = create_app()
