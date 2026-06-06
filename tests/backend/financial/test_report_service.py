"""Tests for ReportService — SQL execution, cache, pagination, drill-down."""

from datetime import date

import pytest
from django.core.cache import cache

from apps.core.models import Company
from apps.financial.models import (
    Account,
    FinancialPeriod,
    ReportDefinition,
    ReportParameter,
)
from apps.financial.services.journal_service import create_journal_entry
from apps.financial.services.posting_service import post_journal_entry
from apps.financial.services.report_service import ReportService, ReportServiceError


@pytest.fixture
def company(db):
    return Company.objects.create(name="Test Co", code="TC")


@pytest.fixture
def period(db, company):
    return FinancialPeriod.objects.create(
        company=company,
        name="June 2026",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 6, 30),
        is_open=True,
    )


@pytest.fixture
def period2(db, company):
    return FinancialPeriod.objects.create(
        company=company,
        name="July 2026",
        start_date=date(2026, 7, 1),
        end_date=date(2026, 7, 31),
        is_open=True,
    )


@pytest.fixture
def asset_account(db):
    return Account.objects.create(
        code="1110", name="Cash", account_type="asset", is_active=True
    )


@pytest.fixture
def revenue_account(db):
    return Account.objects.create(
        code="4100", name="Revenue", account_type="revenue", is_active=True
    )


@pytest.fixture
def report_def(db):
    report, _ = ReportDefinition.objects.get_or_create(
        code="trial_balance",
        defaults={
            "name": "Trial Balance",
            "module": "financial",
            "compute_type": "sql",
            "sql_template": """
                SELECT a.code, a.name, a.account_type,
                       ab.opening_debit, ab.opening_credit,
                       ab.period_debit, ab.period_credit,
                       ab.closing_debit, ab.closing_credit
                FROM financial_accountperiodbalance ab
                JOIN financial_account a ON a.id = ab.account_id
                WHERE ab.company_id = %(company_id)s
                  AND ab.period_id BETWEEN %(period_from)s AND %(period_to)s
                ORDER BY a.code
            """,
            "pre_aggregated": True,
            "supports_drill_down": True,
            "group_field": "account_type",
            "show_subtotals": True,
            "show_grand_total": True,
        },
    )
    ReportParameter.objects.get_or_create(
        report=report,
        key="period_from",
        defaults={
            "label": "Period From",
            "param_type": "period",
            "required": True,
            "sort_order": 1,
        },
    )
    ReportParameter.objects.get_or_create(
        report=report,
        key="period_to",
        defaults={
            "label": "Period To",
            "param_type": "period",
            "required": True,
            "sort_order": 2,
        },
    )
    return report


@pytest.fixture
def numbering(db, company):
    from apps.core.models import CompanyNumberingSeries, NumberingSeriesPolicy

    policy, _ = NumberingSeriesPolicy.objects.get_or_create(
        document_type="journal_entry",
        defaults={"prefix": "JE-", "date_format": "YYYYMM", "padding": 6},
    )
    CompanyNumberingSeries.objects.get_or_create(
        policy=policy,
        company=company,
        defaults={"reset_period": "yearly", "next_number": 1},
    )
    return policy


@pytest.mark.django_db
class TestReportService:
    def _post_test_entry(
        self, company, asset_account, revenue_account, period, numbering, amount=1000
    ):
        entry = create_journal_entry(
            date=period.start_date,
            description="Test",
            lines=[
                {"account_id": asset_account.id, "debit": amount, "credit": 0},
                {"account_id": revenue_account.id, "debit": 0, "credit": amount},
            ],
            company_id=company.id,
        )
        post_journal_entry(entry.id)

    def test_sql_execution_returns_data(
        self, company, period, asset_account, revenue_account, report_def, numbering
    ):
        self._post_test_entry(
            company, asset_account, revenue_account, period, numbering
        )

        svc = ReportService()
        result = svc.run(
            "trial_balance",
            {"period_from": str(period.id), "period_to": str(period.id)},
            company.id,
        )
        assert result["total_rows"] == 2
        assert len(result["columns"]) == 9
        assert result["summary"] is not None

    def test_param_validation_required_missing(self, report_def, company):
        svc = ReportService()
        with pytest.raises(
            ReportServiceError, match="Required parameter 'period_from' is missing"
        ):
            svc.run("trial_balance", {"period_to": "some-uuid"}, company.id)

    def test_pagination(
        self, company, period, asset_account, revenue_account, report_def, numbering
    ):
        self._post_test_entry(
            company, asset_account, revenue_account, period, numbering, amount=500
        )

        svc = ReportService()
        result = svc.run(
            "trial_balance",
            {
                "period_from": str(period.id),
                "period_to": str(period.id),
                "page": 1,
                "page_size": 1,
            },
            company.id,
        )
        assert len(result["rows"]) == 1
        assert result["page"] == 1
        assert result["total_rows"] == 2

    def test_cache_hit(
        self, company, period, asset_account, revenue_account, report_def, numbering
    ):
        self._post_test_entry(
            company, asset_account, revenue_account, period, numbering
        )

        svc = ReportService()
        result1 = svc.run(
            "trial_balance",
            {"period_from": str(period.id), "period_to": str(period.id)},
            company.id,
        )

        result2 = svc.run(
            "trial_balance",
            {"period_from": str(period.id), "period_to": str(period.id)},
            company.id,
        )
        assert result1["generated_at"] == result2["generated_at"]

        cache.clear()

    def test_drill_down_returns_gl_entries(
        self, company, period, asset_account, revenue_account, report_def, numbering
    ):
        self._post_test_entry(
            company, asset_account, revenue_account, period, numbering
        )

        svc = ReportService()
        entries = svc.drill_down(
            "trial_balance",
            row_id="",
            params={"account_id": str(asset_account.id), "period_id": str(period.id)},
            company_id=company.id,
        )
        assert len(entries) == 1
        assert float(entries[0]["debit"]) == 1000

    def test_drill_down_no_data_returns_empty(
        self, company, period, asset_account, revenue_account, report_def, numbering
    ):
        svc = ReportService()
        entries = svc.drill_down(
            "trial_balance",
            row_id="",
            params={"account_id": str(asset_account.id), "period_id": str(period.id)},
            company_id=company.id,
        )
        assert entries == []

    def test_group_totals(
        self, company, period, asset_account, revenue_account, report_def, numbering
    ):
        self._post_test_entry(
            company, asset_account, revenue_account, period, numbering
        )

        svc = ReportService()
        result = svc.run(
            "trial_balance",
            {"period_from": str(period.id), "period_to": str(period.id)},
            company.id,
        )
        assert result["group_totals"] is not None
        group_labels = [g["group"] for g in result["group_totals"]]
        assert "asset" in group_labels
        assert "revenue" in group_labels
