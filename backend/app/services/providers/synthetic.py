"""Deterministic synthetic analytics.

Why synthetic data (full reasoning in ``docs/decisions/ADR-0004``): the brief
explicitly permits mocks, and wiring a live Earth-observation pipeline would
make the demo depend on third-party quotas and multi-minute jobs. A reviewer
who draws a polygon anywhere on Earth must see a credible chart within a
second.

"Deterministic" is the important half. The generator is seeded from the site's
UUID, so the same site always yields the same series: screenshots stay stable,
tests can assert exact values, and two people demoing the app see identical
numbers. The output is not random noise either, it is driven by real physical
structure:

* Area scales carbon stock and flux, because tonnes scale with hectares.
* Latitude sets the seasonal phase and amplitude, so a Southern-Hemisphere site
  greens up in January while a tropical site barely cycles at all.
* Time carries a saturating growth trend, because a restoration site
  accumulates biomass quickly at first and then plateaus.
"""

from __future__ import annotations

import math
import random
from datetime import date
from typing import Final

from app.services.providers.base import AnalyticsProvider, MetricSample, SiteContext

# ---------------------------------------------------------------------------
# Metric keys. These must match the rows created by the metric catalogue
# migration; the seeder asserts that they do.
# ---------------------------------------------------------------------------
CARBON_SEQUESTERED: Final = "carbon_sequestered_tco2e"
CARBON_STOCK: Final = "carbon_stock_tco2e"
NDVI: Final = "ndvi"
CANOPY_COVER: Final = "canopy_cover_pct"
BIODIVERSITY_INDEX: Final = "biodiversity_index"
SPECIES_RICHNESS: Final = "species_richness"

#: Annual CO2e sequestration per hectare for a healthy restoration site.
#: Mid-range of the IPCC 2019 Refinement Vol.4 Ch.4 tier-1 defaults for
#: tropical and temperate reforestation (roughly 4-12 tCO2e/ha/yr).
BASE_SEQUESTRATION_T_PER_HA_YEAR: Final = 7.5
MONTHS_PER_YEAR: Final = 12
#: Beyond this latitude the seasonal swing is treated as maximal.
MAX_SEASONAL_LATITUDE: Final = 60.0
#: Years for the saturating growth curve to reach roughly 63% of its plateau.
GROWTH_TIME_CONSTANT_YEARS: Final = 6.0


def _seed_from_uuid(value: object) -> int:
    """Derive a stable 64-bit seed from a site id."""
    return int.from_bytes(str(value).encode("utf-8")[-8:], "big", signed=False)


def month_starts(start: date, end: date) -> list[date]:
    """Every month boundary in the inclusive range ``[start, end]``."""
    months: list[date] = []
    year, month = start.year, start.month
    while (year, month) <= (end.year, end.month):
        months.append(date(year, month, 1))
        year, month = (year + 1, 1) if month == MONTHS_PER_YEAR else (year, month + 1)
    return months


def seasonality(latitude: float, month: int) -> float:
    """Seasonal multiplier in roughly ``[-1, 1]`` for a latitude and month.

    Amplitude grows with distance from the equator and the phase flips across
    it, so the Southern Hemisphere peaks half a year away from the Northern.
    """
    amplitude = min(abs(latitude), MAX_SEASONAL_LATITUDE) / MAX_SEASONAL_LATITUDE
    phase = (month - 1) / MONTHS_PER_YEAR * 2 * math.pi
    hemisphere = 1.0 if latitude >= 0 else -1.0
    # Peak growing season: July in the north, January in the south.
    return amplitude * hemisphere * -math.cos(phase)


def saturating_growth(elapsed_years: float) -> float:
    """Growth factor in ``[0, 1)`` following a saturating exponential.

    Restoration biomass rises fast in the early years and then flattens, which
    a straight line would misrepresent.
    """
    return 1.0 - math.exp(-elapsed_years / GROWTH_TIME_CONSTANT_YEARS)


def clamp(value: float, *, lower: float, upper: float) -> float:
    """Constrain ``value`` to the inclusive range ``[lower, upper]``."""
    return max(lower, min(upper, value))


class SyntheticAnalyticsProvider(AnalyticsProvider):
    """Generates physically plausible, reproducible monthly metric series."""

    name = "synthetic-v1"

    def generate(self, context: SiteContext) -> list[MetricSample]:
        """Produce the full metric set for one site."""
        # Not cryptographic: the point is reproducibility, not unpredictability.
        rng = random.Random(_seed_from_uuid(context.site_id))  # noqa: S311
        latitude = float(context.geometry.representative_point().y)

        # Per-site constants, drawn once so every metric tells one coherent story.
        productivity = rng.uniform(0.7, 1.35)
        baseline_canopy = rng.uniform(12.0, 45.0)
        baseline_richness = rng.uniform(40.0, 120.0) * (1.0 - abs(latitude) / 120.0)
        stock_per_hectare = rng.uniform(35.0, 90.0)

        samples: list[MetricSample] = []
        cumulative_sequestration = 0.0

        for index, month_start in enumerate(month_starts(context.start_date, context.end_date)):
            elapsed_years = index / MONTHS_PER_YEAR
            season = seasonality(latitude, month_start.month)
            growth = saturating_growth(elapsed_years)
            # Plus or minus 6% observation noise, fixed for this site and month.
            noise = rng.uniform(-0.06, 0.06)

            monthly_flux = max(
                context.area_hectares
                * BASE_SEQUESTRATION_T_PER_HA_YEAR
                / MONTHS_PER_YEAR
                * productivity
                * (1.0 + 0.45 * season)
                * (0.55 + 0.45 * growth)
                * (1.0 + noise),
                0.0,
            )
            cumulative_sequestration += monthly_flux

            ndvi = clamp(
                0.34 + 0.30 * growth + 0.14 * season + 0.05 * (productivity - 1.0) + noise * 0.5,
                lower=0.05,
                upper=0.95,
            )
            canopy = clamp(
                baseline_canopy + 42.0 * growth + 4.0 * season + noise * 12.0,
                lower=0.0,
                upper=98.0,
            )
            biodiversity = clamp(
                38.0 + 34.0 * growth + 4.0 * season + noise * 20.0,
                lower=0.0,
                upper=100.0,
            )
            richness = max(baseline_richness * (0.75 + 0.5 * growth) * (1.0 + noise * 0.4), 1.0)
            carbon_stock = context.area_hectares * stock_per_hectare + cumulative_sequestration

            samples.extend(
                [
                    MetricSample(CARBON_SEQUESTERED, month_start, round(monthly_flux, 3)),
                    MetricSample(CARBON_STOCK, month_start, round(carbon_stock, 2)),
                    MetricSample(NDVI, month_start, round(ndvi, 4)),
                    MetricSample(CANOPY_COVER, month_start, round(canopy, 2)),
                    MetricSample(BIODIVERSITY_INDEX, month_start, round(biodiversity, 2)),
                    MetricSample(SPECIES_RICHNESS, month_start, round(richness, 1)),
                ]
            )

        return samples
