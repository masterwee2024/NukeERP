"""Tests for Journal Entry Posting (T023)."""

from datetime import date

import pytest
from rest_framework_simplejwt.tokens import AccessToken

from apps.core.models import (
    Company,
    CompanyNumberingSeries,
    NumberingSeriesPolicy,
    User,
)
from apps.financial.models import Account, GeneralLedger
from apps.financial.services.journal_service import create_journal_entry
from apps.financial.services.posting_service import PostingError, post_journal_entry

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
def liability_account(db):
    return Account.objects.create(
        code="2110", name="AP", account_type="liability", is_active=True
    )


@pytest.fixture
def draft_entry(db, company, admin_user, numbering, asset_account, revenue_account):
    return create_journal_entry(
        date=date(2026, 6, 1),
        description="Test entry",
        lines=[
            {
                "account_id": asset_account.id,
                "debit": 1000,
                "credit": 0,
                "description": "Debit",
            },
            {
                "account_id": revenue_account.id,
                "debit": 0,
                "credit": 1000,
                "description": "Credit",
            },
        ],
        company_id=company.id,
        created_by_id=admin_user.id,
    )


# ── Service Tests ────────────────────────────────────────────────


@pytest.mark.django_db
class TestPostingService:
    def test_post_creates_gl_entries(self, draft_entry):
        posted = post_journal_entry(draft_entry.id)
        assert posted.status == "posted"
        assert posted.posted_at is not None

        gl_entries = GeneralLedger.objects.filter(journal_entry=posted)
        assert gl_entries.count() == 2

    def test_gl_entry_amounts(self, draft_entry, asset_account, revenue_account):
        post_journal_entry(draft_entry.id)

        asset_gl = GeneralLedger.objects.get(
            journal_entry=draft_entry, account=asset_account
        )
        assert float(asset_gl.debit) == 1000
        assert float(asset_gl.credit) == 0

        rev_gl = GeneralLedger.objects.get(
            journal_entry=draft_entry, account=revenue_account
        )
        assert float(rev_gl.debit) == 0
        assert float(rev_gl.credit) == 1000

    def test_running_balance_asset(
        self, draft_entry, asset_account, company, numbering, revenue_account
    ):
        post_journal_entry(draft_entry.id)

        # Create another entry and post it
        entry2 = create_journal_entry(
            date=date(2026, 6, 2),
            description="Second entry",
            lines=[
                {
                    "account_id": asset_account.id,
                    "debit": 500,
                    "credit": 0,
                    "description": "More cash",
                },
                {
                    "account_id": revenue_account.id,
                    "debit": 0,
                    "credit": 500,
                    "description": "More revenue",
                },
            ],
            company_id=company.id,
        )
        post_journal_entry(entry2.id)

        gl_entries = GeneralLedger.objects.filter(
            account=asset_account, journal_entry=entry2
        )
        assert gl_entries.count() == 1
        gl = gl_entries.first()
        assert float(gl.balance) == 1500  # 1000 + 500

    def test_running_balance_revenue(
        self, draft_entry, revenue_account, company, numbering, asset_account
    ):
        post_journal_entry(draft_entry.id)

        entry2 = create_journal_entry(
            date=date(2026, 6, 2),
            description="More revenue",
            lines=[
                {
                    "account_id": asset_account.id,
                    "debit": 200,
                    "credit": 0,
                    "description": "Cash",
                },
                {
                    "account_id": revenue_account.id,
                    "debit": 0,
                    "credit": 200,
                    "description": "Rev",
                },
            ],
            company_id=company.id,
        )
        post_journal_entry(entry2.id)

        gl = GeneralLedger.objects.get(account=revenue_account, journal_entry=entry2)
        assert float(gl.balance) == 1200  # 1000 + 200 (revenue is credit-normal)

    def test_post_already_posted_fails(self, draft_entry):
        post_journal_entry(draft_entry.id)
        with pytest.raises(PostingError, match="already posted"):
            post_journal_entry(draft_entry.id)

    def test_post_readonly_fields(self, draft_entry, asset_account, revenue_account):
        posted = post_journal_entry(draft_entry.id)
        gl = GeneralLedger.objects.filter(journal_entry=posted).first()
        assert gl.journal_entry_line is not None
        assert gl.company is not None

    def test_gl_immutable_after_post(self, draft_entry):
        post_journal_entry(draft_entry.id)
        draft_entry.refresh_from_db()
        assert draft_entry.status == "posted"
        assert draft_entry.posted_at is not None


# ── API Tests ────────────────────────────────────────────────────


@pytest.mark.django_db
class TestPostingAPI:
    def _headers(self, user, company):
        token = AccessToken.for_user(user)
        return {
            "HTTP_AUTHORIZATION": f"Bearer {token}",
            "HTTP_X_COMPANY_ID": str(company.id),
        }

    def test_post_endpoint(self, client, admin_user, company, draft_entry):
        response = client.post(
            f"/api/v1/financial/journal-entries/{draft_entry.id}/post/",
            **self._headers(admin_user, company),
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "posted"

    def test_post_twice_fails(self, client, admin_user, company, draft_entry):
        client.post(
            f"/api/v1/financial/journal-entries/{draft_entry.id}/post/",
            **self._headers(admin_user, company),
        )
        response = client.post(
            f"/api/v1/financial/journal-entries/{draft_entry.id}/post/",
            **self._headers(admin_user, company),
        )
        assert response.status_code == 400

    def test_post_shows_in_list(self, client, admin_user, company, draft_entry):
        client.post(
            f"/api/v1/financial/journal-entries/{draft_entry.id}/post/",
            **self._headers(admin_user, company),
        )
        response = client.get(
            "/api/v1/financial/journal-entries/?status=posted",
            **self._headers(admin_user, company),
        )
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 1
