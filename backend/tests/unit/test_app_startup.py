"""Tests that the application actually starts.

The httpx test transport does not run FastAPI's lifespan, so every endpoint
test can pass while startup is broken. That is exactly what happened: a
logging misconfiguration raised on the first log line of `lifespan`, the
container exited, and nothing in the suite noticed.

These tests drive the lifespan directly. They need no database: startup only
configures logging, and shutdown disposes a connection pool that was never
opened.
"""

from __future__ import annotations

import structlog

from app.main import create_app


async def test_lifespan_completes_without_raising():
    app = create_app()
    async with app.router.lifespan_context(app):
        pass


async def test_startup_emits_a_log_line(capsys):
    app = create_app()
    async with app.router.lifespan_context(app):
        pass

    output = capsys.readouterr()
    assert "application.startup" in output.out + output.err
    structlog.reset_defaults()


async def test_shutdown_emits_a_log_line(capsys):
    app = create_app()
    async with app.router.lifespan_context(app):
        capsys.readouterr()  # discard the startup line

    output = capsys.readouterr()
    assert "application.shutdown" in output.out + output.err
    structlog.reset_defaults()


async def test_routes_are_mounted_after_startup():
    app = create_app()
    async with app.router.lifespan_context(app):
        paths = set(app.openapi()["paths"])

    assert "/health" in paths
    assert "/api/v1/auth/login" in paths
    assert "/api/v1/sites/geojson" in paths
