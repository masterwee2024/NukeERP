"""Tests for AccountPeriodBalance posting integration."""

from datetime import date

import pytest

from apps.financial.models import (
    Account,
    AccountPeriodBalance,
    Company,
    FinancialPeriod,
)
from apps.financial.services.journal_service import create_journal_entry
from apps.financial.services.posting_service import post_journal_entry


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
class TestAccountPeriodBalance:
    def test_post_updates_balance(
        self, company, period, asset_account, revenue_account, numbering
    ):
        entry = create_journal_entry(
            date=date(2026, 6, 15),
            description="Test",
            lines=[
                {"account_id": asset_account.id, "debit": 1000, "credit": 0},
                {"account_id": revenue_account.id, "debit": 0, "credit": 1000},
            ],
            company_id=company.id,
        )
        post_journal_entry(entry.id)

        bal = AccountPeriodBalance.objects.get(
            account=asset_account, company=company, period=period
        )
        assert float(bal.period_debit) == 1000
        assert float(bal.period_credit) == 0
        assert float(bal.closing_debit) == 1000

        bal_rev = AccountPeriodBalance.objects.get(
            account=revenue_account, company=company, period=period
        )
        assert float(bal_rev.period_credit) == 1000

    def test_multiple_entries_aggregate(
        self, company, period, asset_account, revenue_account, numbering
    ):
        for i in range(3):
            entry = create_journal_entry(
                date=date(2026, 6, 1 + i),
                description=f"Entry {i}",
                lines=[
                    {"account_id": asset_account.id, "debit": 500, "credit": 0},
                    {"account_id": revenue_account.id, "debit": 0, "credit": 500},
                ],
                company_id=company.id,
            )
            post_journal_entry(entry.id)

        bal = AccountPeriodBalance.objects.get(
            account=asset_account, company=company, period=period
        )
        assert float(bal.period_debit) == 1500

    def test_multiple_periods_independent(
        self, company, period, period2, asset_account, revenue_account, numbering
    ):
        # Post in period 1
        e1 = create_journal_entry(
            date=date(2026, 6, 15),
            description="P1",
            lines=[
                {"account_id": asset_account.id, "debit": 1000, "credit": 0},
                {"account_id": revenue_account.id, "debit": 0, "credit": 1000},
            ],
            company_id=company.id,
        )
        post_journal_entry(e1.id)

        # Post in period 2
        e2 = create_journal_entry(
            date=date(2026, 7, 15),
            description="P2",
            lines=[
                {"account_id": asset_account.id, "debit": 500, "credit": 0},
                {"account_id": revenue_account.id, "debit": 0, "credit": 500},
            ],
            company_id=company.id,
        )
        post_journal_entry(e2.id)

        bal_p1 = AccountPeriodBalance.objects.get(
            account=asset_account, company=company, period=period
        )
        bal_p2 = AccountPeriodBalance.objects.get(
            account=asset_account, company=company, period=period2
        )
        assert float(bal_p1.period_debit) == 1000
        assert float(bal_p2.period_debit) == 500

    def test_zero_activity_no_orphan(
        self, company, period, asset_account, revenue_account
    ):
        """No balance for accounts that weren't posted."""
        assert AccountPeriodBalance.objects.filter(company=company).count() == 0

    def test_backfill_function(
        self, company, period, asset_account, revenue_account, numbering
    ):
        """Test the backfill function creates rows from existing GL entries."""
        entry = create_journal_entry(
            date=date(2026, 6, 15),
            description="Test",
            lines=[
                {"account_id": asset_account.id, "debit": 2000, "credit": 0},
                {"account_id": revenue_account.id, "debit": 0, "credit": 2000},
            ],
            company_id=company.id,
        )
        post_journal_entry(entry.id)

        from apps.financial.services.report_service import (
            backfill_account_period_balances,
        )

        AccountPeriodBalance.objects.all().delete()
        assert AccountPeriodBalance.objects.count() == 0

        backfill_account_period_balances(company.id)
        assert AccountPeriodBalance.objects.filter(company=company).count() == 2

        bal = AccountPeriodBalance.objects.get(
            account=asset_account, company=company, period=period
        )
        assert float(bal.period_debit) == 2000
