"""Seed default Tax Codes and Tax Rates for SST."""

from datetime import date

from django.core.management.base import BaseCommand

from apps.financial.models import TaxCode, TaxRate

DEFAULT_TAX_CODES = [
    {"code": "SR", "name": "Standard Rate (Sales)", "rate": 8.00, "type": "sales"},
    {
        "code": "SR-S",
        "name": "Standard Rate (Service)",
        "rate": 8.00,
        "type": "service",
    },
    {"code": "ZR", "name": "Zero-Rated", "rate": 0.00, "type": "zero_rated"},
    {"code": "ES", "name": "Exempt Supply", "rate": 0.00, "type": "exempt"},
    {"code": "OS", "name": "Out of Scope", "rate": 0.00, "type": "out_of_scope"},
    {"code": "DX", "name": "Deemed Supply (Sales)", "rate": 8.00, "type": "sales"},
    {"code": "IM", "name": "Input Tax (Purchases)", "rate": 8.00, "type": "purchase"},
]


class Command(BaseCommand):
    help = "Seed default tax codes and rates for SST"

    def handle(self, *args, **options):
        created = 0
        existing = 0

        for entry in DEFAULT_TAX_CODES:
            tc, was_created = TaxCode.objects.get_or_create(
                code=entry["code"],
                defaults={
                    "name": entry["name"],
                    "rate_percent": entry["rate"],
                    "tax_type": entry["type"],
                },
            )
            if was_created:
                TaxRate.objects.create(
                    tax_code=tc,
                    rate_percent=entry["rate"],
                    effective_from=date(2024, 1, 1),
                    is_current=True,
                )
                created += 1
            else:
                existing += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded {created} tax codes ({existing} already existed)"
            )
        )
