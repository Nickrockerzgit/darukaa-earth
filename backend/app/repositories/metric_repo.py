"""Data access for metric definitions and site time series."""

from __future__ import annotations

import uuid
from collections.abc import Iterable, Sequence
from datetime import date

from sqlalchemy import Date, Row, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.models.metric import AggregationType, MetricDefinition, SiteMetric
from app.models.site import Site
from app.repositories.base import BaseRepository, rows_affected
from app.schemas.analytics import Interval

#: Maps our public interval names onto the PostgreSQL ``date_trunc`` units.
_TRUNC_UNIT: dict[Interval, str] = {
    Interval.DAY: "day",
    Interval.MONTH: "month",
    Interval.QUARTER: "quarter",
    Interval.YEAR: "year",
}


class MetricDefinitionRepository(BaseRepository[MetricDefinition]):
    """Queries over the metric catalogue."""

    model = MetricDefinition

    async def list_all(self) -> Sequence[MetricDefinition]:
        """Every metric definition, in display order."""
        result = await self.session.execute(
            select(MetricDefinition).order_by(
                MetricDefinition.display_order, MetricDefinition.label
            )
        )
        return result.scalars().all()

    async def get_by_keys(self, keys: Iterable[str]) -> list[MetricDefinition]:
        """Resolve metric keys to definitions, preserving catalogue order."""
        wanted = list(keys)
        if not wanted:
            return []
        result = await self.session.execute(
            select(MetricDefinition)
            .where(MetricDefinition.key.in_(wanted))
            .order_by(MetricDefinition.display_order)
        )
        return list(result.scalars().all())


class SiteMetricRepository(BaseRepository[SiteMetric]):
    """Queries over the ``site_metrics`` time series."""

    model = SiteMetric

    async def series(
        self,
        site_id: uuid.UUID,
        metric_ids: Sequence[int],
        date_from: date,
        date_to: date,
        interval: Interval,
    ) -> list[Row[tuple[int, date, float]]]:
        """Roll the raw samples up into ``interval`` buckets.

        The aggregate function is chosen per metric from its declared
        ``aggregation``: flows (sequestered carbon) are summed, stocks (canopy
        cover) are averaged. A CASE expression keeps this to one query rather
        than one query per metric.
        """
        bucket = func.date_trunc(_TRUNC_UNIT[interval], SiteMetric.recorded_at).cast(Date)
        aggregated = func.coalesce(
            func.sum(SiteMetric.value).filter(MetricDefinition.aggregation == AggregationType.SUM),
            func.avg(SiteMetric.value),
        )

        statement = (
            select(SiteMetric.metric_id, bucket.label("bucket"), aggregated.label("value"))
            .join(MetricDefinition, MetricDefinition.id == SiteMetric.metric_id)
            .where(
                SiteMetric.site_id == site_id,
                SiteMetric.metric_id.in_(metric_ids),
                SiteMetric.recorded_at >= date_from,
                SiteMetric.recorded_at <= date_to,
            )
            .group_by(SiteMetric.metric_id, bucket)
            .order_by(SiteMetric.metric_id, bucket)
        )
        result = await self.session.execute(statement)
        return list(result.all())

    async def latest_per_metric(self, site_id: uuid.UUID) -> list[Row[tuple[int, date, float]]]:
        """Most recent sample of every metric for a site.

        ``DISTINCT ON`` is the Postgres-native way to do a top-1-per-group and
        is served straight from ``ix_site_metrics_lookup``.
        """
        statement = (
            select(SiteMetric.metric_id, SiteMetric.recorded_at, SiteMetric.value)
            .where(SiteMetric.site_id == site_id)
            .order_by(SiteMetric.metric_id, SiteMetric.recorded_at.desc())
            .distinct(SiteMetric.metric_id)
        )
        result = await self.session.execute(statement)
        return list(result.all())

    async def value_before(
        self, site_id: uuid.UUID, metric_id: int, before: date
    ) -> tuple[date, float] | None:
        """The sample immediately preceding ``before``, for change-over-time."""
        statement = (
            select(SiteMetric.recorded_at, SiteMetric.value)
            .where(
                SiteMetric.site_id == site_id,
                SiteMetric.metric_id == metric_id,
                SiteMetric.recorded_at < before,
            )
            .order_by(SiteMetric.recorded_at.desc())
            .limit(1)
        )
        row = (await self.session.execute(statement)).first()
        return (row[0], float(row[1])) if row else None

    async def project_latest_totals(self, project_id: uuid.UUID) -> list[Row[tuple[str, float]]]:
        """Latest value per metric per site, rolled up across a project.

        Implemented as a lateral-free two-step: a ``DISTINCT ON`` subquery
        picks each site's newest sample, then the outer query applies the
        metric's own aggregation across sites.
        """
        latest = (
            select(
                SiteMetric.site_id,
                SiteMetric.metric_id,
                SiteMetric.value,
            )
            .join(Site, Site.id == SiteMetric.site_id)
            .where(Site.project_id == project_id)
            .order_by(SiteMetric.site_id, SiteMetric.metric_id, SiteMetric.recorded_at.desc())
            .distinct(SiteMetric.site_id, SiteMetric.metric_id)
            .subquery()
        )

        rolled = func.coalesce(
            func.sum(latest.c.value).filter(MetricDefinition.aggregation == AggregationType.SUM),
            func.avg(latest.c.value),
        )
        statement = (
            select(MetricDefinition.key, rolled)
            # select_from is required: without it SQLAlchemy infers the FROM
            # from the selected columns (metric_definitions) and then tries to
            # join that table to itself. The subquery is the left side.
            .select_from(latest)
            .join(MetricDefinition, MetricDefinition.id == latest.c.metric_id)
            .group_by(MetricDefinition.key)
        )
        result = await self.session.execute(statement)
        return list(result.all())

    async def bulk_upsert(self, rows: Sequence[dict[str, object]]) -> int:
        """Insert many samples, ignoring ones that already exist.

        Used by the seeder and by any future ingestion job: re-running it is
        therefore idempotent instead of raising on the unique constraint.
        """
        if not rows:
            return 0
        statement = (
            pg_insert(SiteMetric)
            .values(list(rows))
            .on_conflict_do_nothing(constraint="uq_site_metric_sample")
        )
        result = await self.session.execute(statement)
        await self.session.flush()
        return rows_affected(result)
