# Architecture Decision Records

Short notes on the choices that were not obvious, written at the time they were
made. Each one states the problem, what was chosen, what was rejected, and what
it costs — so a reviewer can disagree with the reasoning rather than guess at it.

| #                                          | Decision                                   |
| ------------------------------------------ | ------------------------------------------ |
| [0001](ADR-0001-fastapi.md)                | FastAPI over Django REST and Flask         |
| [0002](ADR-0002-postgis-geometry.md)       | Geometry storage and area computation      |
| [0003](ADR-0003-narrow-metrics-table.md)   | Narrow time-series table over wide columns |
| [0004](ADR-0004-synthetic-analytics.md)    | Deterministic synthetic analytics data     |
| [0005](ADR-0005-hand-written-api-types.md) | Hand-written TypeScript API types          |
| [0006](ADR-0006-token-storage.md)          | JWT storage in localStorage                |
| [0007](ADR-0007-mapbox-layers.md)          | Mapbox layers over React map components    |
