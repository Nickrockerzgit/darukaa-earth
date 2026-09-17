"""Populate the metric catalogue.

Revision ID: 0003
Revises: 0002
Create Date: 2026-09-18

The catalogue is reference data, not demo data: the API contract and the
frontend's chart config both depend on these keys existing, so they ship as a
migration rather than as part of the optional seed script.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

METRICS: tuple[dict[str, object], ...] = (
    {
        "key": "carbon_sequestered_tco2e",
        "label": "Carbon Sequestered",
        "unit": "tCO2e",
        "description": "Net CO2 equivalent removed from the atmosphere during the period.",
        "category": "carbon",
        "aggregation": "sum",
        "display_order": 10,
    },
    {
        "key": "carbon_stock_tco2e",
        "label": "Carbon Stock",
        "unit": "tCO2e",
        "description": "Total CO2 equivalent stored in biomass and soil at the period end.",
        "category": "carbon",
        "aggregation": "last",
        "display_order": 20,
    },
    {
        "key": "ndvi",
        "label": "NDVI",
        "unit": "index",
        "description": "Normalised Difference Vegetation Index, 0 (bare) to 1 (dense canopy).",
        "category": "vegetation",
        "aggregation": "avg",
        "display_order": 30,
    },
    {
        "key": "canopy_cover_pct",
        "label": "Canopy Cover",
        "unit": "%",
        "description": "Share of the site's surface shaded by tree canopy.",
        "category": "vegetation",
        "aggregation": "avg",
        "display_order": 40,
    },
    {
        "key": "biodiversity_index",
        "label": "Biodiversity Index",
        "unit": "score",
        "description": "Composite habitat quality score from 0 to 100.",
        "category": "biodiversity",
        "aggregation": "avg",
        "display_order": 50,
    },
    {
        "key": "species_richness",
        "label": "Species Richness",
        "unit": "species",
        "description": "Count of distinct species observed across monitoring surveys.",
        "category": "biodiversity",
        "aggregation": "avg",
        "display_order": 60,
    },
)


def upgrade() -> None:
    """Insert the metric definitions."""
    metric_definitions = sa.table(
        "metric_definitions",
        sa.column("key", sa.String),
        sa.column("label", sa.String),
        sa.column("unit", sa.String),
        sa.column("description", sa.Text),
        sa.column("category", sa.Enum(name="metric_category")),
        sa.column("aggregation", sa.Enum(name="aggregation_type")),
        sa.column("display_order", sa.Integer),
    )
    op.bulk_insert(metric_definitions, list(METRICS))


def downgrade() -> None:
    """Remove the metric definitions; samples cascade."""
    keys = ", ".join(f"'{metric['key']}'" for metric in METRICS)
    op.execute(f"DELETE FROM metric_definitions WHERE key IN ({keys})")  # noqa: S608
