"""SQLAlchemy declarative base.

The explicit naming convention means Alembic autogenerates stable, readable
constraint names instead of database-assigned ones, so migrations stay
reviewable and downgrades actually work.
"""

from __future__ import annotations

from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_N_label)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_N_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Declarative base shared by every ORM model."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)

    def __repr__(self) -> str:
        """Readable repr showing the primary key, useful in test failures."""
        pk = getattr(self, "id", None)
        return f"<{type(self).__name__} id={pk}>"
