# ADR-0001: FastAPI over Django REST and Flask

**Status:** Accepted · **Date:** 2026-09-18

## Context

The brief allows Flask, Django or FastAPI. The API is JSON-only, serves a
separate React SPA, and its most interesting work is geospatial SQL rather than
server-rendered HTML.

## Decision

FastAPI, with SQLAlchemy 2.0 (async), GeoAlchemy2 and Alembic.

## Why

- **Validation is the contract.** Pydantic models validate requests and
  serialise responses from one definition. The GeoJSON validator in
  `schemas/geojson.py` rejects an unclosed ring with a precise field path
  before any database work happens.
- **The OpenAPI spec is free.** `/docs` is a working, explorable API for a
  reviewer. With Flask that is a separate, hand-maintained artefact that goes
  stale.
- **Typing all the way down.** Type hints are load-bearing (they _are_ the
  validation), which makes `mypy --strict` worth running instead of a
  formality.
- **Async fits the workload.** Requests are dominated by waiting on PostGIS.
  One async process handles concurrent requests without a thread per request.

## Rejected

**Django + DRF + GeoDjango.** Real advantages: an admin panel, batteries-included
auth, mature GeoDjango. Rejected because most of that is weight we would not
use — no server-rendered pages, no need for the admin — and GeoDjango's ORM
abstracts PostGIS in ways that make a raw `ST_PointOnSurface` awkward. The
demonstrable geospatial work would have been harder to show, not easier.

**Flask + SQLAlchemy.** Minimal and flexible, but validation, serialisation,
API docs and dependency injection all become hand-written code — more surface
to get wrong, and nothing gained over FastAPI for this shape of application.

## Cost

- A smaller ecosystem than Django: no admin, no built-in user management.
  `app/api/v1/endpoints/auth.py` exists because of this.
- SQLAlchemy 2.0's async API is newer and less documented than the sync one.
- No batteries for background jobs; metric backfill runs inline.
