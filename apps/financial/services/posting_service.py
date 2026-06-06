"""Posting service — post journal entries to General Ledger."""

import logging
from datetime import date
from uuid import UUID

from django.core.cache import cache
from django.db import models, transaction
from django.utils import timezone

from apps.financial.models import (
    Account,
    AccountPeriodBalance,
    FinancialPeriod,
    GeneralLedger,
    JournalEntry,
    JournalEntryLine,
)

logger = logging.getLogger(__name__)


class PostingError(ValueError):
    """Raised when a journal entry cannot be posted."""

    pass


def _get_period(company_id: UUID, entry_date: date) -> FinancialPeriod | None:
    """Return the open financial period for a company/date, or None."""
    try:
        return FinancialPeriod.objects.get(
            company_id=company_id,
            start_date__lte=entry_date,
            end_date__gte=entry_date,
            is_open=True,
            is_closed=False,
        )
    except FinancialPeriod.DoesNotExist:
        return None


def _validate_period(company_id: UUID, entry_date: date) -> FinancialPeriod:
    """Raise PostingError if no open period exists for the given date."""
    period = _get_period(company_id, entry_date)
    if not period:
        raise PostingError(
            f"No open financial period found for {entry_date}. "
            "Create or open a period before posting."
        )
    return period


def _calculate_running_balance(
    account_id: UUID, company_id: UUID, entry_date: date
) -> float:
    """Calculate the running balance for an account before a given date."""
    last_entries = GeneralLedger.objects.filter(
        account_id=account_id,
        company_id=company_id,
        date__lt=entry_date,
    ).aggregate(
        total_debit=models.Sum("debit"),
        total_credit=models.Sum("credit"),
    )

    same_day_entries = GeneralLedger.objects.filter(
        account_id=account_id,
        company_id=company_id,
        date=entry_date,
    ).aggregate(
        total_debit=models.Sum("debit"),
        total_credit=models.Sum("credit"),
    )

    total_debit = float(last_entries["total_debit"] or 0) + float(
        same_day_entries["total_debit"] or 0
    )
    total_credit = float(last_entries["total_credit"] or 0) + float(
        same_day_entries["total_credit"] or 0
    )

    account = Account.objects.get(id=account_id)
    if account.account_type in ("asset", "expense"):
        return total_debit - total_credit
    else:
        return total_credit - total_debit


@transaction.atomic
def submit_for_approval(
    entry_id: UUID,
    requester,
    company_id: UUID,
    workflow_id: UUID | None = None,
) -> JournalEntry:
    """Submit a draft journal entry for approval.

    Creates a WorkflowExecution via the approval engine and sets
    the entry status to 'submitted'. If no workflow_id is given,
    auto-selects the first active workflow for this document type.
    """
    from apps.core.models import WorkflowDefinition
    from apps.core.services.workflow_service import create_execution

    entry = JournalEntry.objects.select_for_update().get(id=entry_id)

    if entry.status != "draft":
        raise PostingError(
            f"Cannot submit entry with status '{entry.status}'. "
            "Only draft entries can be submitted."
        )

    if workflow_id is None:
        workflow = (
            WorkflowDefinition.objects.filter(
                document_type="financial.JournalEntry",
                is_active=True,
            )
            .filter(models.Q(company_id=company_id) | models.Q(company__isnull=True))
            .order_by("-company_id")
            .first()
        )
        if not workflow:
            raise PostingError(
                "No active approval workflow found for Journal Entries. "
                "Create a workflow in Admin → Approval Workflows first."
            )
        workflow_id = workflow.id

    create_execution(
        workflow_id=workflow_id,
        document_type="financial.JournalEntry",
        document_id=entry.id,
        requester=requester,
        company_id=company_id,
    )

    entry.status = "submitted"
    entry.save(update_fields=["status", "updated_at", "version"])

    return entry


@transaction.atomic
def approve_submitted_entry(entry_id: UUID) -> JournalEntry:
    """Mark a submitted journal entry as approved (called on workflow completion)."""
    entry = JournalEntry.objects.select_for_update().get(id=entry_id)
    if entry.status != "submitted":
        return entry
    entry.status = "approved"
    entry.save(update_fields=["status", "updated_at", "version"])
    return entry


def _update_period_balance(account_id, company_id, period, debit, credit):
    """Update AccountPeriodBalance for a single line within a transaction.

    Uses select_for_update to prevent concurrent overwrites.
    """
    from decimal import Decimal

    balance, _ = AccountPeriodBalance.objects.select_for_update().get_or_create(
        account_id=account_id,
        company_id=company_id,
        period=period,
        defaults={
            "opening_debit": 0,
            "opening_credit": 0,
            "period_debit": 0,
            "period_credit": 0,
            "closing_debit": 0,
            "closing_credit": 0,
        },
    )

    db = Decimal(str(debit))
    cr = Decimal(str(credit))
    balance.period_debit += db
    balance.period_credit += cr
    balance.closing_debit += db
    balance.closing_credit += cr
    balance.save()


def _invalidate_report_cache(company_id: UUID):
    """Invalidate all report caches for a company when new GL data is posted."""
    try:
        cache.delete_pattern(f"*report*{company_id}*")
    except Exception:
        pass


@transaction.atomic
def post_journal_entry(entry_id: UUID, company_id: UUID | None = None) -> JournalEntry:
    """Post a journal entry to the General Ledger.

    Accepts 'draft' (direct post) or 'approved' (post-approval) statuses.
    Validates period is open, creates immutable GL entries with running
    balances, and marks the entry as posted.
    """
    filters = {"id": entry_id}
    if company_id:
        filters["company_id"] = company_id

    entry = (
        JournalEntry.objects.select_for_update()
        .filter(**filters)
        .select_related("company")
        .prefetch_related(
            models.Prefetch(
                "lines",
                queryset=JournalEntryLine.objects.select_related("account").order_by(
                    "line_number"
                ),
            )
        )
        .get()
    )

    if entry.status == "posted":
        raise PostingError("Journal entry is already posted")

    if entry.status == "reversed":
        raise PostingError("Cannot post a reversed journal entry")

    if entry.status not in ("draft", "approved"):
        raise PostingError(f"Cannot post journal entry with status '{entry.status}'")

    period = _validate_period(entry.company_id, entry.date)

    for line in entry.lines.all():
        balance = _calculate_running_balance(
            line.account_id, entry.company_id, entry.date
        )

        is_debit_normal = line.account.account_type in ("asset", "expense")
        if line.debit > 0:
            new_balance = (
                balance + float(line.debit)
                if is_debit_normal
                else balance - float(line.debit)
            )
        else:
            new_balance = (
                balance - float(line.credit)
                if is_debit_normal
                else balance + float(line.credit)
            )

        GeneralLedger.objects.create(
            journal_entry=entry,
            journal_entry_line=line,
            account=line.account,
            date=entry.date,
            debit=line.debit,
            credit=line.credit,
            balance=new_balance,
            company=entry.company,
            period=period,
        )

        _update_period_balance(
            line.account_id, entry.company_id, period, line.debit, line.credit
        )

    _invalidate_report_cache(entry.company_id)

    entry.status = "posted"
    entry.posted_at = timezone.now()
    entry.save(update_fields=["status", "posted_at", "updated_at", "version"])

    return entry
