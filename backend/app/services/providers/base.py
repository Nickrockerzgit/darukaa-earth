"""The analytics provider seam.

Every number the dashboard draws arrives through this interface. Today the only
implementation is a deterministic synthetic generator (see
``app.services.providers.synthetic``); swapping in a real remote-sensing
pipeline (Sentinel-2 / Google Earth Engine) later means adding one class here
and changing one line of wiring, not touching the API, the repositories, or the
frontend.
"""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date

from shapely.geometry.base import BaseGeometry


@dataclass(frozen=True, slots=True)
class MetricSample:
    """One generated observation, ready to be persisted."""

    metric_key: str
    recorded_at: date
    value: float


@dataclass(frozen=True, slots=True)
class SiteContext:
    """Everything a provider needs to know about the site it is describing."""

    site_id: uuid.UUID
    geometry: BaseGeometry
    area_hectares: float
    start_date: date
    end_date: date


class AnalyticsProvider(ABC):
    """Produces the metric time series backing a site's analytics view."""

    #: Stable identifier, referenced by the README and ADR-0004.
    name: str = "abstract"

    @abstractmethod
    def generate(self, context: SiteContext) -> list[MetricSample]:
        """Return every metric sample for the site over its date window."""
        raise NotImplementedError
