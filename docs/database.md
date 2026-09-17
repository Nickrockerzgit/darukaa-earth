# Database schema

PostgreSQL 16 with PostGIS 3.4. Migrations live in `backend/alembic/versions/`
and are the only way the schema changes; CI fails a pull request whose models
have drifted from its migrations.

## Entity relationships

```
users ──1:N──▶ projects ──1:N──▶ sites ──1:N──▶ site_metrics ──N:1──▶ metric_definitions
  │
  └──1:N──▶ refresh_tokens

Every FK is ON DELETE CASCADE: deleting a project removes its sites, and
deleting a site removes its metric history. There are no orphan rows.
```

## Tables

### `users`

| Column                      | Type           | Notes                                       |
| --------------------------- | -------------- | ------------------------------------------- |
| `id`                        | `uuid` PK      | `gen_random_uuid()`; non-enumerable in URLs |
| `email`                     | `varchar(320)` | Unique index; matched case-insensitively    |
| `hashed_password`           | `varchar(128)` | bcrypt, cost 12                             |
| `full_name`                 | `varchar(160)` | Nullable                                    |
| `role`                      | `user_role`    | `admin` \| `viewer`                         |
| `is_active`                 | `boolean`      | Soft deactivation without deleting history  |
| `created_at` / `updated_at` | `timestamptz`  | Database clock, not application clock       |

### `refresh_tokens`

Only the **SHA-256 digest** of each refresh token is stored, so a database leak
does not hand an attacker usable sessions. Rotation is one-use: refreshing
revokes the presented token and issues a new pair.

| Column       | Type                | Notes               |
| ------------ | ------------------- | ------------------- |
| `id`         | `uuid` PK           |                     |
| `user_id`    | `uuid` FK → `users` | `ON DELETE CASCADE` |
| `token_hash` | `varchar(64)`       | Unique              |
| `expires_at` | `timestamptz`       |                     |
| `revoked_at` | `timestamptz`       | Null while live     |

Index `ix_refresh_tokens_user_active (user_id, revoked_at)` serves
"revoke everything for this user" without a sequential scan.

### `projects`

| Column         | Type                | Notes                                 |
| -------------- | ------------------- | ------------------------------------- |
| `id`           | `uuid` PK           |                                       |
| `owner_id`     | `uuid` FK → `users` | The tenancy boundary                  |
| `name`         | `varchar(160)`      |                                       |
| `description`  | `text`              |                                       |
| `project_type` | `project_type`      | `carbon` \| `biodiversity` \| `mixed` |
| `status`       | `project_status`    | `draft` \| `active` \| `archived`     |
| `start_date`   | `date`              | Seeds the metric backfill window      |

Indexes:

- `ix_projects_owner_status (owner_id, status)` — the dashboard's exact filter.
- `ix_projects_name_trgm` — **GIN with `gin_trgm_ops`**. The search box issues
  `name ILIKE '%term%'`, and a leading wildcard makes a B-tree useless; a
  trigram index serves it.

### `sites`

| Column          | Type                           | Notes                              |
| --------------- | ------------------------------ | ---------------------------------- |
| `id`            | `uuid` PK                      |                                    |
| `project_id`    | `uuid` FK → `projects`         |                                    |
| `name`          | `varchar(160)`                 |                                    |
| `geometry`      | `geometry(MultiPolygon, 4326)` | WGS84, matching GeoJSON and Mapbox |
| `area_hectares` | `numeric(14,4)`                | Denormalised; `CHECK >= 0`         |
| `centroid`      | `geometry(Point, 4326)`        | `ST_PointOnSurface`                |

Three decisions worth defending:

1. **MultiPolygon, not Polygon.** A site can legitimately be several disjoint
   parcels. Storing one geometry type means no downstream code has to branch.
2. **`area_hectares` is stored, not computed per request.** It is written once
   from `ST_Area(geometry::geography) / 10000` — the `geography` cast measures
   on the spheroid in real metres, where the raw `geometry` would return square
   degrees whose size varies with latitude. Recomputing it on every list request
   would dominate the query cost of a value that only changes when the polygon
   does.
3. **`ST_PointOnSurface`, not `ST_Centroid`.** A centroid can fall outside a
   concave or multi-part polygon, which would make the map fly to open ocean.

Indexes:

- `ix_sites_geometry` — **GIST**. Without it, every spatial predicate
  (`ST_Intersects`, bounding-box queries, `ST_Extent`) is a sequential scan.
- `ix_sites_project_created (project_id, created_at)`.

### `metric_definitions`

The catalogue of measurable quantities. Shipped in migration `0003` because the
API contract and the frontend's chart configuration both depend on these keys
existing — it is reference data, not demo data.

| Column           | Type               | Notes                                      |
| ---------------- | ------------------ | ------------------------------------------ |
| `id`             | `smallint` PK      |                                            |
| `key`            | `varchar(64)`      | Unique; the stable public identifier       |
| `label` / `unit` | `varchar`          | Display strings, served to the client      |
| `category`       | `metric_category`  | `carbon` \| `vegetation` \| `biodiversity` |
| `aggregation`    | `aggregation_type` | `sum` \| `avg` \| `last`                   |
| `display_order`  | `integer`          | The client never hardcodes an order        |

`aggregation` is the interesting one. A **flow** (carbon sequestered this month)
must be _summed_ when months roll up into a year; a **stock** or index (canopy
cover, NDVI) must be _averaged_. Storing that alongside the definition stops the
API and the UI from disagreeing about it — the rollup SQL reads it directly.

Seeded metrics: `carbon_sequestered_tco2e`, `carbon_stock_tco2e`, `ndvi`,
`canopy_cover_pct`, `biodiversity_index`, `species_richness`.

### `site_metrics`

The time series. One row per `(site, metric, date)`.

| Column        | Type                                 | Notes        |
| ------------- | ------------------------------------ | ------------ |
| `id`          | `bigint` PK                          |              |
| `site_id`     | `uuid` FK → `sites`                  |              |
| `metric_id`   | `smallint` FK → `metric_definitions` |              |
| `recorded_at` | `date`                               | Bucket start |
| `value`       | `double precision`                   |              |

- `UNIQUE (site_id, metric_id, recorded_at)` makes ingestion idempotent: the
  seeder and any future import use `ON CONFLICT DO NOTHING` and can be re-run.
- `ix_site_metrics_lookup (site_id, metric_id, recorded_at)` matches the access
  pattern of every analytics query — filter by site and metric, then range-scan
  the dates in order. It also serves the `DISTINCT ON` that fetches each
  metric's latest sample.

#### Why a narrow table rather than wide columns

The obvious alternative is one column per metric on `sites`:

|                           | Narrow (chosen)                 | Wide                                          |
| ------------------------- | ------------------------------- | --------------------------------------------- |
| Add a metric              | One row in `metric_definitions` | Schema migration + backend + frontend release |
| Query one metric's series | Index range scan                | Column scan                                   |
| Multi-metric chart        | One query, one join             | One query, no join                            |
| Row count                 | 6 metrics × 36 months × N sites | N sites                                       |
| Sparse metrics            | Free                            | NULL columns                                  |

The cost is one join, which the composite index makes cheap. The benefit is that
"add soil organic carbon" is a data change, not a release.
See [ADR-0003](decisions/ADR-0003-narrow-metrics-table.md).

## Constraint naming

`app/db/base.py` sets an explicit naming convention, so Alembic autogenerates
stable, readable names (`fk_sites_project_id_projects`) rather than
database-assigned ones. Without it, downgrades break as soon as two environments
generate different names for the same constraint.

## Working with migrations

```bash
make migrate                          # apply everything
make migration m="add soil carbon"    # autogenerate from model changes
cd backend && alembic downgrade -1    # step back one
cd backend && alembic history         # see the chain
```

CI runs `upgrade head → downgrade base → upgrade head`, then autogenerates a
throwaway revision and fails if it is non-empty. That proves three things at
once: migrations apply, they are reversible, and the models match the schema.
