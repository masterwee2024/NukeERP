"""Posting service — post journal entries to General Ledger."""

import logging
from datetime import date
from uuid import UUID

from django.db import models, transaction
from django.utils import timezone

from apps.financial.models import Account, GeneralLedger, JournalEntry, JournalEntryLine

logger = logging.getLogger(__name__)


class PostingError(ValueError):
    """Raised when a journal entry cannot be posted."""

    pass


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

    # Also include entries on the same date but created before this one
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
def post_journal_entry(entry_id: UUID) -> JournalEntry:
    """Post a draft journal entry to the General Ledger.

    Creates immutable GL entries, calculates running balances, and marks
    the entry as posted.
    """
    entry = (
        JournalEntry.objects.select_for_update()
        .select_related("company")
        .prefetch_related(
            models.Prefetch(
                "lines",
                queryset=JournalEntryLine.objects.select_related("account").order_by(
                    "line_number"
                ),
            )
        )
        .get(id=entry_id)
    )

    if entry.status == "posted":
        raise PostingError("Journal entry is already posted")

    if entry.status != "draft":
        raise PostingError(f"Cannot post journal entry with status '{entry.status}'")

    # Create GL entries for each line
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
        )

    entry.status = "posted"
    entry.posted_at = timezone.now()
    entry.save(update_fields=["status", "posted_at", "updated_at", "version"])

    return entry
