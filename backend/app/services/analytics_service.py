"""Analytics queries backing the charts and KPI cards."""

from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import UTC, date, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, ValidationError
from app.models.metric import MetricDefinition
from app.models.site import Site
from app.models.user import User
from app.repositories.metric_repo import MetricDefinitionRepository, SiteMetricRepository
from app.repositories.site_repo import SiteRepository
from app.schemas.analytics import (
    Interval,
    MetricDefinitionRead,
    MetricSeries,
    MetricSnapshot,
    SeriesPoint,
    SiteAnalytics,
    SiteAnalyticsSummary,
)

#: Default analytics window when the caller does not supply one.
DEFAULT_WINDOW_YEARS = 3
#: Guard against a request that would return an unusable number of points.
MAX_WINDOW_DAYS = 365 * 25


class AnalyticsService:
    """Turns stored samples into chart-ready series and KPI snapshots."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.sites = SiteRepository(session)
        self.definitions = MetricDefinitionRepository(session)
        self.samples = SiteMetricRepository(session)

    async def list_metrics(self) -> list[MetricDefinitionRead]:
        """The metric catalogue, so the frontend never hardcodes metric keys."""
        return [
            MetricDefinitionRead.model_validate(definition)
            for definition in await self.definitions.list_all()
        ]

    async def site_series(
        self,
        owner: User,
        site_id: uuid.UUID,
        *,
        metric_keys: list[str] | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        interval: Interval = Interval.MONTH,
    ) -> SiteAnalytics:
        """Return one bucketed series per requested metric."""
        await self._require_site(owner, site_id)
        start, end = self._resolve_window(date_from, date_to)
        definitions = await self._resolve_definitions(metric_keys)

        by_id = {definition.id: definition for definition in definitions}
        rows = await self.samples.series(site_id, list(by_id), start, end, interval)

        grouped: dict[int, list[SeriesPoint]] = defaultdict(list)
        for metric_id, bucket, value in rows:
            grouped[metric_id].append(SeriesPoint(t=bucket, v=round(float(value), 4)))

        return SiteAnalytics(
            site_id=site_id,
            interval=interval,
            date_from=start,
            date_to=end,
            series=[
                MetricSeries(
                    metric_key=definition.key,
                    label=definition.label,
                    unit=definition.unit,
                    category=definition.category,
                    aggregation=definition.aggregation,
                    points=grouped.get(definition.id, []),
                )
                for definition in definitions
            ],
        )

    async def site_summary(self, owner: User, site_id: uuid.UUID) -> SiteAnalyticsSummary:
        """Latest value plus period-over-period change for every metric."""
        site = await self._require_site(owner, site_id)
        catalogue = await self.definitions.list_all()
        definitions = {definition.id: definition for definition in catalogue}

        snapshots: list[MetricSnapshot] = []
        for metric_id, recorded_at, value in await self.samples.latest_per_metric(site_id):
            definition = definitions.get(metric_id)
            if definition is None:
                continue
            previous = await self.samples.value_before(site_id, metric_id, recorded_at)
            previous_value = previous[1] if previous else None
            snapshots.append(
                MetricSnapshot(
                    metric_key=definition.key,
                    label=definition.label,
                    unit=definition.unit,
                    category=definition.category,
                    latest_value=round(float(value), 4),
                    latest_date=recorded_at,
                    previous_value=previous_value,
                    change_pct=_percent_change(previous_value, float(value)),
                )
            )

        snapshots.sort(key=lambda snapshot: definitions_order(definitions, snapshot.metric_key))
        return SiteAnalyticsSummary(
            site_id=site.id,
            site_name=site.name,
            area_hectares=float(site.area_hectares),
            snapshots=snapshots,
        )

    # -- internals ------------------------------------------------------------

    async def _require_site(self, owner: User, site_id: uuid.UUID) -> Site:
        """Load a site the caller may see, or raise 404."""
        site = await self.sites.get_for_owner(site_id, owner.id)
        if site is None:
            raise NotFoundError("Site not found.", site_id=str(site_id))
        return site

    async def _resolve_definitions(self, keys: list[str] | None) -> list[MetricDefinition]:
        """Resolve requested metric keys, defaulting to the whole catalogue."""
        if not keys:
            return list(await self.definitions.list_all())

        definitions = await self.definitions.get_by_keys(keys)
        found = {definition.key for definition in definitions}
        if unknown := sorted(set(keys) - found):
            raise ValidationError(
                f"Unknown metric key(s): {', '.join(unknown)}.", unknown_metrics=unknown
            )
        return definitions

    @staticmethod
    def _resolve_window(date_from: date | None, date_to: date | None) -> tuple[date, date]:
        """Normalise and validate the requested date window."""
        end = date_to or datetime.now(UTC).date()
        start = date_from or date(end.year - DEFAULT_WINDOW_YEARS, end.month, 1)
        if start > end:
            raise ValidationError("date_from must not be after date_to.")
        if (end - start).days > MAX_WINDOW_DAYS:
            raise ValidationError("The requested date window is too large.")
        return start, end


def definitions_order(definitions: dict[int, MetricDefinition], metric_key: str) -> int:
    """Sort key placing snapshots in the catalogue's declared display order."""
    for definition in definitions.values():
        if definition.key == metric_key:
            return definition.display_order
    return 10_000


def _percent_change(previous: float | None, latest: float) -> float | None:
    """Percent change from ``previous`` to ``latest``.

    Returns ``None`` when there is no prior sample or the baseline is zero,
    rather than reporting a meaningless infinite growth rate.
    """
    if previous is None or previous == 0:
        return None
    return round((latest - previous) / abs(previous) * 100.0, 2)
