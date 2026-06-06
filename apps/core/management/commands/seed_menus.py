"""Seed the menu tree with all ERP module navigation items."""

from django.core.management.base import BaseCommand

from apps.core.models import Menu

MENU_TREE = [
    {
        "name": "Dashboard",
        "slug": "dashboard",
        "icon": "LayoutDashboard",
        "url": "/app/dashboard",
        "sort_order": 1,
        "module": "core",
        "children": [],
    },
    {
        "name": "Messaging",
        "slug": "messaging",
        "icon": "MessageSquare",
        "url": "/app/messaging",
        "sort_order": 2,
        "module": "core",
        "children": [],
    },
    {
        "name": "Financial",
        "slug": "financial",
        "icon": "DollarSign",
        "url": "",
        "sort_order": 10,
        "module": "financial",
        "children": [
            {
                "name": "Chart of Accounts",
                "slug": "financial-coa",
                "icon": "BookOpen",
                "url": "/app/financial/accounts",
                "sort_order": 1,
                "module": "financial",
            },
            {
                "name": "General Ledger",
                "slug": "financial-gl",
                "icon": "FileText",
                "url": "",
                "sort_order": 2,
                "module": "financial",
                "children": [
                    {
                        "name": "Journal Entries",
                        "slug": "financial-gl-journal",
                        "icon": "ScrollText",
                        "url": "/app/financial/journal-entries",
                        "sort_order": 1,
                        "module": "financial",
                    },
                ],
            },
            {
                "name": "Accounts Payable",
                "slug": "financial-ap",
                "icon": "CreditCard",
                "url": "",
                "sort_order": 3,
                "module": "financial",
                "children": [
                    {
                        "name": "Supplier Invoices",
                        "slug": "financial-ap-invoices",
                        "icon": "FileText",
                        "url": "/app/financial/ap/invoices",
                        "sort_order": 1,
                        "module": "financial",
                    },
                    {
                        "name": "Payment Runs",
                        "slug": "financial-ap-payments",
                        "icon": "Banknote",
                        "url": "/app/financial/ap/payments",
                        "sort_order": 2,
                        "module": "financial",
                    },
                ],
            },
            {
                "name": "Accounts Receivable",
                "slug": "financial-ar",
                "icon": "Wallet",
                "url": "",
                "sort_order": 4,
                "module": "financial",
                "children": [
                    {
                        "name": "Customer Invoices",
                        "slug": "financial-ar-invoices",
                        "icon": "FileText",
                        "url": "/app/financial/ar/invoices",
                        "sort_order": 1,
                        "module": "financial",
                    },
                    {
                        "name": "Credit Notes",
                        "slug": "financial-ar-credit-notes",
                        "icon": "FileMinus",
                        "url": "/app/financial/ar/credit-notes",
                        "sort_order": 2,
                        "module": "financial",
                    },
                ],
            },
            {
                "name": "Bank Reconciliation",
                "slug": "financial-bank-recon",
                "icon": "CheckCircle",
                "url": "/app/financial/bank-reconciliation",
                "sort_order": 5,
                "module": "financial",
            },
            {
                "name": "Tax / SST",
                "slug": "financial-tax",
                "icon": "Percent",
                "url": "/app/financial/tax-codes",
                "sort_order": 6,
                "module": "financial",
            },
            {
                "name": "Periods",
                "slug": "financial-periods",
                "icon": "Calendar",
                "url": "/app/financial/periods",
                "sort_order": 7,
                "module": "financial",
            },
            {
                "name": "Reports",
                "slug": "financial-reports",
                "icon": "BarChart3",
                "url": "",
                "sort_order": 8,
                "module": "financial",
                "children": [
                    {
                        "name": "Profit & Loss",
                        "slug": "financial-reports-pnl",
                        "icon": "TrendingUp",
                        "url": "/app/financial/reports/pnl",
                        "sort_order": 1,
                        "module": "financial",
                    },
                    {
                        "name": "Balance Sheet",
                        "slug": "financial-reports-bs",
                        "icon": "Balance",
                        "url": "/app/financial/reports/balance-sheet",
                        "sort_order": 2,
                        "module": "financial",
                    },
                    {
                        "name": "Cash Flow Statement",
                        "slug": "financial-reports-cf",
                        "icon": "ArrowLeftRight",
                        "url": "/app/financial/reports/cash-flow",
                        "sort_order": 3,
                        "module": "financial",
                    },
                    {
                        "name": "Trial Balance",
                        "slug": "trial-balance",
                        "icon": "FileText",
                        "url": "/app/financial/reports/trial-balance",
                        "sort_order": 4,
                        "module": "financial",
                    },
                ],
            },
        ],
    },
    {
        "name": "Fixed Assets",
        "slug": "assets",
        "icon": "Landmark",
        "url": "",
        "sort_order": 20,
        "module": "assets",
        "children": [
            {
                "name": "Asset Register",
                "slug": "assets-register",
                "icon": "ClipboardList",
                "url": "/app/assets/register",
                "sort_order": 1,
                "module": "assets",
            },
            {
                "name": "Depreciation",
                "slug": "assets-depreciation",
                "icon": "TrendingDown",
                "url": "/app/assets/depreciation",
                "sort_order": 2,
                "module": "assets",
            },
            {
                "name": "Capital Allowance",
                "slug": "assets-capital-allowance",
                "icon": "Calculator",
                "url": "/app/assets/capital-allowance",
                "sort_order": 3,
                "module": "assets",
            },
        ],
    },
    {
        "name": "Treasury",
        "slug": "treasury",
        "icon": "PiggyBank",
        "url": "",
        "sort_order": 25,
        "module": "treasury",
        "children": [
            {
                "name": "Cash Management",
                "slug": "treasury-cash",
                "icon": "Cash",
                "url": "/app/treasury/cash",
                "sort_order": 1,
                "module": "treasury",
            },
            {
                "name": "Bank Accounts",
                "slug": "treasury-banks",
                "icon": "Building2",
                "url": "/app/treasury/banks",
                "sort_order": 2,
                "module": "treasury",
            },
            {
                "name": "Cash Flow Forecast",
                "slug": "treasury-cashflow",
                "icon": "LineChart",
                "url": "/app/treasury/cash-flow-forecast",
                "sort_order": 3,
                "module": "treasury",
            },
        ],
    },
    {
        "name": "Supply Chain",
        "slug": "scm",
        "icon": "Package",
        "url": "",
        "sort_order": 30,
        "module": "scm",
        "children": [
            {
                "name": "Items",
                "slug": "scm-items",
                "icon": "Box",
                "url": "/app/scm/items",
                "sort_order": 1,
                "module": "scm",
            },
            {
                "name": "Inventory",
                "slug": "scm-inventory",
                "icon": "Warehouse",
                "url": "/app/scm/inventory",
                "sort_order": 2,
                "module": "scm",
            },
            {
                "name": "Purchasing",
                "slug": "scm-purchasing",
                "icon": "ShoppingCart",
                "url": "",
                "sort_order": 3,
                "module": "scm",
                "children": [
                    {
                        "name": "Purchase Requisitions",
                        "slug": "scm-purchasing-pr",
                        "icon": "FileInput",
                        "url": "/app/scm/purchasing/pr",
                        "sort_order": 1,
                        "module": "scm",
                    },
                    {
                        "name": "Request for Quotation",
                        "slug": "scm-purchasing-rfq",
                        "icon": "Mail",
                        "url": "/app/scm/purchasing/rfq",
                        "sort_order": 2,
                        "module": "scm",
                    },
                    {
                        "name": "Purchase Orders",
                        "slug": "scm-purchasing-po",
                        "icon": "FileText",
                        "url": "/app/scm/purchasing/po",
                        "sort_order": 3,
                        "module": "scm",
                    },
                ],
            },
            {
                "name": "Goods Receiving",
                "slug": "scm-grn",
                "icon": "Truck",
                "url": "/app/scm/grn",
                "sort_order": 4,
                "module": "scm",
            },
            {
                "name": "Warehouse",
                "slug": "scm-warehouse",
                "icon": "Home",
                "url": "/app/scm/warehouse",
                "sort_order": 5,
                "module": "scm",
            },
        ],
    },
    {
        "name": "CRM",
        "slug": "crm",
        "icon": "Users",
        "url": "",
        "sort_order": 40,
        "module": "crm",
        "children": [
            {
                "name": "Leads",
                "slug": "crm-leads",
                "icon": "UserPlus",
                "url": "/app/crm/leads",
                "sort_order": 1,
                "module": "crm",
            },
            {
                "name": "Opportunities",
                "slug": "crm-opportunities",
                "icon": "Target",
                "url": "/app/crm/opportunities",
                "sort_order": 2,
                "module": "crm",
            },
            {
                "name": "Customers",
                "slug": "crm-customers",
                "icon": "Users",
                "url": "/app/crm/customers",
                "sort_order": 3,
                "module": "crm",
            },
            {
                "name": "Sales Quotations",
                "slug": "crm-quotations",
                "icon": "FileText",
                "url": "/app/crm/quotations",
                "sort_order": 4,
                "module": "crm",
            },
            {
                "name": "Sales Orders",
                "slug": "crm-sales-orders",
                "icon": "ShoppingBag",
                "url": "/app/crm/sales-orders",
                "sort_order": 5,
                "module": "crm",
            },
            {
                "name": "Delivery Orders",
                "slug": "crm-delivery-orders",
                "icon": "Truck",
                "url": "/app/crm/delivery-orders",
                "sort_order": 6,
                "module": "crm",
            },
        ],
    },
    {
        "name": "MRP",
        "slug": "mrp",
        "icon": "Factory",
        "url": "",
        "sort_order": 50,
        "module": "mrp",
        "children": [
            {
                "name": "Bill of Materials",
                "slug": "mrp-bom",
                "icon": "Layers",
                "url": "/app/mrp/bom",
                "sort_order": 1,
                "module": "mrp",
            },
            {
                "name": "Work Centers",
                "slug": "mrp-work-centers",
                "icon": "Cog",
                "url": "/app/mrp/work-centers",
                "sort_order": 2,
                "module": "mrp",
            },
            {
                "name": "Routings",
                "slug": "mrp-routings",
                "icon": "Route",
                "url": "/app/mrp/routings",
                "sort_order": 3,
                "module": "mrp",
            },
            {
                "name": "Production Planning",
                "slug": "mrp-production",
                "icon": "Calendar",
                "url": "/app/mrp/production",
                "sort_order": 4,
                "module": "mrp",
            },
            {
                "name": "Work Orders",
                "slug": "mrp-work-orders",
                "icon": "ClipboardCheck",
                "url": "/app/mrp/work-orders",
                "sort_order": 5,
                "module": "mrp",
            },
            {
                "name": "Quality Control",
                "slug": "mrp-qc",
                "icon": "ShieldCheck",
                "url": "/app/mrp/quality-control",
                "sort_order": 6,
                "module": "mrp",
            },
        ],
    },
    {
        "name": "HRM",
        "slug": "hrm",
        "icon": "UserCog",
        "url": "",
        "sort_order": 60,
        "module": "hrm",
        "children": [
            {
                "name": "Employees",
                "slug": "hrm-employees",
                "icon": "Users",
                "url": "/app/hrm/employees",
                "sort_order": 1,
                "module": "hrm",
            },
            {
                "name": "Organization",
                "slug": "hrm-org",
                "icon": "Network",
                "url": "/app/hrm/organization",
                "sort_order": 2,
                "module": "hrm",
            },
            {
                "name": "Attendance",
                "slug": "hrm-attendance",
                "icon": "Clock",
                "url": "/app/hrm/attendance",
                "sort_order": 3,
                "module": "hrm",
            },
            {
                "name": "Leave",
                "slug": "hrm-leave",
                "icon": "CalendarOff",
                "url": "/app/hrm/leave",
                "sort_order": 4,
                "module": "hrm",
            },
            {
                "name": "Payroll",
                "slug": "hrm-payroll",
                "icon": "Banknote",
                "url": "/app/hrm/payroll",
                "sort_order": 5,
                "module": "hrm",
            },
            {
                "name": "Claims",
                "slug": "hrm-claims",
                "icon": "Receipt",
                "url": "/app/hrm/claims",
                "sort_order": 6,
                "module": "hrm",
            },
            {
                "name": "Recruitment",
                "slug": "hrm-recruitment",
                "icon": "UserPlus",
                "url": "/app/hrm/recruitment",
                "sort_order": 7,
                "module": "hrm",
            },
            {
                "name": "Performance",
                "slug": "hrm-performance",
                "icon": "Award",
                "url": "/app/hrm/performance",
                "sort_order": 8,
                "module": "hrm",
            },
        ],
    },
    {
        "name": "Administration",
        "slug": "admin",
        "icon": "Settings",
        "url": "",
        "sort_order": 90,
        "module": "admin",
        "children": [
            {
                "name": "Users",
                "slug": "admin-users",
                "icon": "Users",
                "url": "/app/admin/users",
                "sort_order": 1,
                "module": "admin",
            },
            {
                "name": "Roles & Permissions",
                "slug": "admin-roles",
                "icon": "Shield",
                "url": "/app/admin/roles",
                "sort_order": 2,
                "module": "admin",
            },
            {
                "name": "Menu Access",
                "slug": "admin-menu-access",
                "icon": "Menu",
                "url": "/app/admin/menu-access",
                "sort_order": 3,
                "module": "admin",
            },
            {
                "name": "Audit Log",
                "slug": "admin-audit-log",
                "icon": "ClipboardList",
                "url": "/app/admin/audit-logs",
                "sort_order": 4,
                "module": "admin",
            },
            {
                "name": "Opening Balance",
                "slug": "admin-opening-balance",
                "icon": "Database",
                "url": "/app/admin/opening-balance",
                "sort_order": 5,
                "module": "admin",
            },
            {
                "name": "Data Import",
                "slug": "admin-data-import",
                "icon": "Upload",
                "url": "/app/admin/import",
                "sort_order": 6,
                "module": "admin",
            },
            {
                "name": "Field Customizer",
                "slug": "admin-field-customizer",
                "icon": "Pencil",
                "url": "/app/admin/field-customizer",
                "sort_order": 6,
                "module": "admin",
            },
            {
                "name": "Workflow Designer",
                "slug": "admin-workflow-designer",
                "icon": "GitBranch",
                "url": "/app/workflows/designer",
                "sort_order": 6,
                "module": "admin",
            },
            {
                "name": "Approvals Center",
                "slug": "admin-approvals",
                "icon": "CheckSquare",
                "url": "/app/approvals",
                "sort_order": 6,
                "module": "admin",
            },
            {
                "name": "Numbering Series",
                "slug": "admin-numbering",
                "icon": "Hash",
                "url": "/app/admin/numbering-series",
                "sort_order": 7,
                "module": "admin",
            },
            {
                "name": "Notifications",
                "slug": "admin-notifications",
                "icon": "Bell",
                "url": "/app/admin/notifications",
                "sort_order": 8,
                "module": "admin",
            },
            {
                "name": "Settings",
                "slug": "admin-settings",
                "icon": "Settings",
                "url": "/app/admin/settings",
                "sort_order": 9,
                "module": "admin",
            },
        ],
    },
]


class Command(BaseCommand):
    help = "Seed the menu tree with all ERP module navigation items"

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Clear all existing menus before seeding",
        )

    def handle(self, *args, **options):
        if options["clear"]:
            Menu.objects.all().delete()
            self.stdout.write(self.style.WARNING("Cleared all menu items."))

        created_count = 0
        updated_count = 0

        for item in MENU_TREE:
            created = self._create_menu_item(item, parent=None)
            if created:
                created_count += 1
            else:
                updated_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Done! Created: {created_count}, Updated: {updated_count}"
            )
        )

    def _create_menu_item(self, item, parent):
        """Create or update a single menu item and its children."""
        children_data = item.pop("children", [])

        obj, created = Menu.objects.update_or_create(
            slug=item["slug"],
            defaults={
                "name": item["name"],
                "icon": item.get("icon", ""),
                "url": item.get("url", ""),
                "parent": parent,
                "sort_order": item.get("sort_order", 0),
                "module": item.get("module", ""),
                "level": 0 if parent is None else parent.level + 1,
                "is_active": True,
            },
        )

        status = "CREATED" if created else "UPDATED"
        self.stdout.write(f"  {status}: {obj.name} (/{obj.slug})")

        for child_data in children_data:
            self._create_menu_item(child_data, parent=obj)

        # Restore children key for parent loop
        item["children"] = children_data
        return created
