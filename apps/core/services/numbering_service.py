"""Numbering service — business logic for document numbering."""

import datetime
from typing import Any

from django.db import transaction

from apps.core.mixins.models import ConcurrencyError
from apps.core.models import Company, NumberingSeries


def get_series(document_type: str, company: Company) -> NumberingSeries | None:
    """Get numbering series for a document type and company."""
    try:
        return NumberingSeries.objects.get(
            document_type=document_type, company=company, is_active=True
        )
    except NumberingSeries.DoesNotExist:
        return None


def _get_date_part(date_format: str) -> str:
    """Generate date component from format string."""
    if not date_format:
        return ""
    now = datetime.date.today()
    fmt = date_format.replace("YYYY", now.strftime("%Y"))
    fmt = fmt.replace("YY", now.strftime("%y"))
    fmt = fmt.replace("MM", now.strftime("%m"))
    fmt = fmt.replace("DD", now.strftime("%d"))
    return fmt


def _needs_reset(series: NumberingSeries) -> bool:
    """Check if the series needs to be reset based on reset_period."""
    now = datetime.date.today()
    if series.reset_period == "never":
        return False
    if not series.last_reset_at:
        return True
    if series.reset_period == "yearly":
        return series.last_reset_at.year != now.year
    if series.reset_period == "monthly":
        return (
            series.last_reset_at.year != now.year
            or series.last_reset_at.month != now.month
        )
    return False


def format_number(series: NumberingSeries, date_part: str) -> str:
    """Format the full document number."""
    padded = str(series.next_number).zfill(series.padding)
    return f"{series.prefix}{date_part}{padded}"


@transaction.atomic
def get_next_number(document_type: str, company_id: str) -> str:
    """Get the next number for a document type in a company.

    Uses select_for_update() to prevent race conditions.
    Returns the formatted number string.
    """
    try:
        company = Company.objects.get(id=company_id)
    except Company.DoesNotExist:
        raise ValueError(f"Company {company_id} not found") from None

    try:
        series = NumberingSeries.objects.select_for_update().get(
            document_type=document_type,
            company=company,
            is_active=True,
        )
    except NumberingSeries.DoesNotExist:
        raise ValueError(
            f"No active numbering series found for document_type='{document_type}' "
            f"and company='{company.name}'"
        ) from None

    if _needs_reset(series):
        series.next_number = 1
        series.last_reset_at = datetime.datetime.now(datetime.UTC)

    date_part = _get_date_part(series.date_format)
    number = format_number(series, date_part)

    series.next_number += 1
    series.save(update_fields=["next_number", "last_reset_at", "updated_at"])

    return number


def list_series(company_id: str | None = None) -> list[NumberingSeries]:
    """List numbering series, optionally filtered by company."""
    qs = NumberingSeries.objects.select_related("company").all()
    if company_id:
        qs = qs.filter(company_id=company_id)
    return list(qs.order_by("document_type"))


def create_series(data: dict[str, Any]) -> NumberingSeries:
    """Create a new numbering series."""
    company = Company.objects.get(id=data["company_id"])
    return NumberingSeries.objects.create(
        document_type=data["document_type"],
        prefix=data.get("prefix", ""),
        date_format=data.get("date_format", ""),
        next_number=data.get("next_number", 1),
        reset_period=data.get("reset_period", "yearly"),
        padding=data.get("padding", 6),
        company=company,
        description=data.get("description", ""),
        last_reset_at=datetime.datetime.now(datetime.UTC),
    )


def update_series(
    series_id: str, data: dict[str, Any], original_updated_at: str | None = None
) -> NumberingSeries:
    """Update an existing numbering series with concurrency control."""
    with transaction.atomic():
        try:
            series = NumberingSeries.objects.select_for_update().get(id=series_id)
        except NumberingSeries.DoesNotExist:
            raise ValueError("Numbering series not found") from None

        if original_updated_at:
            from django.utils.dateparse import parse_datetime

            client_ts = parse_datetime(original_updated_at)
            if client_ts:
                db_ts = series.updated_at
                if not db_ts:
                    raise ConcurrencyError(
                        "Record was modified by another user. Please reload and try again."
                    )
                if db_ts.tzinfo:
                    db_ts = db_ts.replace(tzinfo=None)
                if client_ts.tzinfo:
                    client_ts = client_ts.replace(tzinfo=None)
                if client_ts != db_ts:
                    raise ConcurrencyError(
                        "Record was modified by another user. Please reload and try again."
                    )

        for field in (
            "document_type",
            "prefix",
            "date_format",
            "next_number",
            "reset_period",
            "padding",
            "description",
        ):
            if field in data:
                setattr(series, field, data[field])
        if "company_id" in data:
            series.company = Company.objects.get(id=data["company_id"])
        series.save()
        return series


def delete_series(series_id: str) -> None:
    """Delete a numbering series."""
    try:
        series = NumberingSeries.objects.get(id=series_id)
    except NumberingSeries.DoesNotExist:
        raise ValueError("Numbering series not found") from None
    series.delete()
