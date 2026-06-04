"""Financial models — Chart of Accounts."""

from django.db import models

from apps.core.mixins.models import ConcurrencyModel

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
