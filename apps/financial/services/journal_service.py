"""Journal entry service — CRUD, reversal, balance validation."""

import logging
from datetime import date
from uuid import UUID

from django.db import transaction
from django.utils import timezone

from apps.core.services.numbering_service import get_next_number
from apps.financial.models import Account, JournalEntry, JournalEntryLine

logger = logging.getLogger(__name__)


class BalanceError(ValueError):
    """Raised when journal entry debits != credits."""

    pass


def _validate_balance(lines: list[dict]) -> None:
    """Validate that total debits equal total credits."""
    total_debit = sum(float(line.get("debit", 0)) for line in lines)
    total_credit = sum(float(line.get("credit", 0)) for line in lines)
    if abs(total_debit - total_credit) > 0.001:
        raise BalanceError(
            f"Journal entry is not balanced. Total debit: {total_debit}, Total credit: {total_credit}"
        )


def _validate_accounts_exist(lines: list[dict]) -> None:
    """Validate that all account IDs reference existing accounts."""
    for line in lines:
        account_id = line.get("account_id")
        if account_id:
            if not Account.objects.filter(id=account_id).exists():
                raise ValueError(f"Account {account_id} not found")


@transaction.atomic
def create_journal_entry(
    date: date,
    description: str,
    lines: list[dict],
    company_id: UUID,
    reference: str = "",
    created_by_id: UUID | None = None,
) -> JournalEntry:
    """Create a balanced journal entry with lines."""
    if not lines:
        raise ValueError("Journal entry must have at least one line")

    _validate_balance(lines)
    _validate_accounts_exist(lines)

    entry_number = get_next_number("journal_entry", str(company_id))
    total_debit = sum(float(line.get("debit", 0)) for line in lines)
    total_credit = sum(float(line.get("credit", 0)) for line in lines)

    entry = JournalEntry.objects.create(
        entry_number=entry_number,
        date=date,
        description=description,
        reference=reference,
        status="draft",
        company_id=company_id,
        total_debit=total_debit,
        total_credit=total_credit,
        created_by_id=created_by_id,
    )

    for i, line_data in enumerate(lines):
        JournalEntryLine.objects.create(
            journal_entry=entry,
            account_id=line_data["account_id"],
            debit=line_data.get("debit", 0),
            credit=line_data.get("credit", 0),
            description=line_data.get("description", ""),
            line_number=i + 1,
        )

    return entry


@transaction.atomic
def update_journal_entry(
    entry_id: UUID,
    date: date | None = None,
    description: str | None = None,
    reference: str | None = None,
    lines: list[dict] | None = None,
) -> JournalEntry:
    """Update a draft journal entry. Raises ValueError if already posted."""
    entry = JournalEntry.objects.select_for_update().get(id=entry_id)

    if entry.status != "draft":
        raise ValueError("Cannot edit a posted or reversed journal entry")

    if lines is not None:
        _validate_balance(lines)
        _validate_accounts_exist(lines)
        entry.total_debit = sum(float(line.get("debit", 0)) for line in lines)
        entry.total_credit = sum(float(line.get("credit", 0)) for line in lines)

    if date is not None:
        entry.date = date
    if description is not None:
        entry.description = description
    if reference is not None:
        entry.reference = reference

    entry.save()

    if lines is not None:
        entry.lines.all().delete()
        for i, line_data in enumerate(lines):
            JournalEntryLine.objects.create(
                journal_entry=entry,
                account_id=line_data["account_id"],
                debit=line_data.get("debit", 0),
                credit=line_data.get("credit", 0),
                description=line_data.get("description", ""),
                line_number=i + 1,
            )

    return entry


@transaction.atomic
def delete_journal_entry(entry_id: UUID) -> None:
    """Delete a draft journal entry."""
    entry = JournalEntry.objects.select_for_update().get(id=entry_id)
    if entry.status != "draft":
        raise ValueError("Cannot delete a posted or reversed journal entry")
    entry.lines.all().delete()
    entry.delete()


@transaction.atomic
def reverse_journal_entry(
    entry_id: UUID, created_by_id: UUID | None = None
) -> JournalEntry:
    """Reverse a posted journal entry by swapping debits and credits."""
    original = JournalEntry.objects.select_for_update().get(id=entry_id)

    if original.status != "posted":
        raise ValueError("Only posted journal entries can be reversed")

    if original.reversal_of_id:
        raise ValueError("Cannot reverse a reversal entry")

    lines_data = [
        {
            "account_id": str(line.account_id),
            "debit": line.credit,
            "credit": line.debit,
            "description": f"Reversal: {line.description or original.description}",
        }
        for line in original.lines.all()
    ]

    reversal = create_journal_entry(
        date=timezone.now().date(),
        description=f"Reversal of {original.entry_number}: {original.description}",
        lines=lines_data,
        company_id=original.company_id,
        reference=original.entry_number,
        created_by_id=created_by_id,
    )

    reversal.reversal_of = original
    reversal.save(update_fields=["reversal_of"])

    original.status = "reversed"
    original.save(update_fields=["status", "updated_at", "version"])

    return reversal
