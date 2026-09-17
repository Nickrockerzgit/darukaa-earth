# Architecture

## The shape of the system

```
                      ┌──────────────────────────────┐
  Browser  ──HTTPS──▶ │  Vercel (static SPA)         │
                      │  React 18 · Vite · TypeScript│
                      └──────────────┬───────────────┘
                                     │  JSON over HTTPS
                                     │  Authorization: Bearer <JWT>
                                     ▼
                      ┌──────────────────────────────┐
                      │  Render (Docker web service) │
                      │  FastAPI · SQLAlchemy 2.0    │
                      └──────────────┬───────────────┘
                                     │  asyncpg
                                     ▼
                      ┌──────────────────────────────┐
                      │  Render PostgreSQL 16        │
                      │  + PostGIS 3.4               │
                      └──────────────────────────────┘

  Mapbox tiles are fetched by the browser directly from Mapbox; they never
  transit our API.
```

Two deployables, one database. The frontend is a static bundle, so it is cheap
to serve from the edge and has no server-side state to get out of sync. All
state lives in PostgreSQL.

## Backend layering

Each request moves through four layers, and each layer may only call the one
below it:

| Layer          | Directory               | Responsibility                                                            | Must not                       |
| -------------- | ----------------------- | ------------------------------------------------------------------------- | ------------------------------ |
| **Router**     | `app/api/v1/endpoints/` | HTTP concerns: paths, status codes, dependency injection, response models | Contain business rules         |
| **Service**    | `app/services/`         | Business rules, ownership checks, orchestration, transactions             | Import SQLAlchemy or `fastapi` |
| **Repository** | `app/repositories/`     | Every SQL statement, including the PostGIS functions                      | Make authorisation decisions   |
| **Model**      | `app/models/`           | Table definitions, relationships, constraints                             | Contain logic                  |

Two supporting layers cut across:

- `app/schemas/` — Pydantic DTOs. Nothing that crosses the HTTP boundary is an
  ORM object, so a column added to a model is never accidentally exposed.
- `app/core/` — configuration, logging, security, the exception hierarchy.

**Why this matters in practice.** A service raises `NotFoundError`; it does not
know that maps to HTTP 404. One exception handler in `app/main.py` performs that
translation, so the status code for "missing project" is defined once and the
business layer is testable without an HTTP client.

### A request, end to end

`POST /api/v1/projects/{id}/sites` with a drawn polygon:

1. **Router** (`endpoints/projects.py`) resolves `CurrentUser` from the bearer
   token and validates the body against `SiteCreate`. A malformed ring is
   rejected here, by `schemas/geojson.py`, before any database work.
2. **Service** (`services/site_service.py`) confirms the caller owns the parent
   project, converts GeoJSON to a Shapely `MultiPolygon` (repairing
   self-intersections), and asks the repository for the geometry facts.
3. **Repository** (`repositories/site_repo.py`) runs
   `ST_Area(geometry::geography)` and `ST_PointOnSurface(geometry)` in a single
   round trip, so area is real square metres rather than square degrees.
4. **Service** rejects anything under 100 m², persists the row, then backfills
   the site's metric history through the `AnalyticsProvider` seam.
5. **Router** commits and serialises the result back to GeoJSON.

## Frontend structure

Feature-sliced rather than layer-sliced: everything the projects feature needs
lives under `features/projects/`, so a change to it touches one directory.

```
src/
├── app/         router, providers, query client   (composition root)
├── features/    auth · projects · sites · map · analytics
├── components/  ui/ (primitives) · layout/ · common/
├── lib/         apiClient · mapbox · highcharts · format · queryKeys
└── types/       the API contract, mirroring the Pydantic schemas
```

Within a feature: `api/` (HTTP), `hooks/` (React Query), `components/`,
`pages/`. A feature may import from `lib/` and `components/`, and from another
feature's `api/` (the projects API owns site creation, so `features/sites` uses
it) — but never from another feature's `components/`.

### State: three kinds, three tools

| Kind        | Tool           | Why                                                                                                                      |
| ----------- | -------------- | ------------------------------------------------------------------------------------------------------------------------ |
| Server data | TanStack Query | Caching, deduplication and invalidation are the actual problem; hand-rolling them with `useEffect` reproduces them badly |
| Session     | Zustand        | A tiny global slice read by the router guard and the HTTP client                                                         |
| UI          | `useState`     | Selected site, open modal, drawing mode — all local                                                                      |

There is no Redux store. The data that would live in one is server data, which
React Query already owns, and duplicating it into a client store is how the two
drift apart.

## Cross-cutting decisions

**The map is a Mapbox layer, not React components.** Site polygons come from one
GeoJSON `Source` styled by three layers. Hit-testing, label collision and
zoom-dependent styling happen on the GPU, so a project with 500 sites costs the
same number of React nodes as one with 5. Hover and selection are expressed as
Mapbox _feature state_, which repaints without touching the source data.

**One error envelope.** Every failure — a domain error, a Pydantic validation
error, or an unhandled exception — returns
`{error, message, details, request_id}`. The frontend has exactly one error
path (`toApiError`), and every log line carries the same `request_id`, so a
user-reported failure is greppable.

**Analytics behind an interface.** `AnalyticsProvider` (`services/providers/`)
is the only source of metric values. Today it is a deterministic synthetic
generator; a real Sentinel-2 pipeline would be a second implementation and a
one-line wiring change. See [ADR-0004](decisions/ADR-0004-synthetic-analytics.md).

**Ownership is the tenancy boundary.** Every project query is scoped by
`owner_id`, and every site query joins through `projects`. A project belonging
to someone else returns 404, not 403 — a 403 would confirm the id exists.

## Known limits

Honest about what this is not:

- **No background jobs.** Metric backfill runs inline when a site is created,
  which takes ~50 ms for three years of monthly data. A real ingestion pipeline
  would need a queue.
- **Tokens in `localStorage`.** See
  [ADR-0006](decisions/ADR-0006-token-storage.md) for the trade-off and the
  mitigations.
- **No rate limiting.** The login endpoint is unthrottled. In production this
  belongs at the edge (Cloudflare, Render's WAF) rather than in application code.
- **Single region.** Both services are deployed in one Render region.
