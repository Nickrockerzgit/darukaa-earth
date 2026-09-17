"""Tests for managed-Postgres URL normalisation.

These pin the three things that silently break a deployment to Neon, Supabase
or any other PgBouncer-fronted Postgres.
"""

from __future__ import annotations

import pytest

from app.db.session import ConnectionSettings

NEON_DIRECT = (
    "postgresql+asyncpg://user:pw@ep-cool-name-123456.ap-southeast-1.aws.neon.tech"
    "/darukaa?sslmode=require&channel_binding=require"
)
NEON_POOLED = (
    "postgresql+asyncpg://user:pw@ep-cool-name-123456-pooler.ap-southeast-1.aws.neon.tech"
    "/darukaa?sslmode=require"
)
LOCAL = "postgresql+asyncpg://darukaa:darukaa@localhost:5433/darukaa"


class TestParameterStripping:
    def test_removes_libpq_only_parameters(self):
        # Left in the URL, asyncpg raises "unexpected keyword argument 'sslmode'".
        url = ConnectionSettings(NEON_DIRECT).url
        assert "sslmode" not in url
        assert "channel_binding" not in url

    def test_keeps_the_rest_of_the_url_intact(self):
        url = ConnectionSettings(NEON_DIRECT).url
        assert url.startswith("postgresql+asyncpg://user:pw@")
        assert "neon.tech" in url
        assert url.endswith("/darukaa")

    def test_preserves_parameters_asyncpg_understands(self):
        settings = ConnectionSettings(f"{LOCAL}?sslmode=require&timeout=10")
        assert "timeout=10" in settings.url
        assert "sslmode" not in settings.url

    def test_leaves_a_plain_local_url_alone(self):
        assert ConnectionSettings(LOCAL).url == LOCAL


class TestTls:
    @pytest.mark.parametrize("mode", ["require", "verify-ca", "verify-full", "prefer"])
    def test_ssl_is_requested_when_the_provider_asks_for_it(self, mode: str):
        settings = ConnectionSettings(f"{NEON_DIRECT.split('?', maxsplit=1)[0]}?sslmode={mode}")
        assert settings.connect_args["ssl"] is True

    def test_no_ssl_argument_for_a_plain_local_connection(self):
        assert "ssl" not in ConnectionSettings(LOCAL).connect_args

    def test_sslmode_disable_does_not_force_tls(self):
        settings = ConnectionSettings(f"{LOCAL}?sslmode=disable")
        assert "ssl" not in settings.connect_args


class TestPooledEndpoints:
    def test_detects_a_neon_pooler_host(self):
        assert ConnectionSettings(NEON_POOLED).is_pooled

    def test_direct_endpoint_is_not_treated_as_pooled(self):
        assert not ConnectionSettings(NEON_DIRECT).is_pooled

    def test_disables_the_prepared_statement_cache_when_pooled(self):
        # PgBouncer in transaction mode moves the client between backends, so a
        # cached prepared statement can land on one that has never seen it.
        assert ConnectionSettings(NEON_POOLED).connect_args["statement_cache_size"] == 0

    def test_keeps_the_statement_cache_on_a_direct_connection(self):
        assert "statement_cache_size" not in ConnectionSettings(NEON_DIRECT).connect_args

    def test_detects_a_supabase_pooler_host(self):
        url = "postgresql+asyncpg://u:p@aws-0-ap-south-1.pooler.supabase.com:6543/postgres"
        assert ConnectionSettings(url).is_pooled

    def test_local_connection_is_not_pooled(self):
        assert not ConnectionSettings(LOCAL).is_pooled
