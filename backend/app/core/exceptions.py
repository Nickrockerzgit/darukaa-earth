"""Domain-level exception hierarchy.

Services raise these; a single FastAPI exception handler maps them to HTTP
responses. This keeps HTTP status codes out of the business layer and gives
the API one consistent error envelope.
"""

from __future__ import annotations

from http import HTTPStatus
from typing import Any


class AppError(Exception):
    """Base class for every expected, handled application error."""

    status_code: int = HTTPStatus.INTERNAL_SERVER_ERROR
    error_code: str = "internal_error"
    default_message: str = "An unexpected error occurred."

    def __init__(self, message: str | None = None, **details: Any) -> None:
        self.message = message or self.default_message
        self.details: dict[str, Any] = details
        super().__init__(self.message)


class NotFoundError(AppError):
    """A requested resource does not exist (or is not visible to the caller)."""

    status_code = HTTPStatus.NOT_FOUND
    error_code = "not_found"
    default_message = "Resource not found."


class ConflictError(AppError):
    """The request collides with existing state, e.g. a duplicate unique key."""

    status_code = HTTPStatus.CONFLICT
    error_code = "conflict"
    default_message = "Resource already exists."


class ValidationError(AppError):
    """The payload is syntactically valid but violates a business rule."""

    status_code = HTTPStatus.UNPROCESSABLE_ENTITY
    error_code = "validation_error"
    default_message = "The submitted data is invalid."


class AuthenticationError(AppError):
    """Credentials are missing, malformed, or expired."""

    status_code = HTTPStatus.UNAUTHORIZED
    error_code = "authentication_error"
    default_message = "Could not validate credentials."


class PermissionDeniedError(AppError):
    """The caller is authenticated but not allowed to perform this action."""

    status_code = HTTPStatus.FORBIDDEN
    error_code = "permission_denied"
    default_message = "You do not have permission to perform this action."


class InvalidGeometryError(ValidationError):
    """The supplied GeoJSON geometry cannot be stored as a valid polygon."""

    error_code = "invalid_geometry"
    default_message = "The supplied geometry is not a valid polygon."
