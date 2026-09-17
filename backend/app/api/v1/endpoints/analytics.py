"""Analytics endpoints powering the charts and KPI cards."""

from __future__ import annotations

import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Query

from app.api.deps import CurrentUser, DbSession
from app.schemas.analytics import (
    Interval,
    MetricDefinitionRead,
    SiteAnalytics,
    SiteAnalyticsSummary,
)
from app.services.analytics_service import AnalyticsService

router = APIRouter(tags=["analytics"])

MetricKeys = Annotated[
    list[str] | None,
    Query(
        alias="metrics",
        description="Metric keys to return; omit for the full catalogue",
    ),
]


@router.get(
    "/metrics",
    response_model=list[MetricDefinitionRead],
    summary="List the metric catalogue",
)
async def list_metrics(session: DbSession, user: CurrentUser) -> list[MetricDefinitionRead]:
    """Return every metric definition, so the client never hardcodes keys."""
    _ = user  # authentication is the only thing required here
    return await AnalyticsService(session).list_metrics()


@router.get(
    "/sites/{site_id}/analytics",
    response_model=SiteAnalytics,
    summary="Bucketed time series for a site",
)
async def site_analytics(
    site_id: uuid.UUID,
    user: CurrentUser,
    session: DbSession,
    metrics: MetricKeys = None,
    date_from: date | None = Query(default=None, description="Inclusive window start"),
    date_to: date | None = Query(default=None, description="Inclusive window end"),
    interval: Interval = Query(default=Interval.MONTH, description="Time bucket size"),
) -> SiteAnalytics:
    """Return one aggregated series per requested metric."""
    return await AnalyticsService(session).site_series(
        user,
        site_id,
        metric_keys=metrics,
        date_from=date_from,
        date_to=date_to,
        interval=interval,
    )


@router.get(
    "/sites/{site_id}/analytics/summary",
    response_model=SiteAnalyticsSummary,
    summary="Latest value and change per metric",
)
async def site_analytics_summary(
    site_id: uuid.UUID, user: CurrentUser, session: DbSession
) -> SiteAnalyticsSummary:
    """Return the KPI-card payload for a site."""
    return await AnalyticsService(session).site_summary(user, site_id)
