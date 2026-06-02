"""Seed page configurations for all ERP modules."""

from django.core.management.base import BaseCommand

from apps.core.services import page_config_service

PAGE_CONFIGS = [
    # Financial
    {
        "page_key": "chart-of-accounts",
        "page_title": "Chart of Accounts",
        "page_type": "list",
        "module": "financial",
        "entity_model": "Account",
        "api_endpoint": "/api/v1/financial/accounts/",
        "actions": [
            {
                "label": "Create",
                "endpoint": "/api/v1/financial/accounts/",
                "method": "POST",
                "confirm": False,
            },
            {
                "label": "Import",
                "endpoint": "/api/v1/financial/accounts/import/",
                "method": "POST",
                "confirm": False,
            },
        ],
        "fields": [
            {
                "field_name": "code",
                "label": "Code",
                "field_type": "text",
                "required": True,
                "is_column": True,
                "column_order": 1,
                "sortable": True,
                "filterable": True,
                "searchable": True,
            },
            {
                "field_name": "name",
                "label": "Name",
                "field_type": "text",
                "required": True,
                "is_column": True,
                "column_order": 2,
                "sortable": True,
                "searchable": True,
            },
            {
                "field_name": "account_type",
                "label": "Type",
                "field_type": "select",
                "is_column": True,
                "column_order": 3,
                "filterable": True,
                "options_source": "static",
                "options": [
                    {"label": "Asset", "value": "asset"},
                    {"label": "Liability", "value": "liability"},
                    {"label": "Equity", "value": "equity"},
                    {"label": "Income", "value": "income"},
                    {"label": "Expense", "value": "expense"},
                ],
            },
            {
                "field_name": "is_active",
                "label": "Active",
                "field_type": "checkbox",
                "is_column": True,
                "column_order": 4,
                "filterable": True,
            },
        ],
    },
    {
        "page_key": "journal-entry",
        "page_title": "Journal Entries",
        "page_type": "list",
        "module": "financial",
        "entity_model": "JournalEntry",
        "api_endpoint": "/api/v1/financial/journal-entries/",
        "actions": [
            {
                "label": "Create",
                "endpoint": "/api/v1/financial/journal-entries/",
                "method": "POST",
            },
        ],
        "fields": [
            {
                "field_name": "entry_number",
                "label": "Entry #",
                "field_type": "text",
                "is_column": True,
                "column_order": 1,
                "sortable": True,
                "searchable": True,
            },
            {
                "field_name": "date",
                "label": "Date",
                "field_type": "date",
                "is_column": True,
                "column_order": 2,
                "sortable": True,
                "filterable": True,
            },
            {
                "field_name": "description",
                "label": "Description",
                "field_type": "text",
                "is_column": True,
                "column_order": 3,
                "searchable": True,
            },
            {
                "field_name": "status",
                "label": "Status",
                "field_type": "select",
                "is_column": True,
                "column_order": 4,
                "filterable": True,
                "options_source": "static",
                "options": [
                    {"label": "Draft", "value": "draft"},
                    {"label": "Posted", "value": "posted"},
                    {"label": "Voided", "value": "voided"},
                ],
            },
        ],
    },
    {
        "page_key": "supplier-invoice",
        "page_title": "Supplier Invoices",
        "page_type": "list",
        "module": "financial",
        "entity_model": "SupplierInvoice",
        "api_endpoint": "/api/v1/financial/ap/invoices/",
        "fields": [
            {
                "field_name": "invoice_number",
                "label": "Invoice #",
                "field_type": "text",
                "is_column": True,
                "column_order": 1,
                "sortable": True,
                "searchable": True,
            },
            {
                "field_name": "supplier",
                "label": "Supplier",
                "field_type": "text",
                "is_column": True,
                "column_order": 2,
                "searchable": True,
            },
            {
                "field_name": "total",
                "label": "Total",
                "field_type": "decimal",
                "is_column": True,
                "column_order": 3,
                "sortable": True,
                "format": "#,##0.00",
            },
            {
                "field_name": "status",
                "label": "Status",
                "field_type": "select",
                "is_column": True,
                "column_order": 4,
                "filterable": True,
                "options_source": "static",
                "options": [
                    {"label": "Draft", "value": "draft"},
                    {"label": "Approved", "value": "approved"},
                    {"label": "Posted", "value": "posted"},
                ],
            },
        ],
    },
    # SCM
    {
        "page_key": "item-master",
        "page_title": "Items",
        "page_type": "list",
        "module": "scm",
        "entity_model": "Item",
        "api_endpoint": "/api/v1/scm/items/",
        "fields": [
            {
                "field_name": "code",
                "label": "Code",
                "field_type": "text",
                "is_column": True,
                "column_order": 1,
                "sortable": True,
                "searchable": True,
            },
            {
                "field_name": "name",
                "label": "Name",
                "field_type": "text",
                "is_column": True,
                "column_order": 2,
                "sortable": True,
                "searchable": True,
            },
            {
                "field_name": "item_type",
                "label": "Type",
                "field_type": "select",
                "is_column": True,
                "column_order": 3,
                "filterable": True,
                "options_source": "static",
                "options": [
                    {"label": "Product", "value": "product"},
                    {"label": "Service", "value": "service"},
                    {"label": "Raw Material", "value": "raw_material"},
                ],
            },
            {
                "field_name": "uom",
                "label": "UoM",
                "field_type": "text",
                "is_column": True,
                "column_order": 4,
            },
            {
                "field_name": "is_active",
                "label": "Active",
                "field_type": "checkbox",
                "is_column": True,
                "column_order": 5,
                "filterable": True,
            },
        ],
    },
    # CRM
    {
        "page_key": "customer",
        "page_title": "Customers",
        "page_type": "list",
        "module": "crm",
        "entity_model": "Customer",
        "api_endpoint": "/api/v1/crm/customers/",
        "fields": [
            {
                "field_name": "code",
                "label": "Code",
                "field_type": "text",
                "is_column": True,
                "column_order": 1,
                "sortable": True,
                "searchable": True,
            },
            {
                "field_name": "name",
                "label": "Name",
                "field_type": "text",
                "is_column": True,
                "column_order": 2,
                "sortable": True,
                "searchable": True,
            },
            {
                "field_name": "email",
                "label": "Email",
                "field_type": "email",
                "is_column": True,
                "column_order": 3,
                "searchable": True,
            },
            {
                "field_name": "phone",
                "label": "Phone",
                "field_type": "text",
                "is_column": True,
                "column_order": 4,
            },
            {
                "field_name": "is_active",
                "label": "Active",
                "field_type": "checkbox",
                "is_column": True,
                "column_order": 5,
                "filterable": True,
            },
        ],
    },
    # HRM
    {
        "page_key": "employee",
        "page_title": "Employees",
        "page_type": "list",
        "module": "hrm",
        "entity_model": "Employee",
        "api_endpoint": "/api/v1/hrm/employees/",
        "fields": [
            {
                "field_name": "employee_id",
                "label": "Employee ID",
                "field_type": "text",
                "is_column": True,
                "column_order": 1,
                "sortable": True,
                "searchable": True,
            },
            {
                "field_name": "first_name",
                "label": "First Name",
                "field_type": "text",
                "is_column": True,
                "column_order": 2,
                "sortable": True,
                "searchable": True,
            },
            {
                "field_name": "last_name",
                "label": "Last Name",
                "field_type": "text",
                "is_column": True,
                "column_order": 3,
                "sortable": True,
                "searchable": True,
            },
            {
                "field_name": "department",
                "label": "Department",
                "field_type": "select",
                "is_column": True,
                "column_order": 4,
                "filterable": True,
            },
            {
                "field_name": "is_active",
                "label": "Active",
                "field_type": "checkbox",
                "is_column": True,
                "column_order": 5,
                "filterable": True,
            },
        ],
    },
    # Admin
    {
        "page_key": "user-management",
        "page_title": "User Management",
        "page_type": "list",
        "module": "admin",
        "entity_model": "User",
        "api_endpoint": "/api/v1/core/auth/users/",
        "fields": [
            {
                "field_name": "email",
                "label": "Email",
                "field_type": "email",
                "is_column": True,
                "column_order": 1,
                "sortable": True,
                "searchable": True,
            },
            {
                "field_name": "first_name",
                "label": "First Name",
                "field_type": "text",
                "is_column": True,
                "column_order": 2,
                "sortable": True,
            },
            {
                "field_name": "last_name",
                "label": "Last Name",
                "field_type": "text",
                "is_column": True,
                "column_order": 3,
                "sortable": True,
            },
            {
                "field_name": "is_active",
                "label": "Active",
                "field_type": "checkbox",
                "is_column": True,
                "column_order": 4,
                "filterable": True,
            },
            {
                "field_name": "is_staff",
                "label": "Staff",
                "field_type": "checkbox",
                "is_column": True,
                "column_order": 5,
                "filterable": True,
            },
        ],
    },
]


class Command(BaseCommand):
    help = "Seed page configurations for all ERP modules"

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear", action="store_true", help="Clear existing configs before seeding"
        )

    def handle(self, *args, **options):
        if options["clear"]:
            from apps.core.models import PageConfig

            PageConfig.objects.all().delete()
            self.stdout.write(self.style.WARNING("Cleared all page configs."))

        created = 0
        updated = 0

        for config_data in PAGE_CONFIGS:
            fields_data = config_data.pop("fields", [])
            page_key = config_data["page_key"]

            try:
                from apps.core.models import PageConfig

                config = PageConfig.objects.get(page_key=page_key)
                for key, value in config_data.items():
                    setattr(config, key, value)
                config.save()
                updated += 1
                self.stdout.write(f"  UPDATED: {page_key}")
            except PageConfig.DoesNotExist:
                config = page_config_service.create_page_config(config_data)
                created += 1
                self.stdout.write(f"  CREATED: {page_key}")

            # Add fields
            for field_data in fields_data:
                try:
                    from apps.core.models import PageConfigField

                    PageConfigField.objects.get(
                        page_config=config, field_name=field_data["field_name"]
                    )
                except PageConfigField.DoesNotExist:
                    page_config_service.add_field(page_key, field_data)

        self.stdout.write(
            self.style.SUCCESS(f"Done! Created: {created}, Updated: {updated}")
        )
