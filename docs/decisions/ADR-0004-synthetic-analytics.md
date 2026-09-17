# ADR-0004: Deterministic synthetic analytics data

**Status:** Accepted · **Date:** 2026-09-18

## Context

The dashboard's purpose is showing how a site performs over time. That needs
metric data. The brief states: _"There are no limitations on datasets and mocks
you would want to use in the project, feel free to use any datasets and document
why this choice was made."_

The real options were a live Earth-observation pipeline (Google Earth Engine or
Sentinel Hub), a static real-world dataset, or generated data.

## Decision

A deterministic synthetic generator, behind an `AnalyticsProvider` interface.

## Why

**A reviewer will draw a polygon somewhere we have no data for.** That is the
core interaction. With a fixed real-world dataset, a polygon drawn over
Rajasthan or Ohio produces an empty chart, and the feature looks broken. The
generator produces a credible series for any polygon on Earth, immediately.

**A live pipeline would make the demo fragile.** Earth Engine requires service
account credentials, imposes quotas, and returns results in tens of seconds to
minutes. A reviewer clicking a site would wait, or hit a quota wall, and the
demo would depend on a third party being up.

**Deterministic, not random.** The generator is seeded from the site's UUID, so:

- the same site always produces the same series — screenshots stay valid,
- tests can assert exact values (`test_the_same_site_always_produces_the_same_series`),
- two people demoing the app see identical numbers.

Reseeding on every request would make the charts jitter and the tests useless.

**The output is driven by real structure, not noise.** From
`services/providers/synthetic.py`:

| Driver             | Effect                                                                                                                  |
| ------------------ | ----------------------------------------------------------------------------------------------------------------------- |
| Area               | Carbon flux and stock scale with hectares, so a 10× larger site sequesters ~10× more                                    |
| Latitude           | Sets seasonal amplitude and phase: a Southern-Hemisphere site peaks in January, a tropical site barely cycles           |
| Time               | A saturating exponential — restoration biomass rises fast early then plateaus, which a straight line would misrepresent |
| Per-site constants | Productivity, baseline canopy and species richness are drawn once per site, so all six metrics tell one coherent story  |

The baseline of 7.5 tCO2e/ha/yr is the mid-range of the IPCC 2019 Refinement
Vol. 4 Ch. 4 tier-1 defaults for tropical and temperate reforestation
(roughly 4–12). NDVI is clamped to [0, 1] and percentages to [0, 100], because a
plausible-looking impossible value is worse than an obviously fake one. Unit
tests assert each of these properties.

## The seam that makes this replaceable

```python
class AnalyticsProvider(ABC):
    @abstractmethod
    def generate(self, context: SiteContext) -> list[MetricSample]: ...
```

`SiteService` takes a provider by constructor injection. A real implementation
would be a second class plus one wiring change — the API, repositories, schemas
and the entire frontend are unaffected, because they already consume
`site_metrics` rows rather than the generator.

## Rejected

**Google Earth Engine / Sentinel Hub.** The right long-term answer. Rejected for
the demo on credentials, quotas and latency.

**A static real-world dataset** (e.g. Global Forest Watch tree-cover loss).
Genuinely real, but only covers where it covers, so a drawn polygon usually
yields nothing.

**`random.random()` per request.** Fastest to write, but charts would change on
every refresh and no test could assert on them.

## Cost

- **The numbers are not real.** This is stated in the README and on this page;
  it must never be presented as measurement.
- The generator encodes one coarse growth model, so every site's shape is
  qualitatively similar.
- `carbon_stock` is a simple accumulation and does not model disturbance,
  harvest or fire.
