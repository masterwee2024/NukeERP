"""Error response schemas for consistent API error format."""

from typing import Any

from ninja import Schema


class ErrorResponseSchema(Schema):
    """Single error response: { "detail": "message" }"""

    detail: str


class ValidationErrorResponseSchema(Schema):
    """Validation error response: { "errors": { "field": ["error1", "error2"] } }"""

    errors: dict[str, list[str]]


class ConflictResponseSchema(Schema):
    """409 Conflict response: { "detail": "...", "conflict": true }"""

    detail: str
    conflict: bool = True
    updated_at: Any = None
