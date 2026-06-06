"""Financial models — Chart of Accounts, Journal Entries."""

from django.db import models

from apps.core.mixins.models import ConcurrencyModel
from apps.core.models import Company, User

ACCOUNT_TYPES = [
    ("asset", "Asset"),
    ("liability", "Liability"),
    ("equity", "Equity"),
    ("revenue", "Revenue"),
    ("expense", "Expense"),
]

ACCOUNT_SUBTYPES = [
    ("current_asset", "Current Asset"),
    ("non_current_asset", "Non-Current Asset"),
    ("current_liability", "Current Liability"),
    ("long_term_liability", "Long-Term Liability"),
    ("equity", "Equity"),
    ("revenue", "Revenue"),
    ("cost_of_sales", "Cost of Sales"),
    ("operating_expense", "Operating Expense"),
    ("non_operating", "Non-Operating"),
]


class Account(ConcurrencyModel):
    """Chart of Accounts — global master data."""

    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=200)
    account_type = models.CharField(max_length=20, choices=ACCOUNT_TYPES)
    subtype = models.CharField(
        max_length=30, choices=ACCOUNT_SUBTYPES, blank=True, default=""
    )
    parent = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="children",
    )
    level = models.PositiveIntegerField(default=0)
    is_group = models.BooleanField(default=False, help_text="Has child accounts")
    is_active = models.BooleanField(default=True)
    mfrs_code = models.CharField(max_length=50, blank=True, default="")
    notes = models.TextField(blank=True, default="")

    class Meta:
        db_table = "financial_account"
        ordering = ["code"]
        verbose_name = "Account"
        verbose_name_plural = "Accounts"

    def __str__(self):
        return f"{self.code} — {self.name}"


class AccountCompany(ConcurrencyModel):
    """Junction table — assigns accounts to companies."""

    account = models.ForeignKey(
        Account, on_delete=models.CASCADE, related_name="company_assignments"
    )
    company = models.ForeignKey(
        "core.Company", on_delete=models.CASCADE, related_name="account_assignments"
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "financial_account_company"
        unique_together = ("account", "company")
        verbose_name = "Account Company Assignment"
        verbose_name_plural = "Account Company Assignments"

    def __str__(self):
        return f"{self.account.code} - {self.company.name}"


class JournalEntry(ConcurrencyModel):
    """General journal entry with multiple debit/credit lines."""

    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("submitted", "Submitted"),
        ("approved", "Approved"),
        ("posted", "Posted"),
        ("reversed", "Reversed"),
    ]

    entry_number = models.CharField(max_length=50, unique=True)
    date = models.DateField(db_index=True)
    description = models.TextField(blank=True, default="")
    reference = models.CharField(max_length=200, blank=True, default="")
    status = models.CharField(
        max_length=10, choices=STATUS_CHOICES, default="draft", db_index=True
    )
    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name="journal_entries"
    )
    total_debit = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    total_credit = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="journal_entries",
    )
    reversal_of = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reversals",
    )
    posted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "financial_journal_entry"
        ordering = ["-date", "-created_at"]
        verbose_name = "Journal Entry"
        verbose_name_plural = "Journal Entries"

    def __str__(self):
        return f"{self.entry_number} ({self.status})"


class JournalEntryLine(ConcurrencyModel):
    """Single line in a journal entry — one debit or credit."""

    journal_entry = models.ForeignKey(
        JournalEntry, on_delete=models.CASCADE, related_name="lines"
    )
    account = models.ForeignKey(
        Account, on_delete=models.PROTECT, related_name="journal_lines"
    )
    debit = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    credit = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    description = models.TextField(blank=True, default="")
    line_number = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "financial_journal_entry_line"
        ordering = ["line_number"]
        verbose_name = "Journal Entry Line"
        verbose_name_plural = "Journal Entry Lines"

    def __str__(self):
        return f"Line {self.line_number}: {self.account.code} DR={self.debit} CR={self.credit}"


class FinancialYear(ConcurrencyModel):
    """Financial year grouping for a company. Contains periods."""

    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name="financial_years"
    )
    name = models.CharField(max_length=100)
    start_date = models.DateField()
    end_date = models.DateField()
    is_closed = models.BooleanField(
        default=False, help_text="Year-end close completed — no further postings"
    )

    class Meta:
        db_table = "financial_year"
        ordering = ["-start_date"]
        unique_together = ("company", "name")
        verbose_name = "Financial Year"
        verbose_name_plural = "Financial Years"

    def __str__(self):
        return f"{self.name} ({self.company.code})"


class FinancialPeriod(ConcurrencyModel):
    """Accounting period for a company. Used to control posting windows."""

    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name="financial_periods"
    )
    financial_year = models.ForeignKey(
        FinancialYear,
        on_delete=models.CASCADE,
        related_name="periods",
        null=True,
        blank=True,
    )
    name = models.CharField(max_length=100)
    start_date = models.DateField()
    end_date = models.DateField()
    is_open = models.BooleanField(default=True)
    is_closed = models.BooleanField(
        default=False, help_text="Year-end close — no further postings"
    )

    class Meta:
        db_table = "financial_period"
        ordering = ["start_date"]
        unique_together = ("company", "start_date", "end_date")
        verbose_name = "Financial Period"
        verbose_name_plural = "Financial Periods"

    def __str__(self):
        return f"{self.name} ({self.company.code})"


class GeneralLedger(models.Model):
    """Immutable GL entry created when a journal entry is posted."""

    journal_entry = models.ForeignKey(
        JournalEntry, on_delete=models.CASCADE, related_name="gl_entries"
    )
    journal_entry_line = models.ForeignKey(
        JournalEntryLine, on_delete=models.CASCADE, related_name="gl_entries"
    )
    account = models.ForeignKey(
        Account, on_delete=models.PROTECT, related_name="gl_entries"
    )
    date = models.DateField(db_index=True)
    debit = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    credit = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    balance = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name="gl_entries"
    )
    period = models.ForeignKey(
        FinancialPeriod,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="gl_entries",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "financial_general_ledger"
        ordering = ["date", "created_at"]
        verbose_name = "General Ledger Entry"
        verbose_name_plural = "General Ledger Entries"
        indexes = [
            models.Index(fields=["account", "date"]),
            models.Index(fields=["company", "date"]),
            models.Index(fields=["period"]),
        ]

    def __str__(self):
        return f"GL: {self.account.code} DR={self.debit} CR={self.credit}"


class TaxCode(ConcurrencyModel):
    """Tax code definition — global master data."""

    TAX_TYPES = [
        ("sales", "Sales Tax"),
        ("service", "Service Tax"),
        ("exempt", "Exempt"),
        ("zero_rated", "Zero-Rated"),
        ("out_of_scope", "Out of Scope"),
        ("purchase", "Purchase / Input Tax"),
    ]

    code = models.CharField(max_length=10, unique=True)
    name = models.CharField(max_length=200)
    rate_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    tax_type = models.CharField(max_length=20, choices=TAX_TYPES)
    is_active = models.BooleanField(default=True)
    description = models.TextField(blank=True, default="")

    class Meta:
        db_table = "financial_tax_code"
        ordering = ["code"]
        verbose_name = "Tax Code"
        verbose_name_plural = "Tax Codes"

    def __str__(self):
        return f"{self.code} ({self.rate_percent}%)"


class TaxRate(ConcurrencyModel):
    """Tax rate with effective dating for rate changes."""

    tax_code = models.ForeignKey(
        TaxCode, on_delete=models.CASCADE, related_name="rates"
    )
    rate_percent = models.DecimalField(max_digits=5, decimal_places=2)
    effective_from = models.DateField()
    effective_to = models.DateField(null=True, blank=True)
    is_current = models.BooleanField(default=True)

    class Meta:
        db_table = "financial_tax_rate"
        ordering = ["-effective_from"]
        verbose_name = "Tax Rate"
        verbose_name_plural = "Tax Rates"

    def __str__(self):
        return f"{self.tax_code.code} @ {self.rate_percent}% from {self.effective_from}"


class AccountPeriodBalance(ConcurrencyModel):
    """Pre-aggregated period balance for each account-company-period."""

    account = models.ForeignKey(
        Account, on_delete=models.CASCADE, related_name="period_balances"
    )
    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name="period_balances"
    )
    period = models.ForeignKey(
        FinancialPeriod, on_delete=models.CASCADE, related_name="account_balances"
    )
    opening_debit = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    opening_credit = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    period_debit = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    period_credit = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    closing_debit = models.DecimalField(max_digits=18, decimal_places=2, default=0)
    closing_credit = models.DecimalField(max_digits=18, decimal_places=2, default=0)

    class Meta:
        db_table = "financial_accountperiodbalance"
        unique_together = ("account", "company", "period")
        verbose_name = "Account Period Balance"
        verbose_name_plural = "Account Period Balances"

    def __str__(self):
        return f"{self.account.code} - {self.period.name}"


REPORT_PARAM_TYPES = [
    ("period", "Period (single)"),
    ("period_range", "Period Range"),
    ("account_tree", "Account Tree (hierarchical)"),
    ("account_multi", "Account Multi-Select"),
    ("customer_multi", "Customer Multi-Select"),
    ("vendor_multi", "Vendor Multi-Select"),
    ("date", "Date"),
    ("date_range", "Date Range"),
    ("checkbox", "Checkbox"),
    ("select", "Dropdown Select"),
    ("text", "Text Input"),
]


class ReportDefinition(ConcurrencyModel):
    """Report definition — metadata for computed reports."""

    code = models.SlugField(unique=True)
    name = models.CharField(max_length=200)
    module = models.CharField(max_length=50)
    category = models.CharField(max_length=50, blank=True, default="")
    company_scoped = models.BooleanField(default=True)
    compute_type = models.CharField(
        max_length=20, choices=[("sql", "SQL"), ("python", "Python Service")]
    )
    sql_template = models.TextField(blank=True)
    service_method = models.CharField(max_length=300, blank=True, default="")
    pre_aggregated = models.BooleanField(default=False)
    supports_drill_down = models.BooleanField(default=False)
    group_field = models.CharField(max_length=100, blank=True, default="")
    show_subtotals = models.BooleanField(default=True)
    show_grand_total = models.BooleanField(default=True)
    page_size = models.PositiveIntegerField(default=100)
    cache_ttl_seconds = models.PositiveIntegerField(default=300)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "financial_report_definition"
        verbose_name = "Report Definition"
        verbose_name_plural = "Report Definitions"

    def __str__(self):
        return self.name


class ReportParameter(ConcurrencyModel):
    """Parameter definition for a report — drives filter form rendering."""

    report = models.ForeignKey(
        ReportDefinition, on_delete=models.CASCADE, related_name="parameters"
    )
    key = models.SlugField()
    label = models.CharField(max_length=200)
    param_type = models.CharField(max_length=30, choices=REPORT_PARAM_TYPES)
    required = models.BooleanField(default=False)
    default_value = models.JSONField(null=True, blank=True)
    options_source = models.CharField(max_length=300, blank=True, default="")
    validation = models.JSONField(default=dict, blank=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "financial_report_parameter"
        ordering = ["sort_order"]
        unique_together = ("report", "key")
        verbose_name = "Report Parameter"
        verbose_name_plural = "Report Parameters"

    def __str__(self):
        return f"{self.report.code}:{self.key}"


class ReportExport(ConcurrencyModel):
    """Tracks an async report export (CSV/PDF/Excel)."""

    FORMAT_CHOICES = [
        ("csv", "CSV"),
        ("pdf", "PDF"),
        ("xlsx", "Excel"),
    ]
    STATUS_CHOICES = [
        ("generating", "Generating"),
        ("ready", "Ready"),
        ("failed", "Failed"),
    ]

    report = models.ForeignKey(
        ReportDefinition, on_delete=models.CASCADE, related_name="exports"
    )
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="report_exports"
    )
    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name="report_exports"
    )
    format = models.CharField(max_length=10, choices=FORMAT_CHOICES)
    params = models.JSONField(default=dict)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="generating"
    )
    file = models.FileField(upload_to="report_exports/%Y/%m/", blank=True)
    error_message = models.TextField(blank=True, default="")
    generated_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "financial_report_export"
        verbose_name = "Report Export"
        verbose_name_plural = "Report Exports"

    def __str__(self):
        return f"{self.report.code} - {self.format} - {self.status}"
