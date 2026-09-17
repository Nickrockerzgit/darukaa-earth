"""Generic async repository.

The repository layer owns every SQL statement. Services stay free of
SQLAlchemy imports, which makes them trivial to unit test and keeps query
tuning in one place.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, cast

from sqlalchemy import CursorResult, Result, Select, delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import Base


def rows_affected(result: Result[Any]) -> int:
    """Rows a DML statement touched.

    ``AsyncSession.execute`` is typed as returning ``Result``, which has no
    ``rowcount``; every DML statement in fact returns a ``CursorResult``.
    """
    return int(cast("CursorResult[Any]", result).rowcount or 0)


class BaseRepository[ModelT: Base]:
    """CRUD operations shared by every concrete repository."""

    model: type[ModelT]

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, entity_id: Any) -> ModelT | None:
        """Fetch one row by primary key, or ``None``."""
        return await self.session.get(self.model, entity_id)

    async def list(self, statement: Select[tuple[ModelT]]) -> Sequence[ModelT]:
        """Execute a prepared SELECT and return the unique scalar rows.

        ``unique()`` is required because joined eager loads can otherwise
        return the same parent once per joined child row.
        """
        result = await self.session.execute(statement)
        return result.scalars().unique().all()

    async def count(self, statement: Select[Any]) -> int:
        """Count rows matching ``statement`` without fetching them.

        Wrapping the original SELECT in a subquery preserves every filter and
        join while discarding ORDER BY / LIMIT, so the count always matches
        what the unpaginated query would return.
        """
        subquery = statement.order_by(None).options().subquery()
        total = await self.session.scalar(select(func.count()).select_from(subquery))
        return int(total or 0)

    async def add(self, entity: ModelT) -> ModelT:
        """Stage a new row and flush so server defaults are populated."""
        self.session.add(entity)
        await self.session.flush()
        await self.session.refresh(entity)
        return entity

    async def delete(self, entity: ModelT) -> None:
        """Delete a loaded row."""
        await self.session.delete(entity)
        await self.session.flush()

    async def delete_by_id(self, entity_id: Any) -> int:
        """Delete by primary key without loading the row. Returns rows removed."""
        result = await self.session.execute(
            delete(self.model).where(self.model.id == entity_id)  # type: ignore[attr-defined]
        )
        await self.session.flush()
        return rows_affected(result)

    @staticmethod
    def apply_updates(entity: ModelT, changes: dict[str, Any]) -> ModelT:
        """Apply a partial-update mapping, ignoring keys the model does not own."""
        for field, value in changes.items():
            if hasattr(entity, field):
                setattr(entity, field, value)
        return entity


def select_base[ModelT: Base](model: type[ModelT]) -> Select[tuple[ModelT]]:
    """Start a SELECT for ``model`` (thin alias that keeps call sites terse)."""
    return select(model)
