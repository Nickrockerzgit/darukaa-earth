"""Metric definitions and the site-level time series that reference them.

Design note (see docs/decisions/ADR-0003): metrics live in a narrow
``(site_id, metric_id, recorded_at, value)`` table rather than one wide column
per metric. Adding "soil organic carbon" tomorrow is then a single row in
``metric_definitions`` instead of a schema migration plus a frontend release.
The cost is one join, which the composite index makes cheap.
"""

from __future__ import annotations

import uuid
from datetime import date
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    Date,
    Float,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, pg_enum

if TYPE_CHECKING:
    from app.models.site import Site


class MetricCategory(StrEnum):
    """Which pillar of the platform a metric belongs to."""

    CARBON = "carbon"
    BIODIVERSITY = "biodiversity"
    VEGETATION = "vegetation"


class AggregationType(StrEnum):
    """How a metric rolls up across time or across sites.

    A stock measure such as canopy cover must be averaged; a flow measure such
    as sequestered carbon must be summed. Storing this alongside the definition
    stops the API and the UI from disagreeing about it.
    """

    SUM = "sum"
    AVG = "avg"
    LAST = "last"


class MetricDefinition(TimestampMixin, Base):
    """Catalogue entry describing one measurable quantity."""

    __tablename__ = "metric_definitions"

    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    label: Mapped[str] = mapped_column(String(120), nullable=False)
    unit: Mapped[str] = mapped_column(String(32), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    category: Mapped[MetricCategory] = mapped_column(
        pg_enum(MetricCategory, "metric_category"), nullable=False
    )
    aggregation: Mapped[AggregationType] = mapped_column(
        pg_enum(AggregationType, "aggregation_type"),
        default=AggregationType.AVG,
        server_default=AggregationType.AVG.value,
        nullable=False,
    )
    #: Ordering hint so the UI lists metrics consistently without hardcoding.
    display_order: Mapped[int] = mapped_column(
        Integer, default=100, server_default="100", nullable=False
    )

    samples: Mapped[list[SiteMetric]] = relationship(back_populates="definition", lazy="noload")


class SiteMetric(Base):
    """One observation of one metric for one site on one date."""

    __tablename__ = "site_metrics"
    __table_args__ = (
        UniqueConstraint("site_id", "metric_id", "recorded_at", name="uq_site_metric_sample"),
        Index("ix_site_metrics_lookup", "site_id", "metric_id", "recorded_at"),
    )

    # BigInteger: this table grows as metrics x months x sites, so a 32-bit
    # key is the wrong ceiling. It also has to match migration 0002.
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    site_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("sites.id", ondelete="CASCADE"),
        nullable=False,
    )
    metric_id: Mapped[int] = mapped_column(
        SmallInteger,
        ForeignKey("metric_definitions.id", ondelete="CASCADE"),
        nullable=False,
    )
    recorded_at: Mapped[date] = mapped_column(Date, nullable=False)
    value: Mapped[float] = mapped_column(Float, nullable=False)

    site: Mapped[Site] = relationship(back_populates="metrics", lazy="noload")
    definition: Mapped[MetricDefinition] = relationship(back_populates="samples", lazy="joined")
