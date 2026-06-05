"""Period management service — close/reopen periods, year-end close."""

import logging
from datetime import date, timedelta
from uuid import UUID

from django.db import transaction
from django.db.models import Sum

from apps.financial.models import (
    Account,
    FinancialPeriod,
    FinancialYear,
    GeneralLedger,
    JournalEntry,
)

logger = logging.getLogger(__name__)

MONTH_NAMES = [
    "",
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
]


class PeriodError(ValueError):
    pass


def _get_retained_earnings_account(company_id: UUID) -> Account | None:
    """Find the retained earnings account for a company.

    Looks for an equity account with 'retained' in the name, or any equity
    account that could serve as retained earnings.
    """
    accounts = Account.objects.filter(
        account_type="equity",
        is_active=True,
    )
    # Prefer accounts with 'retained' in the name
    retained = accounts.filter(name__icontains="retained").first()
    if retained:
        return retained
    return accounts.first()


@transaction.atomic
def close_period(period_id: UUID) -> FinancialPeriod:
    """Close a period — prevent further postings.

    Validates no unposted journal entries exist for the period date range.
    """
    period = FinancialPeriod.objects.select_for_update().get(id=period_id)

    if period.is_closed:
        raise PeriodError("Period is already closed for year-end")

    if not period.is_open:
        raise PeriodError("Period is already closed")

    # Check for unposted entries in this period's date range
    unposted = JournalEntry.objects.filter(
        company_id=period.company_id,
        date__gte=period.start_date,
        date__lte=period.end_date,
    ).exclude(status__in=["posted", "reversed"])

    if unposted.exists():
        raise PeriodError(
            f"Cannot close period. There are {unposted.count()} unposted "
            f"journal entries in this period. Post or delete them first."
        )

    period.is_open = False
    period.save(update_fields=["is_open", "updated_at", "version"])
    return period


@transaction.atomic
def reopen_period(period_id: UUID) -> FinancialPeriod:
    """Reopen a closed period for posting (admin use only)."""
    period = FinancialPeriod.objects.select_for_update().get(id=period_id)

    if period.is_closed:
        raise PeriodError("Cannot reopen a year-end closed period")

    if period.is_open:
        raise PeriodError("Period is already open")

    period.is_open = True
    period.save(update_fields=["is_open", "updated_at", "version"])
    return period


@transaction.atomic
def year_end_close(
    year_id: UUID,
    retained_earnings_account_id: UUID | None = None,
) -> dict:
    """Perform year-end close for a financial year.

    1. Validates all periods in the year are closed
    2. Transfers P&L account balances to retained earnings
    3. Creates new financial year with 12 periods
    4. Locks the old financial year

    Returns dict with transfer details and new year info.
    """
    fin_year = FinancialYear.objects.select_for_update().get(id=year_id)
    company_id = fin_year.company_id

    if fin_year.is_closed:
        raise PeriodError("Financial year is already closed")

    # Close all open periods except the last one (for the closing entry)
    all_periods = list(
        FinancialPeriod.objects.filter(financial_year=fin_year).order_by("start_date")
    )
    last_period = all_periods[-1] if all_periods else None
    for period in all_periods:
        if period.id != (last_period.id if last_period else None):
            period.is_open = False
            period.save(update_fields=["is_open", "updated_at", "version"])

    # Ensure the last period is open for the closing entry
    if last_period and not last_period.is_open:
        last_period.is_open = True
        last_period.save(update_fields=["is_open", "updated_at", "version"])

    # Find retained earnings account
    re_account = None
    if retained_earnings_account_id:
        re_account = Account.objects.filter(id=retained_earnings_account_id).first()
    if not re_account:
        re_account = _get_retained_earnings_account(company_id)
    if not re_account:
        raise PeriodError(
            "No retained earnings account found. "
            "Create an equity account with 'retained' in the name, "
            "or pass retained_earnings_account_id."
        )

    # Calculate P&L balances for the year
    revenue_accounts = Account.objects.filter(account_type="revenue", is_active=True)
    expense_accounts = Account.objects.filter(account_type="expense", is_active=True)

    total_revenue = 0.0
    total_expense = 0.0

    # Only consider accounts assigned to this company via AccountCompany
    from apps.financial.models import AccountCompany

    company_account_ids = set(
        AccountCompany.objects.filter(
            company_id=company_id, is_active=True
        ).values_list("account_id", flat=True)
    )

    for acct in revenue_accounts:
        if acct.id not in company_account_ids:
            continue
        balance = GeneralLedger.objects.filter(
            account=acct,
            company_id=company_id,
            date__gte=fin_year.start_date,
            date__lte=fin_year.end_date,
        ).aggregate(debit=Sum("debit"), credit=Sum("credit"))
        total_revenue += float(balance["credit"] or 0) - float(balance["debit"] or 0)

    for acct in expense_accounts:
        if acct.id not in company_account_ids:
            continue
        balance = GeneralLedger.objects.filter(
            account=acct,
            company_id=company_id,
            date__gte=fin_year.start_date,
            date__lte=fin_year.end_date,
        ).aggregate(debit=Sum("debit"), credit=Sum("credit"))
        total_expense += float(balance["debit"] or 0) - float(balance["credit"] or 0)

    net_income = total_revenue - total_expense

    # Create closing journal entry
    from apps.financial.services.journal_service import create_journal_entry

    closing_date = fin_year.end_date
    lines = []

    # Close revenue accounts (debit revenue to zero, credit retained earnings)
    for acct in revenue_accounts:
        if acct.id not in company_account_ids:
            continue
        bal = GeneralLedger.objects.filter(
            account=acct,
            company_id=company_id,
            date__gte=fin_year.start_date,
            date__lte=fin_year.end_date,
        ).aggregate(debit=Sum("debit"), credit=Sum("credit"))
        credit_balance = float(bal["credit"] or 0) - float(bal["debit"] or 0)
        if abs(credit_balance) > 0.01:
            lines.append(
                {
                    "account_id": str(acct.id),
                    "debit": credit_balance if credit_balance > 0 else 0,
                    "credit": abs(credit_balance) if credit_balance < 0 else 0,
                    "description": f"Year-end close: close {acct.name}",
                }
            )

    # Close expense accounts (credit expense to zero, debit retained earnings)
    for acct in expense_accounts:
        if acct.id not in company_account_ids:
            continue
        bal = GeneralLedger.objects.filter(
            account=acct,
            company_id=company_id,
            date__gte=fin_year.start_date,
            date__lte=fin_year.end_date,
        ).aggregate(debit=Sum("debit"), credit=Sum("credit"))
        debit_balance = float(bal["debit"] or 0) - float(bal["credit"] or 0)
        if abs(debit_balance) > 0.01:
            lines.append(
                {
                    "account_id": str(acct.id),
                    "debit": 0,
                    "credit": debit_balance if debit_balance > 0 else 0,
                    "description": f"Year-end close: close {acct.name}",
                }
            )

    # Add retained earnings entry
    if abs(net_income) > 0.01:
        if net_income > 0:
            lines.append(
                {
                    "account_id": str(re_account.id),
                    "debit": 0,
                    "credit": net_income,
                    "description": "Year-end close: net income transfer",
                }
            )
        else:
            lines.append(
                {
                    "account_id": str(re_account.id),
                    "debit": abs(net_income),
                    "credit": 0,
                    "description": "Year-end close: net loss transfer",
                }
            )

    if lines:
        closing_entry = create_journal_entry(
            date=closing_date,
            description=f"Year-end closing entry for {fin_year.name}",
            lines=lines,
            company_id=company_id,
            reference=f"YE-{fin_year.name}",
        )
        from apps.financial.services.posting_service import post_journal_entry

        post_journal_entry(closing_entry.id)

    # Create new financial year with 12 monthly periods
    new_year_name = _next_year_name(fin_year.name)
    new_start = _next_year_start(fin_year.start_date)

    new_year = FinancialYear.objects.create(
        company_id=company_id,
        name=new_year_name,
        start_date=new_start,
        end_date=date(new_start.year, 12, 31),
    )

    for month in range(1, 13):
        month_start = date(new_start.year, month, 1)
        if month == 12:
            month_end = date(new_start.year, 12, 31)
        else:
            month_end = date(new_start.year, month + 1, 1) - timedelta(days=1)
        FinancialPeriod.objects.create(
            company_id=company_id,
            financial_year=new_year,
            name=f"{MONTH_NAMES[month]} {new_start.year}",
            start_date=month_start,
            end_date=month_end,
            is_open=True,
        )

    # Close the last period too
    if last_period:
        last_period.is_open = False
        last_period.save(update_fields=["is_open", "updated_at", "version"])

    # Lock old financial year
    fin_year.is_closed = True
    fin_year.save(update_fields=["is_closed", "updated_at", "version"])

    return {
        "closed_year": str(fin_year.id),
        "new_year": str(new_year.id),
        "new_year_name": new_year_name,
        "net_income_transferred": net_income,
        "total_lines_created": len(lines),
    }


def _next_year_name(current_name: str) -> str:
    """Increment the year in a financial year name."""
    import re

    match = re.search(r"\d{4}", current_name)
    if match:
        year = int(match.group())
        return current_name.replace(str(year), str(year + 1), 1)
    return f"FY {date.today().year + 1}"


def _next_year_start(current_start: date) -> date:
    """Return the start date for the next financial year."""
    return date(current_start.year + 1, current_start.month, current_start.day)


@transaction.atomic
def create_initial_periods(
    company_id: UUID,
    year: int = 2026,
) -> FinancialYear:
    """Create a financial year with 12 monthly periods for a company."""
    fin_year = FinancialYear.objects.create(
        company_id=company_id,
        name=f"FY {year}",
        start_date=date(year, 1, 1),
        end_date=date(year, 12, 31),
    )
    for month in range(1, 13):
        month_start = date(year, month, 1)
        if month == 12:
            month_end = date(year, 12, 31)
        else:
            month_end = date(year, month + 1, 1) - timedelta(days=1)
        FinancialPeriod.objects.create(
            company_id=company_id,
            financial_year=fin_year,
            name=f"{MONTH_NAMES[month]} {year}",
            start_date=month_start,
            end_date=month_end,
            is_open=True,
        )
    return fin_year
