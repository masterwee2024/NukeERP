"""Numbering series API — admin endpoints for document numbering configuration."""

from uuid import UUID

from ninja import Router, Schema
from ninja.errors import HttpError

from apps.core.mixins.models import ConcurrencyError
from apps.core.models import NumberingSeries
from apps.core.services import numbering_service

router = Router()


# --- Schemas ---


class NumberingSeriesCreateSchema(Schema):
    document_type: str
    prefix: str = ""
    date_format: str = ""
    next_number: int = 1
    reset_period: str = "yearly"
    padding: int = 6
    company_id: str
    description: str = ""


class NumberingSeriesUpdateSchema(Schema):
    document_type: str | None = None
    prefix: str | None = None
    date_format: str | None = None
    next_number: int | None = None
    reset_period: str | None = None
    padding: int | None = None
    company_id: str | None = None
    description: str | None = None
    updated_at: str | None = None


class NumberingSeriesOutSchema(Schema):
    id: str
    document_type: str
    prefix: str = ""
    date_format: str = ""
    next_number: int
    reset_period: str
    padding: int
    company: str
    company_name: str = ""
    description: str = ""
    is_active: bool = True
    last_reset_at: str | None = None
    created_at: str = ""
    updated_at: str = ""
    version: int = 1


class NumberingNextOut(Schema):
    number: str
    document_type: str


# --- Helpers ---


def _to_out(series: NumberingSeries) -> dict:
    """Convert a NumberingSeries instance to the output schema format."""
    return {
        "id": str(series.id),
        "document_type": series.document_type,
        "prefix": series.prefix,
        "date_format": series.date_format,
        "next_number": series.next_number,
        "reset_period": series.reset_period,
        "padding": series.padding,
        "company": str(series.company_id),
        "company_name": series.company.name if series.company else "",
        "description": series.description,
        "is_active": series.is_active,
        "last_reset_at": (
            series.last_reset_at.isoformat() if series.last_reset_at else None
        ),
        "created_at": series.created_at.isoformat() if series.created_at else "",
        "updated_at": series.updated_at.isoformat() if series.updated_at else "",
        "version": series.version,
    }


# --- Endpoints ---


@router.get("/numbering-series/", response=list[NumberingSeriesOutSchema])
def list_numbering_series(request):
    """List all numbering series (superuser only)."""
    if not request.auth.is_superuser:
        raise HttpError(403, "Access denied")
    series_list = numbering_service.list_series()
    return [_to_out(s) for s in series_list]


@router.get("/numbering-series/next/", response=NumberingNextOut)
def get_next_number(request, document_type: str, company_id: str):
    """Get next number for a document type (utility endpoint)."""
    if not request.auth.is_superuser:
        raise HttpError(403, "Access denied")
    try:
        number = numbering_service.get_next_number(document_type, company_id)
        return {"number": number, "document_type": document_type}
    except ValueError as e:
        raise HttpError(400, str(e)) from e


@router.post("/numbering-series/", response=NumberingSeriesOutSchema)
def create_numbering_series(request, payload: NumberingSeriesCreateSchema):
    """Create a new numbering series."""
    if not request.auth.is_superuser:
        raise HttpError(403, "Access denied")
    try:
        series = numbering_service.create_series(payload.model_dump())
        return _to_out(series)
    except ValueError as e:
        raise HttpError(400, str(e)) from e


@router.put("/numbering-series/{series_id}/", response=NumberingSeriesOutSchema)
def update_numbering_series(
    request, series_id: UUID, payload: NumberingSeriesUpdateSchema
):
    """Update a numbering series with optimistic locking."""
    if not request.auth.is_superuser:
        raise HttpError(403, "Access denied")

    try:
        series = numbering_service.update_series(
            str(series_id),
            payload.model_dump(exclude_unset=True),
            original_updated_at=payload.updated_at,
        )
        series.refresh_from_db()
        return _to_out(series)
    except ConcurrencyError as e:
        raise HttpError(409, str(e)) from e
    except ValueError as e:
        raise HttpError(404, str(e)) from e


@router.delete("/numbering-series/{series_id}/")
def delete_numbering_series(request, series_id: UUID):
    """Delete a numbering series."""
    if not request.auth.is_superuser:
        raise HttpError(403, "Access denied")
    try:
        numbering_service.delete_series(str(series_id))
        return {"detail": "Numbering series deleted"}
    except ValueError as e:
        raise HttpError(404, str(e)) from e
