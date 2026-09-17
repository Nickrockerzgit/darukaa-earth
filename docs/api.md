# API reference

Base URL: `{API_URL}/api/v1`. Interactive documentation is served at
`{API_URL}/docs` in every environment except production.

Authentication is `Authorization: Bearer <access_token>` on every endpoint
except `/auth/register`, `/auth/login`, `/auth/refresh` and the health probes.

## Error envelope

Every failure — domain error, validation error or unhandled exception — returns
the same shape:

```json
{
  "error": "not_found",
  "message": "Project not found.",
  "details": { "project_id": "0193..." },
  "request_id": "5f2c9c1e-..."
}
```

`request_id` also appears in the `X-Request-ID` response header and on every log
line for that request, so a user-reported failure is greppable in the logs.

| `error`                | Status | Meaning                                                |
| ---------------------- | ------ | ------------------------------------------------------ |
| `validation_error`     | 422    | Payload failed validation, or violated a business rule |
| `invalid_geometry`     | 422    | The polygon is unrepairable, or below the minimum area |
| `authentication_error` | 401    | Missing, invalid or expired credentials                |
| `permission_denied`    | 403    | Authenticated, but not allowed                         |
| `not_found`            | 404    | Missing, **or owned by someone else**                  |
| `conflict`             | 409    | Duplicate unique key                                   |
| `internal_error`       | 500    | Unhandled; details are never leaked                    |

A resource owned by another user returns **404, not 403**. A 403 would confirm
the id exists, which turns the endpoint into an existence oracle.

## Authentication

### `POST /auth/register` → 201

```json
{ "email": "you@org.earth", "password": "CorrectHorse123", "full_name": "Ada" }
```

Password rules, enforced identically in the browser and on the server: 10–72
characters, with at least one lowercase letter, one uppercase letter and one
digit. The 72-byte ceiling is bcrypt's input limit — beyond it bcrypt silently
truncates, which would make two long passwords sharing a prefix interchangeable.

Returns `{ user, tokens }`.

### `POST /auth/login` → 200

```json
{ "email": "you@org.earth", "password": "CorrectHorse123" }
```

An unknown email and a wrong password return the identical 401 body, so the
endpoint cannot be used to enumerate accounts.

### `POST /auth/refresh` → 200

```json
{ "refresh_token": "eyJ..." }
```

Rotates: the presented token is revoked and a new pair is issued. Replaying a
rotated token returns 401. An access token presented here is rejected — the
`type` claim is checked.

### `POST /auth/logout` → 200

With a `refresh_token`, revokes that one. With no body, revokes every live token
for the user ("sign out everywhere").

### `GET /auth/me` → 200

The signed-in user. Called on app boot to revalidate a restored session.

## Projects

### `GET /projects` → `Page<ProjectWithStats>`

| Query          | Type                                           | Default |
| -------------- | ---------------------------------------------- | ------- |
| `page`         | int ≥ 1                                        | 1       |
| `size`         | int 1–100                                      | 20      |
| `status`       | `draft` \| `active` \| `archived`              | —       |
| `project_type` | `carbon` \| `biodiversity` \| `mixed`          | —       |
| `search`       | string, case-insensitive substring of the name | —       |

Each item carries `site_count` and `total_area_hectares`, computed by a
`LEFT JOIN … GROUP BY` in the same query. Rendering the dashboard is one round
trip regardless of how many projects are on the page.

```json
{ "items": [...], "total": 42, "page": 1, "size": 20, "pages": 3 }
```

### `POST /projects` → 201

```json
{
  "name": "Sundarbans Mangrove Restoration",
  "description": "Blue carbon restoration in the delta.",
  "project_type": "mixed",
  "status": "active",
  "start_date": "2022-04-01"
}
```

`start_date` seeds the metric backfill window for sites added later.

### `GET` / `PATCH` / `DELETE /projects/{id}`

`PATCH` is a partial update: omitted fields are untouched (`exclude_unset`).
`DELETE` cascades to sites and their metric history and returns 204.

### `GET /projects/{id}/summary`

```json
{
  "project_id": "...",
  "site_count": 3,
  "total_area_hectares": 1450.25,
  "latest_metrics": { "carbon_sequestered_tco2e": 812.4, "ndvi": 0.61 }
}
```

`latest_metrics` takes each site's most recent sample (`DISTINCT ON`) and then
applies each metric's own aggregation across sites — summing flows, averaging
stocks.

## Sites

### `GET /projects/{id}/sites` → `Page<SiteListItem>`

Geometry is **omitted** from list items. A list of 100 polygons is megabytes; a
list of 100 names and centroids is kilobytes. Fetch the full geometry from
`/sites/{id}` when it is needed, or the whole collection from `/sites/geojson`.

### `POST /projects/{id}/sites` → 201

```json
{
  "name": "Gosaba Block North",
  "description": "Tidal mangrove replanting.",
  "geometry": {
    "type": "Polygon",
    "coordinates": [
      [
        [88.78, 22.14],
        [88.9, 22.14],
        [88.9, 22.24],
        [88.78, 22.24],
        [88.78, 22.14]
      ]
    ]
  }
}
```

The geometry is exactly what Mapbox GL Draw emits. On the way in it is:

1. validated (closed rings, coordinates within lon/lat bounds),
2. repaired if self-intersecting, and promoted to `MultiPolygon`,
3. measured — `ST_Area(::geography)` for hectares, `ST_PointOnSurface` for the
   centroid,
4. rejected if under 100 m² (a mis-click, not a parcel),
5. backfilled with metric history from the project's start date to today.

The response echoes the stored geometry as `MultiPolygon`, plus `area_hectares`
and `centroid`.

### `GET /sites/geojson` → `FeatureCollection`

The map's single data source. Optional `?project_id=` narrows it.

```json
{
  "type": "FeatureCollection",
  "bbox": [88.62, 22.02, 88.90, 22.27],
  "features": [
    {
      "type": "Feature",
      "id": "0193...",
      "geometry": { "type": "MultiPolygon", "coordinates": [...] },
      "properties": {
        "site_id": "0193...",
        "project_id": "0192...",
        "name": "Gosaba Block North",
        "project_name": "Sundarbans Mangrove Restoration",
        "project_type": "mixed",
        "status": "active",
        "area_hectares": 1120.5
      }
    }
  ]
}
```

The `properties` are exactly what the Mapbox style expressions read, so colour,
labels and popups need no extra request. `bbox` comes from `ST_Extent`, so the
client can `fitBounds` without sweeping every coordinate. It is `null` when the
user has no sites.

### `GET` / `PATCH` / `DELETE /sites/{id}`

`PATCH` with a new `geometry` recomputes area and centroid; `PATCH` with only a
name leaves them untouched.

## Analytics

### `GET /metrics` → `MetricDefinition[]`

The catalogue, in display order. The client renders labels, units, ordering and
colour category from this, so metric keys are never hardcoded in the UI.

```json
{
  "id": 1,
  "key": "carbon_sequestered_tco2e",
  "label": "Carbon Sequestered",
  "unit": "tCO2e",
  "category": "carbon",
  "aggregation": "sum",
  "display_order": 10
}
```

### `GET /sites/{id}/analytics`

| Query                   | Type                                    | Default              |
| ----------------------- | --------------------------------------- | -------------------- |
| `metrics`               | repeated metric keys                    | the full catalogue   |
| `date_from` / `date_to` | `YYYY-MM-DD`                            | last 3 years → today |
| `interval`              | `day` \| `month` \| `quarter` \| `year` | `month`              |

```json
{
  "site_id": "...",
  "interval": "month",
  "date_from": "2022-09-01",
  "date_to": "2025-09-18",
  "series": [
    {
      "metric_key": "carbon_sequestered_tco2e",
      "label": "Carbon Sequestered",
      "unit": "tCO2e",
      "category": "carbon",
      "aggregation": "sum",
      "points": [{ "t": "2025-08-01", "v": 74.21 }]
    }
  ]
}
```

Buckets use `date_trunc`, and the aggregate follows each metric's declared
`aggregation`: flows are summed, stocks and indices are averaged. Requesting an
unknown metric key returns 422 listing the offending keys, rather than silently
returning fewer series than asked for.

### `GET /sites/{id}/analytics/summary`

The KPI-card payload: each metric's latest value, the preceding sample, and the
percent change between them. `change_pct` is `null` when there is no prior
sample or the baseline is zero — reporting infinite growth would be worse than
reporting nothing.

## Health

| Endpoint            | Purpose                                                                          |
| ------------------- | -------------------------------------------------------------------------------- |
| `GET /health`       | Liveness. Never touches the database                                             |
| `GET /health/ready` | Readiness. Queries `PostGIS_Lib_Version()`; 503 when the database is unreachable |

The deploy workflow polls `/health/ready`, so a green deploy means the API is up
_and_ reached its database with PostGIS installed.
