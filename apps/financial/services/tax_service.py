"""Tax service — SST calculation, rate lookup, SST-02 return generation."""

from datetime import date
from decimal import Decimal
from uuid import UUID

from apps.financial.models import TaxCode, TaxRate


def get_effective_rate(
    tax_code_id: UUID, entry_date: date | None = None
) -> TaxRate | None:
    """Get the effective tax rate for a tax code on a given date."""
    from django.db.models import Q

    if entry_date is None:
        from django.utils import timezone

        entry_date = timezone.now().date()

    return (
        TaxRate.objects.filter(
            Q(tax_code_id=tax_code_id),
            Q(effective_from__lte=entry_date),
            Q(effective_to__isnull=True) | Q(effective_to__gte=entry_date),
        )
        .order_by("-effective_from")
        .first()
    )


def calculate_tax(
    amount: Decimal, tax_code_id: UUID, entry_date: date | None = None
) -> dict:
    """Calculate tax amount for a given amount and tax code.

    Returns dict with: tax_amount, rate_percent, tax_code_code, tax_code_name, tax_type.
    """
    rate = get_effective_rate(tax_code_id, entry_date)
    if rate is None:
        tax_code = TaxCode.objects.get(id=tax_code_id)
        rate_percent = tax_code.rate_percent
    else:
        tax_code = rate.tax_code
        rate_percent = rate.rate_percent

    tax_amount = Decimal(str(amount)) * Decimal(str(rate_percent)) / Decimal("100")
    return {
        "tax_amount": round(tax_amount, 2),
        "rate_percent": rate_percent,
        "tax_code_code": tax_code.code,
        "tax_code_name": tax_code.name,
        "tax_type": tax_code.tax_type,
    }


def get_sst_return(company_id: UUID, year: int, month: int) -> dict:
    """Generate SST-02 return data for a company and period.

    Aggregates output tax (sales/service) and input tax (purchases) from GL.
    """
    from apps.financial.models import GeneralLedger

    start_date = date(year, month, 1)
    if month == 12:
        end_date = date(year + 1, 1, 1)
    else:
        end_date = date(year, month + 1, 1)

    gl_entries = GeneralLedger.objects.filter(
        company_id=company_id,
        date__gte=start_date,
        date__lt=end_date,
    ).select_related("account")

    total_output_tax = Decimal("0")
    total_input_tax = Decimal("0")
    taxable_sales = Decimal("0")
    taxable_purchases = Decimal("0")

    for entry in gl_entries:
        if entry.account.account_type == "revenue":
            taxable_sales += entry.credit
            taxable_sales -= entry.debit
        elif entry.account.account_type == "expense":
            taxable_purchases += entry.debit
            taxable_purchases -= entry.credit

    output_tax_codes = TaxCode.objects.filter(
        tax_type__in=("sales", "service"), is_active=True
    )
    for tc in output_tax_codes:
        rate = get_effective_rate(tc.id, start_date)
        rate_pct = rate.rate_percent if rate else tc.rate_percent
        total_output_tax += taxable_sales * rate_pct / Decimal("100")

    return {
        "period": f"{year}-{month:02d}",
        "total_output_tax": round(total_output_tax, 2),
        "total_input_tax": round(total_input_tax, 2),
        "net_tax_payable": round(total_output_tax - total_input_tax, 2),
        "taxable_sales": round(taxable_sales, 2),
        "taxable_purchases": round(taxable_purchases, 2),
    }
