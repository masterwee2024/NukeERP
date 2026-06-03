"""Seed default numbering series rules for all document types."""

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.core.models import Company, NumberingSeries

DEFAULT_RULES = [
    {
        "document_type": "supplier_invoice",
        "prefix": "SI-",
        "date_format": "YYYYMM",
        "reset_period": "yearly",
        "padding": 6,
        "description": "Supplier Invoice",
    },
    {
        "document_type": "customer_invoice",
        "prefix": "CI-",
        "date_format": "YYYYMM",
        "reset_period": "yearly",
        "padding": 6,
        "description": "Customer Invoice",
    },
    {
        "document_type": "purchase_order",
        "prefix": "PO-",
        "date_format": "YYYYMM",
        "reset_period": "yearly",
        "padding": 6,
        "description": "Purchase Order",
    },
    {
        "document_type": "sales_quotation",
        "prefix": "SQ-",
        "date_format": "YYYYMM",
        "reset_period": "yearly",
        "padding": 6,
        "description": "Sales Quotation",
    },
    {
        "document_type": "sales_order",
        "prefix": "SO-",
        "date_format": "YYYYMM",
        "reset_period": "yearly",
        "padding": 6,
        "description": "Sales Order",
    },
    {
        "document_type": "delivery_order",
        "prefix": "DO-",
        "date_format": "YYYYMM",
        "reset_period": "yearly",
        "padding": 6,
        "description": "Delivery Order",
    },
    {
        "document_type": "journal_entry",
        "prefix": "JE-",
        "date_format": "YYYYMM",
        "reset_period": "yearly",
        "padding": 6,
        "description": "Journal Entry",
    },
    {
        "document_type": "credit_note",
        "prefix": "CN-",
        "date_format": "YYYYMM",
        "reset_period": "yearly",
        "padding": 6,
        "description": "Credit Note",
    },
    {
        "document_type": "debit_note",
        "prefix": "DN-",
        "date_format": "YYYYMM",
        "reset_period": "yearly",
        "padding": 6,
        "description": "Debit Note",
    },
    {
        "document_type": "payment",
        "prefix": "PAY-",
        "date_format": "YYYYMM",
        "reset_period": "yearly",
        "padding": 6,
        "description": "Payment",
    },
    {
        "document_type": "grn",
        "prefix": "GRN-",
        "date_format": "YYYYMM",
        "reset_period": "yearly",
        "padding": 6,
        "description": "Goods Receipt Note",
    },
    {
        "document_type": "fixed_asset",
        "prefix": "FA-",
        "date_format": "",
        "reset_period": "never",
        "padding": 6,
        "description": "Fixed Asset",
    },
    {
        "document_type": "employee",
        "prefix": "EMP-",
        "date_format": "",
        "reset_period": "never",
        "padding": 6,
        "description": "Employee",
    },
    {
        "document_type": "purchase_requisition",
        "prefix": "PR-",
        "date_format": "YYYYMM",
        "reset_period": "yearly",
        "padding": 6,
        "description": "Purchase Requisition",
    },
    {
        "document_type": "rma",
        "prefix": "RMA-",
        "date_format": "YYYYMM",
        "reset_period": "yearly",
        "padding": 6,
        "description": "Return Merchandise Authorization",
    },
]


class Command(BaseCommand):
    help = "Seed default numbering series rules for all document types"

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Clear all existing series before seeding",
        )
        parser.add_argument(
            "--company", type=int, help="Company ID to seed (default: all companies)"
        )

    def handle(self, *args, **options):
        if options["clear"]:
            NumberingSeries.objects.all().delete()
            self.stdout.write(self.style.WARNING("Cleared all numbering series."))

        companies = Company.objects.all()
        if options["company"]:
            companies = companies.filter(id=options["company"])

        if not companies:
            self.stdout.write(
                self.style.WARNING("No companies found. Seed a company first.")
            )
            return

        created_count = 0
        updated_count = 0

        for company in companies:
            for rule in DEFAULT_RULES:
                obj, created = NumberingSeries.objects.update_or_create(
                    document_type=rule["document_type"],
                    company=company,
                    defaults={
                        "prefix": rule["prefix"],
                        "date_format": rule["date_format"],
                        "reset_period": rule["reset_period"],
                        "padding": rule["padding"],
                        "description": rule["description"],
                        "is_active": True,
                        "last_reset_at": timezone.now(),
                    },
                )
                if created:
                    created_count += 1
                else:
                    updated_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Done! Created: {created_count}, Updated: {updated_count} "
                f"across {companies.count()} companies."
            )
        )
