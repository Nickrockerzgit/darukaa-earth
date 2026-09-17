"""Create users, projects, sites, metrics and refresh tokens.

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-18
"""

from __future__ import annotations

from collections.abc import Sequence

import geoalchemy2
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SRID = 4326

# `create_type=False` is load-bearing. Without it SQLAlchemy emits CREATE TYPE
# again as part of the first CREATE TABLE that references the enum, and the
# migration dies with `type "user_role" already exists`. The types are created
# once, explicitly, at the top of upgrade().
user_role = postgresql.ENUM("admin", "viewer", name="user_role", create_type=False)
project_type = postgresql.ENUM(
    "carbon", "biodiversity", "mixed", name="project_type", create_type=False
)
project_status = postgresql.ENUM(
    "draft", "active", "archived", name="project_status", create_type=False
)
metric_category = postgresql.ENUM(
    "carbon", "biodiversity", "vegetation", name="metric_category", create_type=False
)
aggregation_type = postgresql.ENUM(
    "sum", "avg", "last", name="aggregation_type", create_type=False
)

ENUMS = (user_role, project_type, project_status, metric_category, aggregation_type)


def upgrade() -> None:
    """Create every table, enum, constraint and index."""
    bind = op.get_bind()
    for enum in ENUMS:
        enum.create(bind, checkfirst=True)

    op.create_table(
        "users",
        sa.Column("id", sa.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()")),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("hashed_password", sa.String(128), nullable=False),
        sa.Column("full_name", sa.String(160)),
        sa.Column("role", user_role, nullable=False, server_default="admin"),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "refresh_tokens",
        sa.Column("id", sa.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id", name="pk_refresh_tokens"),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="fk_refresh_tokens_user_id_users",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint("token_hash", name="uq_refresh_tokens_token_hash"),
    )
    op.create_index("ix_refresh_tokens_user_active", "refresh_tokens", ["user_id", "revoked_at"])

    op.create_table(
        "projects",
        sa.Column("id", sa.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()")),
        sa.Column("owner_id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("project_type", project_type, nullable=False, server_default="carbon"),
        sa.Column("status", project_status, nullable=False, server_default="draft"),
        sa.Column("start_date", sa.Date),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id", name="pk_projects"),
        sa.ForeignKeyConstraint(
            ["owner_id"], ["users.id"], name="fk_projects_owner_id_users", ondelete="CASCADE"
        ),
    )
    op.create_index("ix_projects_owner_status", "projects", ["owner_id", "status"])
    op.create_index(
        "ix_projects_name_trgm",
        "projects",
        ["name"],
        postgresql_using="gin",
        postgresql_ops={"name": "gin_trgm_ops"},
    )

    op.create_table(
        "sites",
        sa.Column("id", sa.UUID(as_uuid=True), server_default=sa.text("gen_random_uuid()")),
        sa.Column("project_id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column(
            "geometry",
            geoalchemy2.Geometry(geometry_type="MULTIPOLYGON", srid=SRID, spatial_index=False),
            nullable=False,
        ),
        sa.Column("area_hectares", sa.Numeric(14, 4), nullable=False),
        sa.Column(
            "centroid",
            geoalchemy2.Geometry(geometry_type="POINT", srid=SRID, spatial_index=False),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id", name="pk_sites"),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["projects.id"],
            name="fk_sites_project_id_projects",
            ondelete="CASCADE",
        ),
        sa.CheckConstraint("area_hectares >= 0", name="ck_sites_area_non_negative"),
    )
    # GIST is what makes ST_Intersects / bbox queries index-assisted rather
    # than a sequential scan over every polygon.
    op.create_index("ix_sites_geometry", "sites", ["geometry"], postgresql_using="gist")
    op.create_index("ix_sites_project_created", "sites", ["project_id", "created_at"])

    op.create_table(
        "metric_definitions",
        sa.Column("id", sa.SmallInteger, autoincrement=True),
        sa.Column("key", sa.String(64), nullable=False),
        sa.Column("label", sa.String(120), nullable=False),
        sa.Column("unit", sa.String(32), nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("category", metric_category, nullable=False),
        sa.Column("aggregation", aggregation_type, nullable=False, server_default="avg"),
        sa.Column("display_order", sa.Integer, nullable=False, server_default="100"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id", name="pk_metric_definitions"),
        sa.UniqueConstraint("key", name="uq_metric_definitions_key"),
    )

    op.create_table(
        "site_metrics",
        sa.Column("id", sa.BigInteger, autoincrement=True),
        sa.Column("site_id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("metric_id", sa.SmallInteger, nullable=False),
        sa.Column("recorded_at", sa.Date, nullable=False),
        sa.Column("value", sa.Float, nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_site_metrics"),
        sa.ForeignKeyConstraint(
            ["site_id"], ["sites.id"], name="fk_site_metrics_site_id_sites", ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["metric_id"],
            ["metric_definitions.id"],
            name="fk_site_metrics_metric_id_metric_definitions",
            ondelete="CASCADE",
        ),
        sa.UniqueConstraint("site_id", "metric_id", "recorded_at", name="uq_site_metric_sample"),
    )
    # Matches the access pattern of every analytics query: filter by site and
    # metric, then range-scan the dates in order.
    op.create_index(
        "ix_site_metrics_lookup", "site_metrics", ["site_id", "metric_id", "recorded_at"]
    )


def downgrade() -> None:
    """Drop everything this migration created, children first."""
    op.drop_table("site_metrics")
    op.drop_table("metric_definitions")
    op.drop_table("sites")
    op.drop_table("projects")
    op.drop_table("refresh_tokens")
    op.drop_table("users")
    bind = op.get_bind()
    for enum in reversed(ENUMS):
        enum.drop(bind, checkfirst=True)
