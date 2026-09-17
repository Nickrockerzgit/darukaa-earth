"""Tests for logging configuration.

These exist because a misconfiguration here is not a cosmetic problem: pairing
`add_logger_name` with a PrintLogger raised AttributeError on the first log
line, which is application startup, so the container never came up. Nothing
caught it locally because the log call only happens inside the FastAPI
lifespan, which the httpx test transport does not run.
"""

from __future__ import annotations

import logging

import pytest
import structlog

from app.core.logging import configure_logging, get_logger, request_id_ctx


@pytest.fixture(autouse=True)
def _reset_structlog():
    """Leave global structlog state as we found it."""
    yield
    structlog.reset_defaults()


@pytest.mark.parametrize("json_output", [True, False], ids=["json", "console"])
def test_a_configured_logger_can_actually_log(json_output: bool, capsys):
    # The regression: this raised AttributeError before the logger factory
    # was matched to the processors.
    configure_logging(level="INFO", json_output=json_output)
    get_logger("app.main").info("application.startup", environment="production")

    output = capsys.readouterr()
    assert "application.startup" in output.out + output.err


@pytest.mark.parametrize("json_output", [True, False], ids=["json", "console"])
def test_structured_fields_survive_rendering(json_output: bool, capsys):
    configure_logging(level="INFO", json_output=json_output)
    get_logger("app.main").info("http.request", status_code=200)

    captured = capsys.readouterr()
    rendered = captured.out + captured.err
    assert "status_code" in rendered
    assert "200" in rendered


def test_logger_name_is_attached(capsys):
    configure_logging(level="INFO", json_output=True)
    get_logger("app.services.site_service").info("site.created")

    assert "app.services.site_service" in capsys.readouterr().out


def test_request_id_is_attached(capsys):
    configure_logging(level="INFO", json_output=True)
    token = request_id_ctx.set("req-12345")
    try:
        get_logger("app.main").info("http.request")
    finally:
        request_id_ctx.reset(token)

    assert "req-12345" in capsys.readouterr().out


def test_request_id_defaults_outside_a_request(capsys):
    configure_logging(level="INFO", json_output=True)
    get_logger("app.main").info("worker.tick")

    assert "request_id" in capsys.readouterr().out


def test_exceptions_render_with_a_traceback(capsys):
    configure_logging(level="INFO", json_output=True)
    try:
        raise ValueError("boom")
    except ValueError:
        get_logger("app.main").exception("unhandled.exception")

    assert "boom" in capsys.readouterr().out


def test_level_filtering_drops_quieter_records(capsys):
    configure_logging(level="WARNING", json_output=True)
    logger = get_logger("app.main")
    logger.info("should.not.appear")
    logger.warning("should.appear")

    output = capsys.readouterr().out
    assert "should.not.appear" not in output
    assert "should.appear" in output


def test_reconfiguring_is_safe(capsys):
    # configure_logging runs at import time and again inside the lifespan.
    configure_logging(level="INFO", json_output=False)
    configure_logging(level="INFO", json_output=True)
    get_logger("app.main").info("application.startup")

    assert "application.startup" in capsys.readouterr().out


def test_noisy_stdlib_loggers_are_quietened():
    configure_logging(level="INFO", json_output=True)
    assert logging.getLogger("uvicorn.access").handlers == []
