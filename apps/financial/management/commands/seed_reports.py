"""Seed report definitions and parameters."""

from django.core.management.base import BaseCommand

from apps.financial.models import ReportDefinition, ReportParameter

TRIAL_BALANCE_SQL = """
SELECT a.code, a.name, a.account_type,
       ab.opening_debit, ab.opening_credit,
       ab.period_debit, ab.period_credit,
       ab.closing_debit, ab.closing_credit
FROM financial_accountperiodbalance ab
JOIN financial_account a ON a.id = ab.account_id
WHERE ab.company_id = %(company_id)s
  AND ab.period_id BETWEEN %(period_from)s AND %(period_to)s
  AND (ab.opening_debit != 0 OR ab.opening_credit != 0
       OR ab.period_debit != 0 OR ab.period_credit != 0
       OR ab.closing_debit != 0 OR ab.closing_credit != 0)
ORDER BY a.code
"""


class Command(BaseCommand):
    help = "Seed report definitions and parameters"

    def handle(self, *args, **options):
        self._seed_trial_balance()
        self.stdout.write(self.style.SUCCESS("Reports seeded successfully"))

    def _seed_trial_balance(self):
        report, _ = ReportDefinition.objects.update_or_create(
            code="trial_balance",
            defaults={
                "name": "Trial Balance",
                "module": "financial",
                "category": "financial_statements",
                "compute_type": "sql",
                "sql_template": TRIAL_BALANCE_SQL,
                "pre_aggregated": True,
                "supports_drill_down": True,
                "group_field": "account_type",
                "show_subtotals": True,
                "show_grand_total": True,
                "page_size": 500,
                "cache_ttl_seconds": 300,
                "is_active": True,
            },
        )

        params = [
            {
                "key": "period_from",
                "label": "Period From",
                "param_type": "period",
                "required": True,
                "sort_order": 1,
            },
            {
                "key": "period_to",
                "label": "Period To",
                "param_type": "period",
                "required": True,
                "sort_order": 2,
            },
            {
                "key": "show_zero_balances",
                "label": "Show Zero Balances",
                "param_type": "checkbox",
                "required": False,
                "default_value": False,
                "sort_order": 3,
            },
        ]

        for param_data in params:
            ReportParameter.objects.update_or_create(
                report=report,
                key=param_data["key"],
                defaults=param_data,
            )
