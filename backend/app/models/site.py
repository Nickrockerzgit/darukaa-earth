"""Site model - a geographic polygon belonging to a project."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from geoalchemy2 import Geometry
from sqlalchemy import ForeignKey, Index, Numeric, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.metric import SiteMetric
    from app.models.project import Project

#: WGS84. Everything crossing the API boundary is lon/lat degrees, matching
#: what Mapbox GL and the GeoJSON spec expect. Area is computed by casting to
#: ``geography`` at write time so we never store a planar-metre lie.
SRID = 4326


class Site(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A monitored land parcel, stored as a MultiPolygon in WGS84."""

    __tablename__ = "sites"
    __table_args__ = (
        Index("ix_sites_geometry", "geometry", postgresql_using="gist"),
        Index("ix_sites_project_created", "project_id", "created_at"),
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)

    # MultiPolygon (not Polygon) so a site can legitimately consist of several
    # disjoint parcels without needing a second table.
    geometry: Mapped[Any] = mapped_column(
        Geometry(geometry_type="MULTIPOLYGON", srid=SRID, spatial_index=False),
        nullable=False,
    )
    #: Denormalised from ``geometry`` on write. Recomputing ST_Area on every
    #: list request would dominate the query cost for a value that never
    #: changes unless the polygon does.
    area_hectares: Mapped[float] = mapped_column(Numeric(14, 4, asdecimal=False), nullable=False)
    #: ST_PointOnSurface, guaranteed to fall inside the polygon (unlike a
    #: centroid on a concave shape). Used for map fly-to and label placement.
    centroid: Mapped[Any] = mapped_column(
        Geometry(geometry_type="POINT", srid=SRID, spatial_index=False),
        nullable=False,
    )

    project: Mapped[Project] = relationship(back_populates="sites", lazy="joined")
    metrics: Mapped[list[SiteMetric]] = relationship(
        back_populates="site",
        cascade="all, delete-orphan",
        lazy="noload",
    )
