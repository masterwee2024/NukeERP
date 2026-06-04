"""Tests for Journal Entry CRUD (T022)."""

from datetime import date

import pytest
from rest_framework_simplejwt.tokens import AccessToken

from apps.core.models import (
    Company,
    CompanyNumberingSeries,
    NumberingSeriesPolicy,
    User,
)
from apps.financial.models import Account, JournalEntry
from apps.financial.services.journal_service import (
    BalanceError,
    create_journal_entry,
    delete_journal_entry,
    reverse_journal_entry,
    update_journal_entry,
)

# ── Fixtures ─────────────────────────────────────────────────────


@pytest.fixture
def admin_user(db):
    return User.objects.create_superuser(
        email="admin@test.com",
        password="admin123",
        first_name="Admin",
        last_name="User",
    )


@pytest.fixture
def company(db):
    return Company.objects.create(name="Test Company", code="TC")


@pytest.fixture
def asset_account(db):
    return Account.objects.create(
        code="1110", name="Cash", account_type="asset", is_active=True
    )


@pytest.fixture
def revenue_account(db):
    return Account.objects.create(
        code="4100", name="Sales Revenue", account_type="revenue", is_active=True
    )


@pytest.fixture
def expense_account(db):
    return Account.objects.create(
        code="6100", name="Salaries", account_type="expense", is_active=True
    )


@pytest.fixture
def numbering_policy(db, company):
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
def balanced_lines(asset_account, revenue_account):
    return [
        {
            "account_id": asset_account.id,
            "debit": 1000,
            "credit": 0,
            "description": "Payment received",
        },
        {
            "account_id": revenue_account.id,
            "debit": 0,
            "credit": 1000,
            "description": "Sales revenue",
        },
    ]


@pytest.fixture
def journal_entry(db, company, admin_user, balanced_lines, numbering_policy):
    return create_journal_entry(
        date=date(2026, 6, 1),
        description="Test entry",
        lines=balanced_lines,
        company_id=company.id,
        created_by_id=admin_user.id,
    )


# ── Service Tests ────────────────────────────────────────────────


@pytest.mark.django_db
class TestJournalService:
    def test_create_balanced_entry(self, journal_entry):
        assert journal_entry.status == "draft"
        assert journal_entry.total_debit == 1000
        assert journal_entry.total_credit == 1000
        assert journal_entry.lines.count() == 2

    def test_create_unbalanced_entry(self, asset_account, company):
        with pytest.raises(BalanceError):
            create_journal_entry(
                date=date(2026, 6, 1),
                description="Unbalanced",
                lines=[{"account_id": asset_account.id, "debit": 100, "credit": 0}],
                company_id=company.id,
            )

    def test_create_entry_no_lines(self, company):
        with pytest.raises(ValueError, match="at least one line"):
            create_journal_entry(
                date=date(2026, 6, 1),
                description="Empty",
                lines=[],
                company_id=company.id,
            )

    def test_update_draft_entry(self, journal_entry, expense_account):
        updated = update_journal_entry(
            entry_id=journal_entry.id,
            description="Updated description",
            lines=[
                {
                    "account_id": expense_account.id,
                    "debit": 500,
                    "credit": 0,
                    "description": "Expense",
                },
                {
                    "account_id": journal_entry.lines.first().account_id,
                    "debit": 0,
                    "credit": 500,
                    "description": "Offset",
                },
            ],
        )
        assert updated.description == "Updated description"
        assert updated.lines.count() == 2

    def test_update_posted_entry_fails(self, journal_entry):
        journal_entry.status = "posted"
        journal_entry.save(update_fields=["status"])
        with pytest.raises(ValueError, match="Cannot edit"):
            update_journal_entry(
                entry_id=journal_entry.id, description="Trying to edit"
            )

    def test_delete_draft_entry(self, journal_entry):
        delete_journal_entry(journal_entry.id)
        assert not JournalEntry.objects.filter(id=journal_entry.id).exists()

    def test_delete_posted_entry_fails(self, journal_entry):
        journal_entry.status = "posted"
        journal_entry.save(update_fields=["status"])
        with pytest.raises(ValueError, match="Cannot delete"):
            delete_journal_entry(journal_entry.id)

    def test_reverse_posted_entry(self, journal_entry, admin_user):
        journal_entry.status = "posted"
        journal_entry.save(update_fields=["status"])

        reversal = reverse_journal_entry(journal_entry.id, created_by_id=admin_user.id)
        assert reversal.reversal_of_id == journal_entry.id
        assert reversal.total_debit == 1000
        assert reversal.total_credit == 1000

        # Debits and credits should be swapped
        reversal_lines = list(reversal.lines.all().order_by("line_number"))
        assert float(reversal_lines[0].debit) == 0
        assert float(reversal_lines[0].credit) == 1000
        assert float(reversal_lines[1].debit) == 1000
        assert float(reversal_lines[1].credit) == 0

        # Original should be marked as reversed
        journal_entry.refresh_from_db()
        assert journal_entry.status == "reversed"

    def test_reverse_draft_entry_fails(self, journal_entry):
        with pytest.raises(ValueError, match="Only posted"):
            reverse_journal_entry(journal_entry.id)

    def test_reverse_reversal_fails(self, journal_entry, admin_user):
        journal_entry.status = "posted"
        journal_entry.save(update_fields=["status", "version"])

        reversal = reverse_journal_entry(journal_entry.id, created_by_id=admin_user.id)
        JournalEntry.objects.filter(id=reversal.id).update(status="posted")

        with pytest.raises(ValueError, match="Cannot reverse"):
            reverse_journal_entry(reversal.id)


# ── API Tests ────────────────────────────────────────────────────


@pytest.mark.django_db
class TestJournalAPI:
    def _auth_header(self, user):
        token = AccessToken.for_user(user)
        return {"HTTP_AUTHORIZATION": f"Bearer {token}"}

    def _company_header(self, company):
        return {"HTTP_X_COMPANY_ID": str(company.id)}

    def _headers(self, user, company):
        h = self._auth_header(user)
        h.update(self._company_header(company))
        return h

    def test_list_empty(self, client, admin_user, company):
        response = client.get(
            "/api/v1/financial/journal-entries/", **self._headers(admin_user, company)
        )
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 0

    def test_create_entry(
        self,
        client,
        admin_user,
        company,
        asset_account,
        revenue_account,
        numbering_policy,
    ):
        payload = {
            "date": "2026-06-01",
            "description": "API test entry",
            "lines": [
                {"account_id": str(asset_account.id), "debit": 500, "credit": 0},
                {"account_id": str(revenue_account.id), "debit": 0, "credit": 500},
            ],
        }
        response = client.post(
            "/api/v1/financial/journal-entries/",
            payload,
            content_type="application/json",
            **self._headers(admin_user, company),
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total_debit"] == 500
        assert data["status"] == "draft"
        assert len(data["lines"]) == 2

    def test_create_entry_unbalanced(self, client, admin_user, company, asset_account):
        payload = {
            "date": "2026-06-01",
            "description": "Unbalanced",
            "lines": [
                {"account_id": str(asset_account.id), "debit": 100, "credit": 0},
            ],
        }
        response = client.post(
            "/api/v1/financial/journal-entries/",
            payload,
            content_type="application/json",
            **self._headers(admin_user, company),
        )
        assert response.status_code == 400

    def test_get_entry(self, client, admin_user, company, journal_entry):
        response = client.get(
            f"/api/v1/financial/journal-entries/{journal_entry.id}/",
            **self._headers(admin_user, company),
        )
        assert response.status_code == 200
        data = response.json()
        assert data["entry_number"] == journal_entry.entry_number
        assert len(data["lines"]) == 2

    def test_get_entry_wrong_company(self, client, admin_user, company, journal_entry):
        other = Company.objects.create(name="Other", code="OT")
        response = client.get(
            f"/api/v1/financial/journal-entries/{journal_entry.id}/",
            **self._headers(admin_user, other),
        )
        assert response.status_code == 404

    def test_delete_entry(self, client, admin_user, company, journal_entry):
        response = client.delete(
            f"/api/v1/financial/journal-entries/{journal_entry.id}/",
            **self._headers(admin_user, company),
        )
        assert response.status_code == 200

    def test_reverse_entry(self, client, admin_user, company, journal_entry):
        journal_entry.status = "posted"
        journal_entry.save(update_fields=["status"])

        response = client.post(
            f"/api/v1/financial/journal-entries/{journal_entry.id}/reverse/",
            **self._headers(admin_user, company),
        )
        assert response.status_code == 200
        data = response.json()
        assert data["reversal_of_id"] == str(journal_entry.id)

    def test_reverse_draft_fails(self, client, admin_user, company, journal_entry):
        response = client.post(
            f"/api/v1/financial/journal-entries/{journal_entry.id}/reverse/",
            **self._headers(admin_user, company),
        )
        assert response.status_code == 400

    def test_list_filter_by_status(self, client, admin_user, company, journal_entry):
        response = client.get(
            "/api/v1/financial/journal-entries/?status=draft",
            **self._headers(admin_user, company),
        )
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 1

    def test_list_filter_no_match(self, client, admin_user, company):
        response = client.get(
            "/api/v1/financial/journal-entries/?status=posted",
            **self._headers(admin_user, company),
        )
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 0
