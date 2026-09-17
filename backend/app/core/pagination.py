"""Offset pagination primitives shared by every list endpoint."""

from __future__ import annotations

from dataclasses import dataclass
from math import ceil

from fastapi import Query

DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100


@dataclass(frozen=True, slots=True)
class PaginationParams:
    """Validated page/size pair plus the derived SQL offset."""

    page: int
    size: int

    @property
    def offset(self) -> int:
        """Number of rows to skip."""
        return (self.page - 1) * self.size

    @property
    def limit(self) -> int:
        """Number of rows to fetch."""
        return self.size

    @staticmethod
    def total_pages(total: int, size: int) -> int:
        """Total page count for ``total`` rows at ``size`` rows per page."""
        return ceil(total / size) if size else 0


def pagination_params(
    page: int = Query(default=1, ge=1, description="1-indexed page number"),
    size: int = Query(
        default=DEFAULT_PAGE_SIZE,
        ge=1,
        le=MAX_PAGE_SIZE,
        description="Rows per page",
    ),
) -> PaginationParams:
    """FastAPI dependency that yields validated pagination parameters."""
    return PaginationParams(page=page, size=size)
