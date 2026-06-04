"""Journal Entry API — CRUD, list, reverse."""

import logging
from datetime import date
from uuid import UUID

from django.db import models
from ninja import Router, Schema
from ninja.errors import HttpError

from apps.core.api.auth import JWTAuth
from apps.financial.models import JournalEntry, JournalEntryLine
from apps.financial.services.journal_service import (
    create_journal_entry,
    delete_journal_entry,
    reverse_journal_entry,
    update_journal_entry,
)

logger = logging.getLogger(__name__)

router = Router(auth=JWTAuth())


def _require_company_id(request) -> UUID:
    company_id = request.headers.get("x-company-id")
    if not company_id:
        raise HttpError(400, "X-Company-Id header is required")
    try:
        return UUID(company_id)
    except ValueError:
        raise HttpError(400, "Invalid X-Company-Id header") from None


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class JournalEntryLineOut(Schema):
    id: str
    account_id: str
    account_code: str = ""
    account_name: str = ""
    debit: float = 0
    credit: float = 0
    description: str = ""
    line_number: int = 0

    @staticmethod
    def resolve_id(obj):
        return str(obj.id)

    @staticmethod
    def resolve_account_id(obj):
        return str(obj.account_id)

    @staticmethod
    def resolve_account_code(obj):
        return obj.account.code if obj.account else ""

    @staticmethod
    def resolve_account_name(obj):
        return obj.account.name if obj.account else ""


class JournalEntryOut(Schema):
    id: str
    entry_number: str
    date: str
    description: str = ""
    reference: str = ""
    status: str
    company_id: str
    total_debit: float = 0
    total_credit: float = 0
    created_by_name: str = ""
    reversal_of_id: str | None = None
    lines: list[JournalEntryLineOut] = []
    created_at: str = ""
    updated_at: str = ""

    @staticmethod
    def resolve_id(obj):
        return str(obj.id)

    @staticmethod
    def resolve_company_id(obj):
        return str(obj.company_id)

    @staticmethod
    def resolve_created_by_name(obj):
        return obj.created_by.full_name if obj.created_by else ""

    @staticmethod
    def resolve_reversal_of_id(obj):
        return str(obj.reversal_of_id) if obj.reversal_of_id else None

    @staticmethod
    def resolve_date(obj):
        return obj.date.isoformat() if obj.date else ""

    @staticmethod
    def resolve_created_at(obj):
        return obj.created_at.isoformat() if obj.created_at else ""

    @staticmethod
    def resolve_updated_at(obj):
        return obj.updated_at.isoformat() if obj.updated_at else ""


class JournalEntryListOut(Schema):
    count: int
    results: list[JournalEntryOut]


class JournalEntryLineIn(Schema):
    account_id: str
    debit: float = 0
    credit: float = 0
    description: str = ""


class JournalEntryCreateIn(Schema):
    date: str
    description: str
    lines: list[JournalEntryLineIn]
    reference: str = ""


class JournalEntryUpdateIn(Schema):
    date: str | None = None
    description: str | None = None
    reference: str | None = None
    lines: list[JournalEntryLineIn] | None = None


class JournalEntryReverseOut(Schema):
    id: str
    entry_number: str
    status: str
    reversal_of_id: str | None = None

    @staticmethod
    def resolve_id(obj):
        return str(obj.id)

    @staticmethod
    def resolve_reversal_of_id(obj):
        return str(obj.reversal_of_id) if obj.reversal_of_id else None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/journal-entries/", response=JournalEntryListOut)
def list_entries(
    request, page: int = 1, page_size: int = 50, status: str = "", search: str = ""
):
    """List journal entries with filters."""
    company_id = _require_company_id(request)
    qs = (
        JournalEntry.objects.filter(company_id=company_id)
        .select_related("created_by")
        .order_by("-date", "-created_at")
    )

    if status:
        qs = qs.filter(status=status)
    if search:
        qs = qs.filter(
            models.Q(entry_number__icontains=search)
            | models.Q(description__icontains=search)
            | models.Q(reference__icontains=search)
        )

    total = qs.count()
    start = (page - 1) * page_size
    end = start + page_size
    items = qs[start:end]

    return {"count": total, "results": list(items)}


@router.get("/journal-entries/{id}/", response=JournalEntryOut)
def get_entry(request, id: UUID):
    """Get a single journal entry with lines."""
    company_id = _require_company_id(request)
    try:
        entry = (
            JournalEntry.objects.select_related("created_by")
            .prefetch_related(
                models.Prefetch(
                    "lines",
                    queryset=JournalEntryLine.objects.select_related(
                        "account"
                    ).order_by("line_number"),
                )
            )
            .get(id=id, company_id=company_id)
        )
        return entry
    except JournalEntry.DoesNotExist:
        raise HttpError(404, "Journal entry not found") from None


@router.post("/journal-entries/", response=JournalEntryOut)
def create(request, payload: JournalEntryCreateIn):
    """Create a new journal entry."""
    company_id = _require_company_id(request)

    try:
        entry_date = date.fromisoformat(payload.date)
    except ValueError:
        raise HttpError(400, "Invalid date format. Use YYYY-MM-DD") from None

    lines_data = [
        {
            "account_id": UUID(line.account_id),
            "debit": line.debit,
            "credit": line.credit,
            "description": line.description,
        }
        for line in payload.lines
    ]

    try:
        entry = create_journal_entry(
            date=entry_date,
            description=payload.description,
            lines=lines_data,
            company_id=company_id,
            reference=payload.reference,
            created_by_id=request.auth.id,
        )
        return (
            JournalEntry.objects.select_related("created_by")
            .prefetch_related(
                models.Prefetch(
                    "lines", JournalEntryLine.objects.select_related("account")
                )
            )
            .get(id=entry.id)
        )
    except ValueError as e:
        raise HttpError(400, str(e)) from e


@router.put("/journal-entries/{id}/", response=JournalEntryOut)
def update(request, id: UUID, payload: JournalEntryUpdateIn):
    """Update a draft journal entry."""
    company_id = _require_company_id(request)

    try:
        JournalEntry.objects.get(id=id, company_id=company_id)
    except JournalEntry.DoesNotExist:
        raise HttpError(404, "Journal entry not found") from None

    entry_date = None
    if payload.date:
        try:
            entry_date = date.fromisoformat(payload.date)
        except ValueError:
            raise HttpError(400, "Invalid date format. Use YYYY-MM-DD") from None

    lines_data = None
    if payload.lines is not None:
        lines_data = [
            {
                "account_id": UUID(line.account_id),
                "debit": line.debit,
                "credit": line.credit,
                "description": line.description,
            }
            for line in payload.lines
        ]

    try:
        updated = update_journal_entry(
            entry_id=id,
            date=entry_date,
            description=payload.description,
            reference=payload.reference,
            lines=lines_data,
        )
        return (
            JournalEntry.objects.select_related("created_by")
            .prefetch_related(
                models.Prefetch(
                    "lines", JournalEntryLine.objects.select_related("account")
                )
            )
            .get(id=updated.id)
        )
    except ValueError as e:
        raise HttpError(400, str(e)) from e


@router.delete("/journal-entries/{id}/")
def delete(request, id: UUID):
    """Delete a draft journal entry."""
    try:
        delete_journal_entry(id)
        return {"success": True}
    except ValueError as e:
        raise HttpError(400, str(e)) from e


@router.post("/journal-entries/{id}/reverse/", response=JournalEntryReverseOut)
def reverse(request, id: UUID):
    """Reverse a posted journal entry."""
    try:
        reversal = reverse_journal_entry(id, created_by_id=request.auth.id)
        return reversal
    except ValueError as e:
        raise HttpError(400, str(e)) from e
