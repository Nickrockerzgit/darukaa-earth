"""Shared response envelopes."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ORMModel(BaseModel):
    """Base for schemas that are serialised straight from ORM instances."""

    model_config = ConfigDict(from_attributes=True)


class Page[T](BaseModel):
    """A single page of results plus the metadata a client needs to paginate."""

    items: list[T]
    total: int = Field(description="Total rows matching the filter, ignoring pagination")
    page: int
    size: int
    pages: int = Field(description="Total number of pages available")

    @classmethod
    def create(cls, items: list[T], total: int, page: int, size: int) -> Page[T]:
        """Build a page, deriving the page count from ``total`` and ``size``."""
        pages = -(-total // size) if size else 0
        return cls(items=items, total=total, page=page, size=size, pages=pages)


class ErrorResponse(BaseModel):
    """The single error envelope every failing request returns."""

    error: str = Field(description="Stable machine-readable error code")
    message: str = Field(description="Human-readable explanation")
    details: dict[str, Any] | None = None
    request_id: str | None = None


class Message(BaseModel):
    """Trivial acknowledgement payload."""

    message: str
