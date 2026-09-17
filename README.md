# Darukaa.Earth

A full-stack geospatial analytics platform for carbon and biodiversity projects.
Draw a project boundary on a map, and the platform tracks carbon sequestration,
vegetation and biodiversity across it, month by month — so a claim is always
traceable to a specific polygon and a specific date.

|                |                                           |
| -------------- | ----------------------------------------- |
| **Live demo**  | _add the Vercel URL here_                 |
| **API docs**   | _add_ `{API_URL}/docs`                    |
| **Demo login** | `admin@darukaa.earth` / `DarukaaDemo123!` |

---

## Contents

- [What it does](#what-it-does)
- [Tech stack](#tech-stack)
- [Architecture](#architecture)
- [Database schema](#database-schema)
- [Running it locally](#running-it-locally)
- [CI/CD pipeline](#cicd-pipeline)
- [Code quality](#code-quality)
- [Testing](#testing)
- [Data: what is real and what is not](#data-what-is-real-and-what-is-not)
- [Key decisions and trade-offs](#key-decisions-and-trade-offs)
- [Deployment](#deployment)
- [Project layout](#project-layout)

---

## What it does

**Authentication** — register and sign in. JWT access tokens (15 minutes) paired
with one-use rotating refresh tokens (7 days), stored server-side as SHA-256
digests.

**Projects** — create, search, filter and archive monitoring programmes. Each
card shows its site count and total area, computed in the same query that lists
it.

**Sites** — draw a polygon on the map and it becomes a monitored site. On the
way in it is validated, repaired if self-intersecting, measured on the spheroid
(real hectares, not square degrees), and backfilled with three years of metric
history.

**Analytics** — click a site for KPI cards with period-over-period change and
Highcharts time series for six metrics, switchable between monthly, quarterly
and yearly aggregation. Flows (carbon sequestered) sum across periods; stocks
and indices (canopy cover, NDVI) average — the correct behaviour is stored
alongside each metric, so the API and the UI cannot disagree.

**Portfolio map** — every site across every project on one canvas, colour-coded
by project type, with analytics in a side drawer.

---

## Tech stack

| Layer         | Choice                                             | Why                                                                                                                   |
| ------------- | -------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------- |
| Frontend      | React 18, Vite, TypeScript (strict)                | Fast builds; strict typing makes a contract change a build failure                                                    |
| Map           | Mapbox GL JS via `react-map-gl` + `mapbox-gl-draw` | Required by the brief; drawing and data-driven styling built in                                                       |
| Charts        | Highcharts + `highcharts-react-official`           | Required by the brief; strong time-series and multi-axis support                                                      |
| Server state  | TanStack Query                                     | Caching, deduplication and invalidation are the real problem                                                          |
| Session state | Zustand                                            | One small global slice; no Redux ceremony                                                                             |
| Styling       | Tailwind CSS v4 + hand-built primitives            | Full design control, small bundle, no component-library lock-in                                                       |
| Backend       | FastAPI (Python 3.12)                              | Pydantic validation, free OpenAPI docs, async, `mypy --strict` clean — [ADR-0001](docs/decisions/ADR-0001-fastapi.md) |
| ORM           | SQLAlchemy 2.0 (async) + GeoAlchemy2               | Typed ORM with first-class PostGIS types                                                                              |
| Database      | PostgreSQL 16 + PostGIS 3.4                        | Required by the brief; the geospatial work is genuinely PostGIS work                                                  |
| Migrations    | Alembic                                            | Reversibility and drift are both enforced in CI                                                                       |
| Hosting       | Render (API + database), Vercel (web)              | Free tiers, Docker-native, GitHub Actions integration                                                                 |

---

## Architecture

```
  Browser ──HTTPS──▶ Vercel (static SPA) ──JSON/JWT──▶ Render (FastAPI) ──asyncpg──▶ PostgreSQL 16 + PostGIS

  Mapbox tiles are fetched by the browser directly and never transit our API.
```

The backend has four layers, each of which may only call the one below it:

```
Router      app/api/v1/endpoints/   HTTP only: paths, status codes, DI
   ↓
Service     app/services/           Business rules, ownership, transactions
   ↓
Repository  app/repositories/       Every SQL statement, including PostGIS
   ↓
Model       app/models/             Tables, relationships, constraints
```

A service raises `NotFoundError`; it does not know that becomes HTTP 404. One
exception handler performs that translation, so the status code for "missing
project" is defined once and services are testable without an HTTP client.

The frontend is feature-sliced: everything the projects feature needs lives
under `features/projects/`, so a change to it touches one directory.

**Full detail, including a request traced end to end:
[`docs/architecture.md`](docs/architecture.md).**

---

## Database schema

```
users ──1:N──▶ projects ──1:N──▶ sites ──1:N──▶ site_metrics ──N:1──▶ metric_definitions
  │
  └──1:N──▶ refresh_tokens
```

| Table                | Purpose               | Notable                                                  |
| -------------------- | --------------------- | -------------------------------------------------------- |
| `users`              | Accounts              | bcrypt (cost 12), case-insensitive unique email          |
| `refresh_tokens`     | Session revocation    | Stores only the SHA-256 digest                           |
| `projects`           | Monitoring programmes | GIN trigram index for `ILIKE` search                     |
| `sites`              | Land parcels          | `geometry(MultiPolygon, 4326)` + **GIST index**          |
| `metric_definitions` | Metric catalogue      | Carries each metric's aggregation semantics              |
| `site_metrics`       | The time series       | `UNIQUE (site, metric, date)` makes ingestion idempotent |

Three choices worth defending here:

**Geometry is `MultiPolygon` in SRID 4326**, matching GeoJSON and Mapbox exactly,
so nothing reprojects at the API boundary. A single Polygon is promoted to a
one-member MultiPolygon on write, so the column has one geometry type and no
downstream code branches.

**Area is computed as `ST_Area(geometry::geography) / 10000`.** On a 4326
`geometry`, `ST_Area` returns _square degrees_ — meaningless, since a degree of
longitude is 111 km at the equator and 0 km at the pole. The `geography` cast
measures on the spheroid in real metres. An integration test asserts that a
1 km × 1 km square at the equator comes back as ~100 ha.

**Metrics live in a narrow time-series table, not wide columns.** Adding "soil
organic carbon" is one row in `metric_definitions`, not a schema migration plus
a backend release plus a frontend release. The cost is one join, which the
composite index makes cheap — [ADR-0003](docs/decisions/ADR-0003-narrow-metrics-table.md).

**Full schema with every column, index and rationale:
[`docs/database.md`](docs/database.md).**

---

## Running it locally

### Prerequisites

Docker Desktop, Node 20+ with pnpm (`corepack enable`), Python 3.12, and a free
[Mapbox token](https://account.mapbox.com/access-tokens/) (starts with `pk.`).

### Quick start

```bash
git clone <repository-url>
cd darukaa-earth

cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
# Put your Mapbox token in frontend/.env as VITE_MAPBOX_TOKEN

pnpm install        # installs dependencies and the Husky hooks
make dev            # PostGIS + API + web, with hot reload
```

In a second terminal:

```bash
make seed           # demo user, 5 projects, 10 sites, 3 years of metrics
```

|          |                                          |
| -------- | ---------------------------------------- |
| Web      | http://localhost:5173                    |
| API docs | http://localhost:8000/docs               |
| PostGIS  | `localhost:5433` (`darukaa` / `darukaa`) |

Port **5433**, not 5432, because 5432 is commonly taken by a native PostgreSQL
install.

Sign in with `admin@darukaa.earth` / `DarukaaDemo123!`.

### Running natively instead

```bash
make db                                   # PostGIS only

cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
alembic upgrade head
python -m app.db.seed
uvicorn app.main:app --reload

# and in another terminal
pnpm --filter darukaa-web dev
```

### Everyday commands

```bash
make help            # list every target
make lint            # ruff + mypy + eslint + tsc + prettier
make format          # auto-fix formatting everywhere
make test            # backend and frontend suites
make migration m="add soil carbon"   # autogenerate a migration
make migrate
```

**The app runs without a Mapbox token.** The map area renders setup
instructions instead of a blank grey canvas, and every other feature works.

---

## CI/CD pipeline

Three gates, fastest first.

### 1. Pre-commit — Husky + lint-staged

Installed automatically by `pnpm install`.

| Hook         | What it does                                                                                                                  |
| ------------ | ----------------------------------------------------------------------------------------------------------------------------- |
| `pre-commit` | `lint-staged`: ESLint `--fix` + Prettier on staged TS/TSX; Ruff check + format on staged Python; Prettier on JSON/MD/YAML/CSS |
| `commit-msg` | `commitlint` — Conventional Commits with an allow-list of scopes                                                              |
| `pre-push`   | `tsc --noEmit` and the backend unit suite                                                                                     |

Scoping to _staged_ files is what keeps this fast enough to survive. Linting the
whole repository on every commit is how teams end up with `--no-verify` in their
muscle memory.

### 2. GitHub Actions

| Workflow        | Jobs                                                                                                                                                                |
| --------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Backend CI**  | `ruff check` · `ruff format --check` · `mypy --strict` · `pytest` against a **PostGIS service container** (coverage ≥ 80%) · migration up/down/up **+ drift check** |
| **Frontend CI** | `prettier --check` · `eslint --max-warnings=0` · `tsc --noEmit` · `vitest --coverage` · production build with bundle-size reporting                                 |
| **Deploy**      | Triggered by `workflow_run` on **both** CI workflows succeeding on `main`                                                                                           |
| **CodeQL**      | Security analysis for TypeScript and Python, per PR and weekly                                                                                                      |

Two things in Backend CI are worth pointing at:

**A real PostGIS service container.** Tests run against the same extension set
as production, so a dropped `geography` cast or a missing GIST index fails in CI
rather than on the demo URL. Mocking the database would test the mock.

**The migration job proves three things at once** — that migrations apply from
nothing, that they are reversible (a migration you cannot undo is one you cannot
roll back during an incident), and that the models have not drifted from the
schema. The drift check autogenerates a throwaway revision and fails if it
contains any operation, which catches the most common real mistake: editing a
model and forgetting the migration.

### 3. Deploy

`workflow_run` rather than `push` is what makes the gate real — a `push` trigger
would race CI and could ship a commit whose tests were still running.

1. **API → Render.** Render builds the Dockerfile and runs
   `alembic upgrade head` as its pre-deploy command, so the schema is applied
   before the new instance takes traffic. The workflow then polls
   `/health/ready`, which queries `PostGIS_Lib_Version()` — a green deploy means
   the API is up _and_ reached its database with PostGIS installed.
2. **Web → Vercel.** `vercel pull / build / deploy --prod`, then a smoke request.
   It `needs: deploy-api`, so the frontend is never pointed at an API that has
   not finished migrating.

**Required secrets** — `RENDER_DEPLOY_HOOK_URL`, `VERCEL_TOKEN`,
`VERCEL_ORG_ID`, `VERCEL_PROJECT_ID`.
**Required variables** — `API_URL`, `WEB_URL`.

**Full pipeline walkthrough: [`docs/cicd.md`](docs/cicd.md).**

---

## Code quality

| Tool                                             | Scope                                                | Enforced                |
| ------------------------------------------------ | ---------------------------------------------------- | ----------------------- |
| Ruff                                             | Python lint + format (replaces flake8, isort, black) | pre-commit, CI          |
| mypy `--strict`                                  | Python types                                         | pre-commit-adjacent, CI |
| ESLint 9 (`strictTypeChecked`)                   | TypeScript                                           | pre-commit, CI          |
| TypeScript `strict` + `noUncheckedIndexedAccess` | Types                                                | pre-push, CI            |
| Prettier                                         | Everything                                           | pre-commit, CI          |
| commitlint                                       | Commit messages                                      | commit-msg              |
| pytest + Vitest coverage gates                   | Tests                                                | CI                      |
| CodeQL                                           | Security                                             | CI                      |

Ruff runs a deliberately wide rule set — including `S` (bandit security), `B`
(bugbear), `ASYNC`, `PTH`, `ERA` (commented-out code) and `D` (docstrings). Every
exception is listed in `pyproject.toml` with the reason. ESLint runs with
`--max-warnings=0`: a tolerated warning is a warning nobody will ever fix.

---

## Testing

```bash
make test            # everything
make test-backend    # pytest with coverage
make test-frontend   # vitest with coverage
```

| Suite               | Count | Approach                                                                        |
| ------------------- | ----- | ------------------------------------------------------------------------------- |
| Backend unit        | 50    | Security primitives, geometry conversion, the synthetic provider                |
| Backend integration | 68    | Every endpoint against **real PostGIS**, each test in a rolled-back transaction |
| Frontend            | 144   | Vitest + Testing Library, with **MSW** intercepting at the network layer        |

The tests assert behaviour that would be a bug, not that endpoints return 200:

- An unknown email and a wrong password return **identical** responses, so login
  cannot enumerate accounts.
- A rotated refresh token cannot be replayed.
- A refresh token cannot be used as a bearer credential.
- Another user's project reads as 404, not 403.
- A self-intersecting "bow-tie" polygon is repaired; a 1 m² polygon is rejected.
- Rolling months into years **sums** carbon and **averages** NDVI.
- Eight keystrokes in the search box produce fewer than four requests.

`src/features/map/**` is excluded from frontend coverage: `mapbox-gl` needs
WebGL, which jsdom does not implement, so those modules cannot execute in a unit
test. Rather than write hollow tests for coverage's sake, they are excluded
explicitly and covered by a scripted manual walkthrough in
[`docs/testing.md`](docs/testing.md). The page _around_ the map is tested with
`MapView` stubbed.

---

## Data: what is real and what is not

**The metric values are synthetic.** They are generated, not measured. This is
stated plainly because a carbon platform that is vague about data provenance is
worse than useless.

The brief permits mocks and asks for the choice to be documented. The full
reasoning is in [ADR-0004](docs/decisions/ADR-0004-synthetic-analytics.md); the
short version:

- **A reviewer will draw a polygon somewhere no dataset covers.** That is the
  core interaction. A fixed real-world dataset would produce an empty chart for
  a polygon over Rajasthan or Ohio, and the feature would look broken.
- **A live Earth-observation pipeline would make the demo fragile** — service
  account credentials, quotas, and results that take tens of seconds to minutes.

**What the generator does guarantee:**

- **Deterministic.** Seeded from the site's UUID, so the same site always
  produces the same series. Screenshots stay valid, tests assert exact values,
  and two people demoing see identical numbers.
- **Physically structured, not noise.** Carbon scales with area; latitude sets
  seasonal amplitude and phase (a Patagonian site peaks in January, a tropical
  one barely cycles); growth follows a saturating exponential, because
  restoration biomass rises fast then plateaus. The 7.5 tCO2e/ha/yr baseline is
  the mid-range of IPCC 2019 Refinement Vol. 4 Ch. 4 tier-1 defaults for
  reforestation.
- **Bounded.** NDVI is clamped to [0, 1], percentages to [0, 100]. A
  plausible-looking impossible value is worse than an obviously fake one.

**Replaceable in one line.** Every number reaches the database through
`AnalyticsProvider`. A real Sentinel-2 pipeline is a second implementation of
that interface — the API, repositories, schemas and the whole frontend are
unaffected.

The demo _geography_ is real: the seeded polygons are bounding boxes of actual
landscapes — the Sundarbans, the Western Ghats, the Rio Tapajós, Santa Cruz
province, Finnish Lapland — chosen to span both hemispheres so the
latitude-driven seasonality is visible side by side.

---

## Key decisions and trade-offs

Each of these is a full ADR in [`docs/decisions/`](docs/decisions/), with what
was rejected and what it costs.

| Decision                                                                    | Rejected                     | Cost accepted                                 |
| --------------------------------------------------------------------------- | ---------------------------- | --------------------------------------------- |
| [FastAPI](docs/decisions/ADR-0001-fastapi.md)                               | Django REST, Flask           | No admin panel; auth written by hand          |
| [PostGIS geography for area](docs/decisions/ADR-0002-postgis-geometry.md)   | Web Mercator, Shapely        | Approximate near the poles                    |
| [Narrow metrics table](docs/decisions/ADR-0003-narrow-metrics-table.md)     | Wide columns, JSONB          | One join per analytics query                  |
| [Synthetic analytics](docs/decisions/ADR-0004-synthetic-analytics.md)       | Earth Engine, static dataset | The numbers are not measurements              |
| [Hand-written API types](docs/decisions/ADR-0005-hand-written-api-types.md) | `openapi-typescript`         | The contract is stated twice                  |
| [Tokens in localStorage](docs/decisions/ADR-0006-token-storage.md)          | httpOnly cookie              | XSS would yield the tokens                    |
| [Mapbox layers over components](docs/decisions/ADR-0007-mapbox-layers.md)   | A component per site         | Mapbox expression syntax is a second language |

### What this is not

- **No background jobs.** Metric backfill runs inline (~50 ms for three years).
  A real ingestion pipeline needs a queue.
- **No rate limiting.** The login endpoint is unthrottled; in production this
  belongs at the edge rather than in application code.
- **Single region**, and the free Render tier sleeps after inactivity — the
  first request after a quiet period takes ~30 seconds.

---

## Deployment

### Backend → Render

1. **New → Blueprint**, point it at this repository. `render.yaml` provisions the
   PostgreSQL 16 database and the Dockerised web service.
2. Enable the **PostGIS** extension on the database (Render's dashboard, or
   `CREATE EXTENSION postgis;`). Migration `0001` then enables `pg_trgm` and
   `pgcrypto`.
3. Set `CORS_ORIGINS` to the Vercel production domain. `SECRET_KEY` is generated
   automatically and `DATABASE_URL` is wired from the database.
4. Copy the **Deploy Hook URL** into the `RENDER_DEPLOY_HOOK_URL` repository
   secret.

### Frontend → Vercel

1. Import the repository. `vercel.json` sets the build command, output directory,
   SPA rewrites and security headers.
2. Environment variables: `VITE_API_BASE_URL` (the Render URL) and
   `VITE_MAPBOX_TOKEN`.
3. Run `vercel link` locally and copy `orgId` / `projectId` from
   `.vercel/project.json` into the `VERCEL_ORG_ID` / `VERCEL_PROJECT_ID` secrets.

### Then

Set the `API_URL` and `WEB_URL` repository variables, and protect `main`:
require a pull request and both CI workflows.

---

## Project layout

```
darukaa-earth/
├── .github/workflows/    ci-backend · ci-frontend · deploy · codeql
├── .husky/               pre-commit · commit-msg · pre-push
├── backend/
│   ├── app/
│   │   ├── api/v1/endpoints/   auth · projects · sites · analytics · health
│   │   ├── core/               config · security · logging · exceptions
│   │   ├── db/                 base · session · seed
│   │   ├── models/             user · project · site · metric · refresh_token
│   │   ├── schemas/            Pydantic DTOs, including typed GeoJSON
│   │   ├── repositories/       every SQL statement
│   │   ├── services/           business logic
│   │   │   └── providers/      the AnalyticsProvider seam
│   │   └── utils/geo.py        GeoJSON ⇄ Shapely ⇄ PostGIS
│   ├── alembic/versions/       0001 extensions · 0002 schema · 0003 catalogue
│   └── tests/                  unit/ · integration/
├── frontend/src/
│   ├── app/                    router · providers · query client
│   ├── features/               auth · projects · sites · map · analytics
│   ├── components/             ui/ · layout/ · common/
│   ├── lib/                    apiClient · mapbox · highcharts · format
│   └── types/                  the API contract
├── docs/                       architecture · database · api · cicd · testing
│   └── decisions/              ADR-0001 … ADR-0007
├── docker-compose.yml
├── render.yaml · vercel.json
└── Makefile
```

---

Built for the Darukaa.Earth full-stack hackathon.
