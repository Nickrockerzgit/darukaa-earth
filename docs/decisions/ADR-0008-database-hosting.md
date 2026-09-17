# ADR-0008: Host Postgres on Neon, not on Render

**Status:** Accepted · **Date:** 2026-09-18

## Context

The application needs a managed PostgreSQL with PostGIS. The API runs on Render
and the SPA on Vercel, so the obvious move is Render's own managed Postgres,
provisioned in the same blueprint.

It also needs to stay up for an unknown length of time: this is a hackathon
submission, and reviewers may open the live demo weeks after it is handed in.

## Decision

**Neon** for the database. Render keeps the API; Vercel keeps the web app.

## Why not Render Postgres

Technically it is fine — Render's Postgres supports `postgis`, `pg_trgm` and
`pgcrypto` on PostgreSQL 13+, which is everything migration `0001` needs.

The problem is the free plan's lifetime. A free Render Postgres **expires 30
days after creation**, then gets a 14-day grace period, and is then **deleted
along with all of its data**. Only one free database is allowed per workspace,
with 1 GB of storage and no backups.

For a normal side project that is an acceptable trade. For a submission whose
whole point is a working demo URL, it is disqualifying: the most likely outcome
is a reviewer opening the link in week five and finding a dead API. A demo that
dies on a timer is worse than no demo, because it looks like the app is broken
rather than the free tier having lapsed.

## Why Neon

- **The free tier does not expire.** It is a standing plan, not a trial.
- **PostGIS is supported** on any Neon project: `CREATE EXTENSION postgis;`
  works, so migration `0001` runs unchanged.
- **Scale-to-zero suits the traffic.** The demo is idle almost all the time.
  Neon suspends the compute and resumes it on the next connection, which pairs
  naturally with Render's free tier already sleeping the API.
- **Branching** gives a throwaway database per pull request later, without
  another provider.

The cost is a third dashboard to configure and 0.5 GB of storage. The seeded
demo is a few thousand rows, so storage is not close to binding.

## Rejected

**Supabase.** Also free, and ships PostGIS enabled by default. Rejected because
a free Supabase project **pauses after a week of inactivity** and needs a manual
resume from the dashboard — the same "reviewer finds it dead" failure, just on a
shorter clock and with a human in the loop. Neon resumes on connection.

**Railway / Aiven.** Trial credit or a time-limited free plan, so the same
expiry problem in a different shape.

**Keeping Render Postgres and upgrading to a paid plan.** The correct answer for
a real product and the right move if this ships; unnecessary for a submission
when a non-expiring free tier exists.

## What this costs in code

Neon hands out a libpq-style URL, which asyncpg cannot consume as-is. Three
things had to be handled in `app/db/session.py`, all covered by
`tests/unit/test_connection_settings.py`:

1. **`sslmode` and `channel_binding` are stripped.** They are libpq parameters;
   asyncpg raises `TypeError: connect() got an unexpected keyword argument
'sslmode'`. TLS is requested through `connect_args={"ssl": True}` instead.
2. **The prepared-statement cache is disabled on a pooled endpoint.** Neon's
   `-pooler` host is PgBouncer in transaction mode, which does not keep a client
   on one backend between statements, so asyncpg's cached statements start
   referring to statements the new backend has never prepared. The failure is
   intermittent, which makes it genuinely hard to diagnose.
3. **`NullPool` on a pooled endpoint.** Pooling in front of PgBouncer is a
   second, redundant pool.

Detection is by URL, so the same code path serves the local Docker Postgres with
no special-casing and no environment flag to forget.

## Migrations

Alembic connects through the **direct** (non-pooled) endpoint: DDL and advisory
locks want a stable backend. The running API uses the **pooled** endpoint. Both
come from the same Neon project; only the hostname differs.
