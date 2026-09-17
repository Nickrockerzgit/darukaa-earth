# ADR-0003: Narrow time-series table over wide columns

**Status:** Accepted · **Date:** 2026-09-18

## Context

Each site has several metrics measured monthly: carbon sequestered, carbon
stock, NDVI, canopy cover, a biodiversity index, species richness. The set will
grow — soil organic carbon, water stress and canopy height are all plausible
next additions.

## Decision

Two tables:

- `metric_definitions` — the catalogue: key, label, unit, category, and how the
  metric aggregates.
- `site_metrics` — `(site_id, metric_id, recorded_at, value)`, one row per
  observation, with a unique constraint on the triple.

## Why

**Adding a metric is a data change.** A new metric is one row in
`metric_definitions`. With a column per metric it is a schema migration, a
backend release and a frontend release, coordinated.

**The client stops hardcoding metric keys.** `GET /metrics` serves the
catalogue, so labels, units, ordering and colour category all come from the
database. A typo in a unit is fixed with an UPDATE.

**Aggregation semantics live with the metric.** `aggregation` is `sum` for a
flow (carbon sequestered during a period) and `avg` for a stock or index (canopy
cover, NDVI). The rollup SQL reads it directly:

```sql
COALESCE(
  SUM(value) FILTER (WHERE md.aggregation = 'sum'),
  AVG(value)
)
```

Without that column, "how do monthly values become a yearly value?" is answered
separately in the API and in the UI, and they eventually disagree. The test
`test_flows_sum_while_stocks_average` pins the behaviour.

**Sparse data is free.** A metric collected only at some sites simply has fewer
rows, rather than a column full of NULLs.

## Rejected

**Wide columns on `sites`.** Simplest to query and smallest on disk, but every
new metric becomes a coordinated release, and the table accumulates NULLs.

**A JSONB blob per site.** Flexible, but it cannot be indexed usefully for range
queries over time, aggregation needs JSON functions, and nothing constrains the
shape — a typo in a key is silently a new metric.

**A dedicated time-series database.** Correct at real scale; disproportionate
here, and it would put the metrics outside the transaction that creates a site.

## Cost

- One join on every analytics query. `ix_site_metrics_lookup` makes it an index
  scan, so this is small.
- Row count grows as metrics × months × sites. Six metrics × 36 months × 100
  sites is ~22k rows — nothing. At a million sites this table would need
  partitioning by `recorded_at`.
- A metric key is a string, so a typo in an ingestion job creates a dangling
  reference. The foreign key to `metric_definitions` prevents that.
