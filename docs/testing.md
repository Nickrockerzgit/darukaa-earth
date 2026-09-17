# Testing

## What is tested, and how

| Suite               | Tool                           | Covers                                                           |
| ------------------- | ------------------------------ | ---------------------------------------------------------------- |
| Backend unit        | pytest                         | Security primitives, geometry conversion, the synthetic provider |
| Backend integration | pytest + real PostGIS          | Every endpoint, against the real database                        |
| Frontend unit       | Vitest                         | Formatting, geometry, chart option builders, the auth store      |
| Frontend component  | Vitest + Testing Library + MSW | Pages and forms against a mocked API                             |

```bash
make test           # everything
make test-backend   # pytest with coverage
make test-frontend  # vitest with coverage
```

## Backend

### A real database, not a mock

Integration tests run against PostGIS — a service container in CI, the compose
container locally. Mocking the database would test the mock: the interesting
behaviour here _is_ the SQL. `test_computes_area_in_hectares_on_the_spheroid`
asserts that a 1 km × 1 km square at the equator measures ~100 ha, which is only
true if the `geography` cast is present. Against a mock it would pass either way.

### Schema by migration

`conftest.py` builds the test schema by running the real Alembic migrations
once per session. It costs a couple of seconds and buys a genuine guarantee that
`alembic upgrade head` produces the schema the code expects — a failure mode
that otherwise only appears in production.

### Isolation by transaction

Each test runs inside a transaction that is rolled back on teardown, with the
session joined via `create_savepoint`. Application code can call `commit()`
normally — the commit releases a savepoint, and the outer rollback still
discards everything. Tests never see each other's rows, and the suite is
re-runnable without a reset step.

### Coverage

Gated at **80%**, enforced by `--cov-fail-under=80` in `pyproject.toml`.
`app/main.py` and `app/db/seed.py` are excluded: the first is wiring exercised
by every integration test, the second is a developer script.

### What the tests actually assert

Not "the endpoint returns 200", but the behaviour that would be a bug:

- An unknown email and a wrong password return **identical** responses, so login
  cannot enumerate accounts.
- A rotated refresh token cannot be replayed.
- A refresh token cannot be used as a bearer credential.
- Another user's project reads as 404, not 403.
- A bow-tie polygon is repaired rather than rejected.
- A polygon under 100 m² is rejected as a mis-click.
- Rolling months into years **sums** carbon and **averages** NDVI.

## Frontend

### MSW, not mocked modules

Component tests intercept HTTP at the network layer with MSW, so the real
`apiClient` — interceptors, error normalisation and all — runs in the test. A
mocked `projectsApi` module would skip exactly the code most likely to be wrong.

It also lets tests assert on the request:

```ts
expect(requestedUrls.filter((url) => url.includes('search=')).length).toBeLessThan(4);
```

Eight keystrokes must not produce eight requests — that is the debounce, tested
through the user-visible behaviour rather than by reaching into a timer.

### Queries by role and label

Tests find elements the way a user or a screen reader does
(`getByRole('button', { name: 'Sign in' })`, `getByLabelText('Site name')`).
This keeps the accessibility wiring honest: if the label stops being associated
with the input, the test fails.

### Coverage

Thresholds in `vitest.config.ts`: 70% statements/lines/branches, 65% functions.

`src/features/map/**` is **excluded**. `mapbox-gl` requires WebGL, which jsdom
does not implement, so those modules cannot execute in a unit test at all.
Rather than write hollow tests for coverage's sake, they are excluded explicitly
and covered by the manual walkthrough below. The page _around_ the map is still
tested, with `MapView` stubbed — see `ProjectDetailPage.test.tsx`.

## Manual walkthrough (the map)

The one path automated tests cannot reach. Run before any release that touches
`src/features/map/`.

**Setup:** `make dev`, `make seed`, a Mapbox token in `frontend/.env`, sign in as
`admin@darukaa.earth`.

1. **Portfolio map** — open `/map`. Sites appear on five continents; the map
   fits their bounds automatically. Carbon, biodiversity and mixed projects show
   in three distinct colours matching the legend.
2. **Hover** — polygon fill brightens; the cursor becomes a pointer.
3. **Select** — click a polygon. The outline thickens, the analytics drawer opens
   on the right, and the KPI cards and charts match the site named in the header.
4. **Labels** — zoom past level 8. Site names appear, and overlapping labels are
   suppressed rather than stacking.
5. **Draw** — open a project, click _Draw a new site_, and place at least three
   corners. Double-click to close. The name form appears.
6. **Save** — name it and save. A toast reports the computed area, the polygon
   appears in the site list and on the map, and its analytics load with three
   years of history.
7. **Reject a mis-click** — draw a polygon a few metres across. The save is
   refused with "Site area must be at least 100 m²", and the form stays open
   with the typed name intact.
8. **Repair** — draw a deliberate bow-tie (cross your own edges). It saves, and
   the stored polygon renders without self-intersection.
9. **No token** — unset `VITE_MAPBOX_TOKEN` and reload. The map area shows setup
   instructions rather than a blank grey canvas, and the rest of the app works.

## Adding a test

- **A bug fix** starts with a failing test that reproduces it.
- **A new endpoint** gets an integration test for the happy path, the
  unauthorised path, and the ownership boundary.
- **A new component** gets a test for its empty, loading and error states —
  those are the states most likely to ship broken, because they are the ones a
  developer sees least.
