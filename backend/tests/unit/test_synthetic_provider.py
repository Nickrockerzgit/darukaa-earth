"""Tests for the deterministic synthetic analytics provider.

These assertions are what make the "deterministic, physically plausible"
claim in the README verifiable rather than decorative.
"""

from __future__ import annotations

import uuid
from datetime import date

import pytest
from shapely.geometry import Polygon

from app.services.providers.base import SiteContext
from app.services.providers.synthetic import (
    BIODIVERSITY_INDEX,
    CANOPY_COVER,
    CARBON_SEQUESTERED,
    NDVI,
    SyntheticAnalyticsProvider,
    month_starts,
    saturating_growth,
    seasonality,
)

PROVIDER = SyntheticAnalyticsProvider()
START = date(2023, 1, 1)
END = date(2025, 12, 1)


def _context(site_id: uuid.UUID, *, latitude: float = 12.0, area: float = 100.0) -> SiteContext:
    """Build a site context centred on ``latitude``."""
    polygon = Polygon(
        [
            (77.0, latitude),
            (77.01, latitude),
            (77.01, latitude + 0.01),
            (77.0, latitude + 0.01),
            (77.0, latitude),
        ]
    )
    return SiteContext(
        site_id=site_id,
        geometry=polygon,
        area_hectares=area,
        start_date=START,
        end_date=END,
    )


class TestHelpers:
    def test_month_starts_is_inclusive_at_both_ends(self):
        months = month_starts(date(2024, 1, 15), date(2024, 3, 2))
        assert months == [date(2024, 1, 1), date(2024, 2, 1), date(2024, 3, 1)]

    def test_month_starts_crosses_a_year_boundary(self):
        months = month_starts(date(2023, 11, 1), date(2024, 2, 1))
        assert len(months) == 4

    @pytest.mark.parametrize("month", range(1, 13))
    def test_seasonality_stays_within_bounds(self, month: int):
        assert -1.0 <= seasonality(55.0, month) <= 1.0

    def test_hemispheres_are_out_of_phase(self):
        # July is peak growing season in the north and mid-winter in the south.
        assert seasonality(55.0, 7) > 0
        assert seasonality(-55.0, 7) < 0

    def test_the_tropics_barely_cycle(self):
        assert abs(seasonality(2.0, 7)) < abs(seasonality(55.0, 7))

    def test_growth_saturates(self):
        assert saturating_growth(0.0) == 0.0
        assert 0.0 < saturating_growth(3.0) < saturating_growth(10.0) < 1.0


class TestDeterminism:
    def test_the_same_site_always_produces_the_same_series(self):
        site_id = uuid.UUID("11111111-1111-1111-1111-111111111111")
        first = PROVIDER.generate(_context(site_id))
        second = PROVIDER.generate(_context(site_id))
        assert [(s.metric_key, s.recorded_at, s.value) for s in first] == [
            (s.metric_key, s.recorded_at, s.value) for s in second
        ]

    def test_different_sites_produce_different_series(self):
        left = PROVIDER.generate(_context(uuid.UUID(int=1)))
        right = PROVIDER.generate(_context(uuid.UUID(int=2)))
        assert [s.value for s in left] != [s.value for s in right]


class TestPhysicalPlausibility:
    def test_every_metric_is_present_for_every_month(self):
        samples = PROVIDER.generate(_context(uuid.uuid4()))
        expected_months = len(month_starts(START, END))
        by_key: dict[str, int] = {}
        for sample in samples:
            by_key[sample.metric_key] = by_key.get(sample.metric_key, 0) + 1
        assert set(by_key.values()) == {expected_months}

    def test_ndvi_stays_inside_its_physical_range(self):
        samples = PROVIDER.generate(_context(uuid.uuid4(), latitude=55.0))
        values = [s.value for s in samples if s.metric_key == NDVI]
        assert all(0.0 <= value <= 1.0 for value in values)

    def test_percentage_metrics_stay_within_zero_to_one_hundred(self):
        samples = PROVIDER.generate(_context(uuid.uuid4()))
        for key in (CANOPY_COVER, BIODIVERSITY_INDEX):
            values = [s.value for s in samples if s.metric_key == key]
            assert all(0.0 <= value <= 100.0 for value in values)

    def test_sequestration_is_never_negative(self):
        samples = PROVIDER.generate(_context(uuid.uuid4(), latitude=60.0))
        values = [s.value for s in samples if s.metric_key == CARBON_SEQUESTERED]
        assert all(value >= 0.0 for value in values)

    def test_sequestration_scales_with_area(self):
        site_id = uuid.uuid4()
        small = PROVIDER.generate(_context(site_id, area=10.0))
        large = PROVIDER.generate(_context(site_id, area=1000.0))
        small_total = sum(s.value for s in small if s.metric_key == CARBON_SEQUESTERED)
        large_total = sum(s.value for s in large if s.metric_key == CARBON_SEQUESTERED)
        assert large_total == pytest.approx(small_total * 100, rel=0.01)

    def test_canopy_cover_trends_upward_over_time(self):
        samples = PROVIDER.generate(_context(uuid.UUID(int=7), latitude=5.0))
        values = [s.value for s in samples if s.metric_key == CANOPY_COVER]
        first_year = sum(values[:12]) / 12
        last_year = sum(values[-12:]) / 12
        assert last_year > first_year

    def test_a_single_month_window_yields_one_sample_per_metric(self):
        context = SiteContext(
            site_id=uuid.uuid4(),
            geometry=Polygon([(0, 0), (0.01, 0), (0.01, 0.01), (0, 0.01), (0, 0)]),
            area_hectares=50.0,
            start_date=date(2025, 5, 1),
            end_date=date(2025, 5, 28),
        )
        samples = PROVIDER.generate(context)
        assert len({s.metric_key for s in samples}) == len(samples)
