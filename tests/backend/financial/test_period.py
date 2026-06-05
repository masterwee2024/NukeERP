"""Tests for Period Management (T024)."""

from datetime import date

import pytest
from rest_framework_simplejwt.tokens import AccessToken

from apps.core.models import (
    Company,
    CompanyNumberingSeries,
    NumberingSeriesPolicy,
    User,
)
from apps.financial.models import Account, FinancialPeriod, FinancialYear
from apps.financial.services.journal_service import create_journal_entry
from apps.financial.services.period_service import (
    PeriodError,
    close_period,
    create_initial_periods,
    reopen_period,
    year_end_close,
)
from apps.financial.services.posting_service import post_journal_entry

# ── Fixtures ─────────────────────────────────────────────────────


@pytest.fixture
def admin_user(db):
    return User.objects.create_superuser(email="admin@test.com", password="admin123")


@pytest.fixture
def company(db):
    return Company.objects.create(name="Test Company", code="TC")


@pytest.fixture
def numbering(db, company):
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
def expense_account(db):
    return Account.objects.create(
        code="6100", name="Salaries", account_type="expense", is_active=True
    )


@pytest.fixture
def retained_earnings_account(db):
    return Account.objects.create(
        code="3000",
        name="Retained Earnings",
        account_type="equity",
        is_active=True,
    )


@pytest.fixture
def financial_year(db, company):
    year = FinancialYear.objects.create(
        company=company,
        name="FY 2026",
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
    )
    # Create 12 periods
    for month in range(1, 13):
        month_start = date(2026, month, 1)
        if month == 12:
            month_end = date(2026, 12, 31)
        else:
            from datetime import timedelta

            month_end = date(2026, month + 1, 1) - timedelta(days=1)
        FinancialPeriod.objects.create(
            company=company,
            financial_year=year,
            name=f"Month {month}",
            start_date=month_start,
            end_date=month_end,
            is_open=True,
        )
    return year


@pytest.fixture
def open_period(db, company, financial_year):
    return FinancialPeriod.objects.filter(
        company=company, financial_year=financial_year
    ).first()


@pytest.fixture
def initial_periods(db, company):
    return create_initial_periods(company.id, year=2026)


# ── Service Tests ────────────────────────────────────────────────


@pytest.mark.django_db
class TestCloseReopenPeriod:
    def test_close_open_period(self, open_period):
        closed = close_period(open_period.id)
        assert not closed.is_open

    def test_close_twice_fails(self, open_period):
        close_period(open_period.id)
        with pytest.raises(PeriodError, match="already closed"):
            close_period(open_period.id)

    def test_close_with_unposted_entry_fails(
        self,
        open_period,
        company,
        admin_user,
        numbering,
        asset_account,
        revenue_account,
    ):
        """Closing a period with unposted entries should fail."""
        create_journal_entry(
            date=open_period.start_date,
            description="Unposted entry",
            lines=[
                {"account_id": asset_account.id, "debit": 100, "credit": 0},
                {"account_id": revenue_account.id, "debit": 0, "credit": 100},
            ],
            company_id=company.id,
            created_by_id=admin_user.id,
        )
        with pytest.raises(PeriodError, match="unposted"):
            close_period(open_period.id)

    def test_close_with_posted_entries_succeeds(
        self,
        open_period,
        company,
        admin_user,
        numbering,
        asset_account,
        revenue_account,
    ):
        """Closing with posted entries should succeed."""
        entry = create_journal_entry(
            date=open_period.start_date,
            description="Posted entry",
            lines=[
                {"account_id": asset_account.id, "debit": 100, "credit": 0},
                {"account_id": revenue_account.id, "debit": 0, "credit": 100},
            ],
            company_id=company.id,
            created_by_id=admin_user.id,
        )
        post_journal_entry(entry.id)
        closed = close_period(open_period.id)
        assert not closed.is_open

    def test_reopen_closed_period(self, open_period):
        close_period(open_period.id)
        reopened = reopen_period(open_period.id)
        assert reopened.is_open

    def test_reopen_already_open_fails(self, open_period):
        with pytest.raises(PeriodError, match="already open"):
            reopen_period(open_period.id)


@pytest.mark.django_db
class TestYearEndClose:
    def test_year_end_close_creates_new_year(
        self,
        financial_year,
        company,
        admin_user,
        numbering,
        asset_account,
        revenue_account,
        retained_earnings_account,
    ):
        """Year-end close should create a new financial year with periods."""
        from apps.financial.models import AccountCompany

        AccountCompany.objects.create(account=revenue_account, company=company)
        AccountCompany.objects.create(
            account=retained_earnings_account, company=company
        )
        # Post some entries to generate P&L balances
        entry = create_journal_entry(
            date=date(2026, 6, 15),
            description="Revenue entry",
            lines=[
                {"account_id": asset_account.id, "debit": 10000, "credit": 0},
                {"account_id": revenue_account.id, "debit": 0, "credit": 10000},
            ],
            company_id=company.id,
            created_by_id=admin_user.id,
        )
        post_journal_entry(entry.id)

        result = year_end_close(financial_year.id)
        assert result["new_year_name"] == "FY 2027"
        assert result["net_income_transferred"] > 0

        # New year should exist with 12 periods
        new_year = FinancialYear.objects.get(company=company, name="FY 2027")
        assert new_year is not None
        assert new_year.periods.count() == 12

        # Old year should be locked
        financial_year.refresh_from_db()
        assert financial_year.is_closed

    def test_year_end_close_closes_periods_automatically(
        self,
        financial_year,
        company,
        admin_user,
        numbering,
        asset_account,
        revenue_account,
        retained_earnings_account,
    ):
        """Year-end close should automatically close all periods."""
        from apps.financial.models import AccountCompany

        AccountCompany.objects.create(account=revenue_account, company=company)
        AccountCompany.objects.create(
            account=retained_earnings_account, company=company
        )

        entry = create_journal_entry(
            date=date(2026, 6, 15),
            description="Test revenue",
            lines=[
                {"account_id": asset_account.id, "debit": 1000, "credit": 0},
                {"account_id": revenue_account.id, "debit": 0, "credit": 1000},
            ],
            company_id=company.id,
            created_by_id=admin_user.id,
        )
        post_journal_entry(entry.id)

        result = year_end_close(financial_year.id)
        assert result["new_year_name"] == "FY 2027"
        assert result["net_income_transferred"] > 0

        # All original periods should now be closed
        for p in FinancialPeriod.objects.filter(financial_year=financial_year):
            assert not p.is_open

    def test_year_end_close_no_retained_earnings(
        self,
        financial_year,
        admin_user,
        company,
        numbering,
        asset_account,
        revenue_account,
    ):
        """Year-end close should fail if no retained earnings account exists."""
        Account.objects.filter(name__icontains="retained").delete()

        with pytest.raises(PeriodError, match="retained earnings"):
            year_end_close(financial_year.id)

    def test_double_year_end_close_fails(
        self,
        financial_year,
        retained_earnings_account,
        company,
        admin_user,
        numbering,
        asset_account,
        revenue_account,
    ):
        """Closing an already-closed year should fail."""
        from apps.financial.models import AccountCompany

        AccountCompany.objects.create(account=revenue_account, company=company)
        AccountCompany.objects.create(
            account=retained_earnings_account, company=company
        )

        year_end_close(financial_year.id)
        with pytest.raises(PeriodError, match="already closed"):
            year_end_close(financial_year.id)


@pytest.mark.django_db
class TestInitialPeriods:
    def test_create_initial_periods(self, company):
        year = create_initial_periods(company.id, year=2026)
        assert year.name == "FY 2026"
        assert year.periods.count() == 12
        assert all(p.is_open for p in year.periods.all())

    def test_period_dates_contiguous(self, company):
        from datetime import timedelta

        year = create_initial_periods(company.id, year=2026)
        periods = list(year.periods.order_by("start_date"))

        for i in range(len(periods) - 1):
            assert periods[i].end_date + timedelta(days=1) == periods[i + 1].start_date


# ── API Tests ────────────────────────────────────────────────────


@pytest.mark.django_db
class TestPeriodAPI:
    def _headers(self, user, company):
        token = AccessToken.for_user(user)
        return {
            "HTTP_AUTHORIZATION": f"Bearer {token}",
            "HTTP_X_COMPANY_ID": str(company.id),
        }

    def _auth_header(self, user):
        token = AccessToken.for_user(user)
        return {"HTTP_AUTHORIZATION": f"Bearer {token}"}

    def test_list_periods(self, client, admin_user, company, initial_periods):
        response = client.get(
            "/api/v1/financial/periods/",
            **self._headers(admin_user, company),
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 12

    def test_list_periods_no_company_header(
        self, client, admin_user, company, initial_periods
    ):
        response = client.get(
            "/api/v1/financial/periods/",
            **self._auth_header(admin_user),
        )
        assert response.status_code == 400

    def test_close_period_endpoint(self, client, admin_user, company, initial_periods):
        period_id = initial_periods.periods.first().id
        response = client.post(
            f"/api/v1/financial/periods/{period_id}/close/",
            **self._headers(admin_user, company),
        )
        assert response.status_code == 200
        data = response.json()
        assert data["is_open"] is False

    def test_reopen_period_endpoint(self, client, admin_user, company, initial_periods):
        period_id = initial_periods.periods.first().id
        client.post(
            f"/api/v1/financial/periods/{period_id}/close/",
            **self._headers(admin_user, company),
        )
        response = client.post(
            f"/api/v1/financial/periods/{period_id}/reopen/",
            **self._headers(admin_user, company),
        )
        assert response.status_code == 200
        data = response.json()
        assert data["is_open"] is True

    def test_list_years(self, client, admin_user, company, initial_periods):
        response = client.get(
            "/api/v1/financial/financial-years/",
            **self._headers(admin_user, company),
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert "periods" in data[0]
        assert len(data[0]["periods"]) == 12

    def test_init_periods_endpoint(self, client, admin_user, company):
        response = client.post(
            "/api/v1/financial/init-periods/",
            **self._headers(admin_user, company),
        )
        assert response.status_code == 200
        data = response.json()
        assert "FY " in data["name"]
        assert len(data["periods"]) == 12

    def test_init_periods_twice_fails(
        self, client, admin_user, company, initial_periods
    ):
        response = client.post(
            "/api/v1/financial/init-periods/",
            **self._headers(admin_user, company),
        )
        assert response.status_code == 400

    def test_year_end_close_endpoint(
        self,
        client,
        admin_user,
        company,
        financial_year,
        retained_earnings_account,
        numbering,
        asset_account,
        revenue_account,
    ):
        from apps.financial.models import AccountCompany

        AccountCompany.objects.create(account=revenue_account, company=company)
        AccountCompany.objects.create(
            account=retained_earnings_account, company=company
        )

        entry = create_journal_entry(
            date=date(2026, 6, 15),
            description="Test revenue",
            lines=[
                {"account_id": asset_account.id, "debit": 5000, "credit": 0},
                {"account_id": revenue_account.id, "debit": 0, "credit": 5000},
            ],
            company_id=company.id,
            created_by_id=admin_user.id,
        )
        # Create a period for posting
        period = financial_year.periods.filter(
            start_date__lte=date(2026, 6, 15),
            end_date__gte=date(2026, 6, 15),
        ).first()
        period.is_open = True
        period.save(update_fields=["is_open"])
        post_journal_entry(entry.id)

        response = client.post(
            f"/api/v1/financial/financial-years/{financial_year.id}/year-end-close/",
            {"retained_earnings_account_id": str(retained_earnings_account.id)},
            content_type="application/json",
            **self._headers(admin_user, company),
        )
        assert response.status_code == 200
        data = response.json()
        assert data["new_year_name"] == "FY 2027"
        assert data["net_income_transferred"] > 0
