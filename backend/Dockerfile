# syntax=docker/dockerfile:1.7

# ---------------------------------------------------------------------------
# Base: shared runtime layer.
# ---------------------------------------------------------------------------
FROM python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# GEOS is required by Shapely; curl backs the container health check.
RUN apt-get update \
    && apt-get install --no-install-recommends -y libgeos-c1v5 curl \
    && rm -rf /var/lib/apt/lists/*

# ---------------------------------------------------------------------------
# Builder: install dependencies into a virtualenv that can be copied wholesale.
# ---------------------------------------------------------------------------
FROM base AS builder

RUN apt-get update \
    && apt-get install --no-install-recommends -y build-essential libgeos-dev \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy only the manifest first, so dependency installation is cached and is not
# invalidated by an application code change.
#
# pyproject.toml stays the single source of truth for dependencies: a stub
# package satisfies the build, then the project itself is uninstalled, leaving
# exactly its dependency closure in the virtualenv. Duplicating the dependency
# list in this file instead would guarantee it drifts.
COPY pyproject.toml ./
RUN mkdir -p app && touch app/__init__.py \
    && python -m pip install --upgrade pip setuptools wheel \
    && python -m pip install . \
    && python -m pip uninstall --yes darukaa-api \
    && rm -rf app

# ---------------------------------------------------------------------------
# Dev: hot reload, dev dependencies, runs as root for bind-mount convenience.
# ---------------------------------------------------------------------------
FROM builder AS dev

ENV PATH="/opt/venv/bin:$PATH"

COPY . .
# Dev image: install the project editable, with its dev extras.
RUN python -m pip install -e ".[dev]"
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# ---------------------------------------------------------------------------
# Production: slim runtime, non-root, no build toolchain.
# ---------------------------------------------------------------------------
FROM base AS production

COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY alembic.ini ./
COPY alembic ./alembic
COPY app ./app

# A compromised process should not be able to write to the image.
RUN useradd --create-home --shell /usr/sbin/nologin --uid 10001 darukaa \
    && chown -R darukaa:darukaa /app
USER darukaa

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD curl --fail --silent http://localhost:8000/health || exit 1

# One worker: Render's free tier is single-CPU, and the app is I/O bound, so
# async concurrency inside one process beats several competing processes.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
