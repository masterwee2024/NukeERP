"""Seed default numbering policies and assign to all companies."""

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.core.models import Company, CompanyNumberingSeries, NumberingSeriesPolicy

DEFAULT_POLICIES = [
    {
        "document_type": "supplier_invoice",
        "prefix": "SI-",
        "date_format": "YYYYMM",
        "padding": 6,
        "description": "Supplier Invoice",
    },
    {
        "document_type": "customer_invoice",
        "prefix": "CI-",
        "date_format": "YYYYMM",
        "padding": 6,
        "description": "Customer Invoice",
    },
    {
        "document_type": "purchase_order",
        "prefix": "PO-",
        "date_format": "YYYYMM",
        "padding": 6,
        "description": "Purchase Order",
    },
    {
        "document_type": "sales_quotation",
        "prefix": "SQ-",
        "date_format": "YYYYMM",
        "padding": 6,
        "description": "Sales Quotation",
    },
    {
        "document_type": "sales_order",
        "prefix": "SO-",
        "date_format": "YYYYMM",
        "padding": 6,
        "description": "Sales Order",
    },
    {
        "document_type": "delivery_order",
        "prefix": "DO-",
        "date_format": "YYYYMM",
        "padding": 6,
        "description": "Delivery Order",
    },
    {
        "document_type": "journal_entry",
        "prefix": "JE-",
        "date_format": "YYYYMM",
        "padding": 6,
        "description": "Journal Entry",
    },
    {
        "document_type": "credit_note",
        "prefix": "CN-",
        "date_format": "YYYYMM",
        "padding": 6,
        "description": "Credit Note",
    },
    {
        "document_type": "debit_note",
        "prefix": "DN-",
        "date_format": "YYYYMM",
        "padding": 6,
        "description": "Debit Note",
    },
    {
        "document_type": "payment",
        "prefix": "PAY-",
        "date_format": "YYYYMM",
        "padding": 6,
        "description": "Payment",
    },
    {
        "document_type": "grn",
        "prefix": "GRN-",
        "date_format": "YYYYMM",
        "padding": 6,
        "description": "Goods Receipt Note",
    },
    {
        "document_type": "fixed_asset",
        "prefix": "FA-",
        "date_format": "",
        "padding": 6,
        "description": "Fixed Asset",
    },
    {
        "document_type": "employee",
        "prefix": "EMP-",
        "date_format": "",
        "padding": 4,
        "description": "Employee",
    },
    {
        "document_type": "purchase_requisition",
        "prefix": "PR-",
        "date_format": "YYYYMM",
        "padding": 6,
        "description": "Purchase Requisition",
    },
    {
        "document_type": "rma",
        "prefix": "RMA-",
        "date_format": "YYYYMM",
        "padding": 6,
        "description": "Return Merchandise Authorization",
    },
]


class Command(BaseCommand):
    help = "Seed default numbering policies and assign to all active companies"

    def handle(self, *args, **options):
        created_policies = 0
        updated_policies = 0
        total_assignments = 0

        for item in DEFAULT_POLICIES:
            policy, created = NumberingSeriesPolicy.objects.update_or_create(
                document_type=item["document_type"],
                defaults={
                    "prefix": item["prefix"],
                    "date_format": item["date_format"],
                    "padding": item["padding"],
                    "description": item["description"],
                    "is_active": True,
                },
            )
            if created:
                created_policies += 1
            else:
                updated_policies += 1

            # Assign to all active companies
            for company in Company.objects.filter(is_active=True):
                _, was_created = CompanyNumberingSeries.objects.get_or_create(
                    policy=policy,
                    company=company,
                    defaults={
                        "next_number": 1,
                        "reset_period": "yearly",
                        "last_reset_at": timezone.now(),
                    },
                )
                if was_created:
                    total_assignments += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Done! Policies: {created_policies} created, {updated_policies} updated. "
                f"Company assignments: {total_assignments} created."
            )
        )
