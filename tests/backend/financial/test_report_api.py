"""Tests for report API endpoints."""

import uuid
from datetime import date

import pytest
from rest_framework_simplejwt.tokens import AccessToken

from apps.core.models import Company
from apps.financial.models import (
    Account,
    FinancialPeriod,
    ReportDefinition,
    ReportParameter,
)
from apps.financial.services.journal_service import create_journal_entry
from apps.financial.services.posting_service import post_journal_entry


@pytest.fixture
def admin_user(db):
    from django.contrib.auth import get_user_model

    User = get_user_model()
    return User.objects.create_superuser(email="admin@test.com", password="admin123")


@pytest.fixture
def company(db):
    return Company.objects.create(name="Test Co", code="TC")


@pytest.fixture
def other_company(db):
    return Company.objects.create(name="Other Co", code="OC")


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
                  AND (ab.opening_debit != 0 OR ab.opening_credit != 0
                       OR ab.period_debit != 0 OR ab.period_credit != 0)
                ORDER BY a.code
            """,
            "pre_aggregated": True,
            "supports_drill_down": True,
            "group_field": "account_type",
            "show_subtotals": True,
            "show_grand_total": True,
        },
    )
    ReportParameter.objects.update_or_create(
        report=report,
        key="period_from",
        defaults={
            "label": "Period From",
            "param_type": "period",
            "required": True,
            "sort_order": 1,
        },
    )
    ReportParameter.objects.update_or_create(
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


def headers(user, company):
    token = AccessToken.for_user(user)
    return {
        "HTTP_AUTHORIZATION": f"Bearer {token}",
        "HTTP_X_COMPANY_ID": str(company.id),
    }


@pytest.mark.django_db
class TestReportAPI:
    def test_list_reports(self, client, admin_user, company, report_def):
        response = client.get(
            "/api/v1/financial/reports/", **headers(admin_user, company)
        )
        assert response.status_code == 200
        data = response.json()
        codes = [r["code"] for r in data]
        assert "trial_balance" in codes

    def test_list_reports_filter_by_module(
        self, client, admin_user, company, report_def
    ):
        response = client.get(
            "/api/v1/financial/reports/?module=financial",
            **headers(admin_user, company),
        )
        assert response.status_code == 200
        data = response.json()
        for r in data:
            assert r["module"] == "financial"

    def test_get_parameters(self, client, admin_user, company, report_def):
        response = client.get(
            "/api/v1/financial/reports/trial_balance/parameters/",
            **headers(admin_user, company),
        )
        assert response.status_code == 200
        data = response.json()
        keys = [p["key"] for p in data]
        assert "period_from" in keys
        assert "period_to" in keys

    def test_get_parameters_not_found(self, client, admin_user, company):
        response = client.get(
            "/api/v1/financial/reports/nonexistent/parameters/",
            **headers(admin_user, company),
        )
        assert response.status_code == 404

    def test_run_report_missing_required_param(
        self, client, admin_user, company, report_def
    ):
        response = client.get(
            "/api/v1/financial/reports/trial_balance/",
            {"period_to": str(uuid.uuid4())},
            **headers(admin_user, company),
        )
        assert response.status_code == 400

    def test_run_report_with_valid_params(
        self,
        client,
        admin_user,
        company,
        period,
        report_def,
        asset_account,
        revenue_account,
        numbering,
    ):
        # Post some data
        entry = create_journal_entry(
            date=period.start_date,
            description="Test",
            lines=[
                {"account_id": asset_account.id, "debit": 1000, "credit": 0},
                {"account_id": revenue_account.id, "debit": 0, "credit": 1000},
            ],
            company_id=company.id,
        )
        post_journal_entry(entry.id)

        response = client.get(
            "/api/v1/financial/reports/trial_balance/",
            {"period_from": str(period.id), "period_to": str(period.id)},
            **headers(admin_user, company),
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total_rows"] == 2
        assert data["summary"] is not None

    def test_drill_down(
        self,
        client,
        admin_user,
        company,
        period,
        report_def,
        asset_account,
        revenue_account,
        numbering,
    ):
        entry = create_journal_entry(
            date=period.start_date,
            description="Test",
            lines=[
                {"account_id": asset_account.id, "debit": 1000, "credit": 0},
                {"account_id": revenue_account.id, "debit": 0, "credit": 1000},
            ],
            company_id=company.id,
        )
        post_journal_entry(entry.id)

        response = client.get(
            "/api/v1/financial/reports/trial_balance/drill-down/",
            {
                "account_id": str(asset_account.id),
                "period_id": str(period.id),
            },
            **headers(admin_user, company),
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) == 1
        assert float(data["results"][0]["debit"]) == 1000

    def test_export_creates_report_export(
        self, client, admin_user, company, report_def, period
    ):
        response = client.post(
            "/api/v1/financial/reports/trial_balance/export/",
            {
                "format": "csv",
                "params": {"period_from": str(period.id), "period_to": str(period.id)},
            },
            content_type="application/json",
            **headers(admin_user, company),
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] in ("ready", "generating")
        assert data["export_id"] is not None

    def test_export_status_poll(self, client, admin_user, company, report_def, period):
        # Create export
        response = client.post(
            "/api/v1/financial/reports/trial_balance/export/",
            {
                "format": "csv",
                "params": {"period_from": str(period.id), "period_to": str(period.id)},
            },
            content_type="application/json",
            **headers(admin_user, company),
        )
        export_id = response.json()["export_id"]

        # Poll status
        response = client.get(
            f"/api/v1/financial/exports/{export_id}/",
            **headers(admin_user, company),
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == export_id

    def test_company_scoping(
        self, client, admin_user, company, other_company, report_def, period
    ):
        # Create export in company
        response = client.post(
            "/api/v1/financial/reports/trial_balance/export/",
            {
                "format": "csv",
                "params": {"period_from": str(period.id), "period_to": str(period.id)},
            },
            content_type="application/json",
            **headers(admin_user, company),
        )
        export_id = response.json()["export_id"]

        # Try to access from other company
        response = client.get(
            f"/api/v1/financial/exports/{export_id}/",
            **headers(admin_user, other_company),
        )
        assert response.status_code == 404

    def test_unauthorized_returns_401(self, client):
        response = client.get("/api/v1/financial/reports/")
        assert response.status_code == 401
