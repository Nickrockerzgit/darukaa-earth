"""Analytics request/response schemas."""

from __future__ import annotations

import uuid
from datetime import date
from enum import StrEnum

from pydantic import BaseModel, Field

from app.models.metric import AggregationType, MetricCategory
from app.schemas.common import ORMModel


class Interval(StrEnum):
    """Time bucket used when rolling up a series."""

    DAY = "day"
    MONTH = "month"
    QUARTER = "quarter"
    YEAR = "year"


class MetricDefinitionRead(ORMModel):
    """Catalogue entry describing a measurable quantity."""

    id: int
    key: str
    label: str
    unit: str
    description: str | None
    category: MetricCategory
    aggregation: AggregationType
    display_order: int


class SeriesPoint(BaseModel):
    """One (timestamp, value) pair of a time series."""

    t: date = Field(description="Bucket start date")
    v: float = Field(description="Aggregated value for the bucket")


class MetricSeries(BaseModel):
    """A full time series for one metric on one site."""

    metric_key: str
    label: str
    unit: str
    category: MetricCategory
    aggregation: AggregationType
    points: list[SeriesPoint]


class SiteAnalytics(BaseModel):
    """Time-series payload for a site, one entry per requested metric."""

    site_id: uuid.UUID
    interval: Interval
    date_from: date
    date_to: date
    series: list[MetricSeries]


class MetricSnapshot(BaseModel):
    """Latest value of a metric plus its change over the comparison window."""

    metric_key: str
    label: str
    unit: str
    category: MetricCategory
    latest_value: float
    latest_date: date
    previous_value: float | None = None
    change_pct: float | None = Field(
        default=None, description="Percent change against the previous period"
    )


class SiteAnalyticsSummary(BaseModel):
    """KPI-card payload for a site."""

    site_id: uuid.UUID
    site_name: str
    area_hectares: float
    snapshots: list[MetricSnapshot]
