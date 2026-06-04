"""Seed default Chart of Accounts structure."""

from django.core.management.base import BaseCommand

from apps.financial.models import Account

DEFAULT_ACCOUNTS = [
    # Level 0
    {
        "code": "1000",
        "name": "Assets",
        "type": "asset",
        "subtype": "",
        "parent_code": None,
    },
    {
        "code": "2000",
        "name": "Liabilities",
        "type": "liability",
        "subtype": "",
        "parent_code": None,
    },
    {
        "code": "3000",
        "name": "Equity",
        "type": "equity",
        "subtype": "",
        "parent_code": None,
    },
    {
        "code": "4000",
        "name": "Revenue",
        "type": "revenue",
        "subtype": "",
        "parent_code": None,
    },
    {
        "code": "5000",
        "name": "Cost of Sales",
        "type": "expense",
        "subtype": "cost_of_sales",
        "parent_code": None,
    },
    {
        "code": "6000",
        "name": "Operating Expenses",
        "type": "expense",
        "subtype": "operating_expense",
        "parent_code": None,
    },
    # Level 1 — Assets
    {
        "code": "1100",
        "name": "Current Assets",
        "type": "asset",
        "subtype": "current_asset",
        "parent_code": "1000",
    },
    {
        "code": "1200",
        "name": "Non-Current Assets",
        "type": "asset",
        "subtype": "non_current_asset",
        "parent_code": "1000",
    },
    # Level 1 — Liabilities
    {
        "code": "2100",
        "name": "Current Liabilities",
        "type": "liability",
        "subtype": "current_liability",
        "parent_code": "2000",
    },
    {
        "code": "2200",
        "name": "Long-Term Liabilities",
        "type": "liability",
        "subtype": "long_term_liability",
        "parent_code": "2000",
    },
    # Level 2 — Current Assets
    {
        "code": "1110",
        "name": "Cash and Cash Equivalents",
        "type": "asset",
        "subtype": "current_asset",
        "parent_code": "1100",
    },
    {
        "code": "1120",
        "name": "Accounts Receivable",
        "type": "asset",
        "subtype": "current_asset",
        "parent_code": "1100",
    },
    {
        "code": "1130",
        "name": "Inventory",
        "type": "asset",
        "subtype": "current_asset",
        "parent_code": "1100",
    },
    {
        "code": "1140",
        "name": "Prepaid Expenses",
        "type": "asset",
        "subtype": "current_asset",
        "parent_code": "1100",
    },
    # Level 2 — Non-Current Assets
    {
        "code": "1210",
        "name": "Fixed Assets",
        "type": "asset",
        "subtype": "non_current_asset",
        "parent_code": "1200",
    },
    {
        "code": "1220",
        "name": "Accumulated Depreciation",
        "type": "asset",
        "subtype": "non_current_asset",
        "parent_code": "1200",
    },
    # Level 2 — Current Liabilities
    {
        "code": "2110",
        "name": "Accounts Payable",
        "type": "liability",
        "subtype": "current_liability",
        "parent_code": "2100",
    },
    {
        "code": "2120",
        "name": "Accrued Expenses",
        "type": "liability",
        "subtype": "current_liability",
        "parent_code": "2100",
    },
    {
        "code": "2130",
        "name": "SST Payable",
        "type": "liability",
        "subtype": "current_liability",
        "parent_code": "2100",
    },
    {
        "code": "2140",
        "name": "EPF Payable",
        "type": "liability",
        "subtype": "current_liability",
        "parent_code": "2100",
    },
    {
        "code": "2150",
        "name": "SOCSO Payable",
        "type": "liability",
        "subtype": "current_liability",
        "parent_code": "2100",
    },
    {
        "code": "2160",
        "name": "PCB Payable",
        "type": "liability",
        "subtype": "current_liability",
        "parent_code": "2100",
    },
    # Level 2 — Long-Term Liabilities
    {
        "code": "2210",
        "name": "Loans Payable",
        "type": "liability",
        "subtype": "long_term_liability",
        "parent_code": "2200",
    },
    # Level 1 — Equity
    {
        "code": "3100",
        "name": "Share Capital",
        "type": "equity",
        "subtype": "equity",
        "parent_code": "3000",
    },
    {
        "code": "3200",
        "name": "Retained Earnings",
        "type": "equity",
        "subtype": "equity",
        "parent_code": "3000",
    },
    # Level 1 — Revenue
    {
        "code": "4100",
        "name": "Sales Revenue",
        "type": "revenue",
        "subtype": "revenue",
        "parent_code": "4000",
    },
    {
        "code": "4200",
        "name": "Service Revenue",
        "type": "revenue",
        "subtype": "revenue",
        "parent_code": "4000",
    },
    # Level 1 — Cost of Sales
    {
        "code": "5100",
        "name": "Cost of Goods Sold",
        "type": "expense",
        "subtype": "cost_of_sales",
        "parent_code": "5000",
    },
    # Level 1 — Operating Expenses
    {
        "code": "6100",
        "name": "Salaries and Wages",
        "type": "expense",
        "subtype": "operating_expense",
        "parent_code": "6000",
    },
    {
        "code": "6200",
        "name": "Rent Expense",
        "type": "expense",
        "subtype": "operating_expense",
        "parent_code": "6000",
    },
    {
        "code": "6300",
        "name": "Utilities Expense",
        "type": "expense",
        "subtype": "operating_expense",
        "parent_code": "6000",
    },
    {
        "code": "6400",
        "name": "Depreciation Expense",
        "type": "expense",
        "subtype": "operating_expense",
        "parent_code": "6000",
    },
]


class Command(BaseCommand):
    help = "Seed default Chart of Accounts"

    def handle(self, *args, **options):
        code_map: dict[str, object] = {}
        created = 0
        existing = 0

        for entry in DEFAULT_ACCOUNTS:
            if Account.objects.filter(code=entry["code"]).exists():
                existing += 1
                code_map[entry["code"]] = Account.objects.get(code=entry["code"])
                continue

            parent = (
                code_map.get(entry["parent_code"]) if entry["parent_code"] else None
            )
            level = parent.level + 1 if parent else 0

            account = Account.objects.create(
                code=entry["code"],
                name=entry["name"],
                account_type=entry["type"],
                subtype=entry["subtype"],
                parent=parent,
                level=level,
                is_group=bool(entry.get("children")),
            )
            code_map[entry["code"]] = account
            created += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded {created} accounts ({existing} already existed)"
            )
        )
