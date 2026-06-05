"""Tests for Journal Entry Posting (T023)."""

from datetime import date

import pytest
from rest_framework_simplejwt.tokens import AccessToken

from apps.core.models import (
    Company,
    CompanyNumberingSeries,
    NumberingSeriesPolicy,
    User,
    WorkflowDefinition,
    WorkflowEdge,
    WorkflowNode,
)
from apps.financial.models import (
    Account,
    FinancialPeriod,
    GeneralLedger,
)
from apps.financial.services.journal_service import create_journal_entry
from apps.financial.services.posting_service import (
    PostingError,
    post_journal_entry,
    submit_for_approval,
)
from apps.financial.signals import on_workflow_completed

# ── Fixtures ─────────────────────────────────────────────────────


@pytest.fixture
def admin_user(db):
    return User.objects.create_superuser(email="admin@test.com", password="admin123")


@pytest.fixture
def approver_user(db):
    return User.objects.create_user(
        email="approver@test.com", password="approver123", full_name="Approver"
    )


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


@pytest.fixture
def approval_workflow(db, company):
    """Create a simple single-approval workflow for journal entries."""
    workflow = WorkflowDefinition.objects.create(
        name="JE Approval",
        module="financial",
        document_type="financial.JournalEntry",
        is_active=True,
        company=company,
    )
    WorkflowNode.objects.create(
        workflow=workflow,
        node_id="start",
        node_type="start",
        label="Start",
    )
    WorkflowNode.objects.create(
        workflow=workflow,
        node_id="approve1",
        node_type="approve",
        label="Approve",
        config={
            "approval_type": "sequential",
            "min_approvals": 1,
            "approvers": [{"type": "user", "id": ""}],  # no fixie required
        },
    )
    WorkflowNode.objects.create(
        workflow=workflow,
        node_id="end",
        node_type="end",
        label="End",
    )
    WorkflowEdge.objects.create(
        workflow=workflow,
        source_node_id="start",
        target_node_id="approve1",
    )
    WorkflowEdge.objects.create(
        workflow=workflow,
        source_node_id="approve1",
        target_node_id="end",
    )
    return workflow


# ── Service Tests ────────────────────────────────────────────────


@pytest.mark.django_db
class TestPeriodValidation:
    def test_post_without_period_fails(self, draft_entry):
        """Posting should fail when no open period exists for the entry date."""
        with pytest.raises(PostingError, match="No open financial period"):
            post_journal_entry(draft_entry.id)

    def test_post_with_closed_period_fails(self, company, draft_entry, period):
        period.is_open = False
        period.save()
        with pytest.raises(PostingError, match="No open financial period"):
            post_journal_entry(draft_entry.id)

    def test_post_with_period_succeeds(self, draft_entry, period):
        posted = post_journal_entry(draft_entry.id)
        assert posted.status == "posted"
        gl = GeneralLedger.objects.filter(journal_entry=posted).first()
        assert gl.period == period


@pytest.mark.django_db
class TestPostingService:
    def test_post_creates_gl_entries(self, draft_entry, period):
        posted = post_journal_entry(draft_entry.id)
        assert posted.status == "posted"
        assert posted.posted_at is not None

        gl_entries = GeneralLedger.objects.filter(journal_entry=posted)
        assert gl_entries.count() == 2

    def test_gl_entry_amounts(
        self, draft_entry, asset_account, revenue_account, period
    ):
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
        self, draft_entry, asset_account, company, numbering, revenue_account, period
    ):
        post_journal_entry(draft_entry.id)

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
        assert float(gl.balance) == 1500

    def test_running_balance_revenue(
        self, draft_entry, revenue_account, company, numbering, asset_account, period
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
        assert float(gl.balance) == 1200

    def test_post_already_posted_fails(self, draft_entry, period):
        post_journal_entry(draft_entry.id)
        with pytest.raises(PostingError, match="already posted"):
            post_journal_entry(draft_entry.id)

    def test_post_readonly_fields(
        self, draft_entry, asset_account, revenue_account, period
    ):
        posted = post_journal_entry(draft_entry.id)
        gl = GeneralLedger.objects.filter(journal_entry=posted).first()
        assert gl.journal_entry_line is not None
        assert gl.company is not None

    def test_gl_immutable_after_post(self, draft_entry, period):
        post_journal_entry(draft_entry.id)
        draft_entry.refresh_from_db()
        assert draft_entry.status == "posted"
        assert draft_entry.posted_at is not None

    def test_post_approved_entry_succeeds(self, draft_entry, period):
        """Approved entries should also be postable."""
        draft_entry.status = "approved"
        draft_entry.save(update_fields=["status"])
        posted = post_journal_entry(draft_entry.id)
        assert posted.status == "posted"

    def test_post_reversed_fails(self, draft_entry, period):
        draft_entry.status = "reversed"
        draft_entry.save(update_fields=["status"])
        with pytest.raises(PostingError, match="Cannot post"):
            post_journal_entry(draft_entry.id)


@pytest.mark.django_db
class TestSubmitForApproval:
    def test_submit_creates_workflow_execution(
        self, draft_entry, company, admin_user, approval_workflow
    ):
        entry = submit_for_approval(
            entry_id=draft_entry.id,
            requester=admin_user,
            company_id=company.id,
            workflow_id=approval_workflow.id,
        )
        assert entry.status == "submitted"
        from apps.core.models import WorkflowExecution

        executions = WorkflowExecution.objects.filter(
            document_type="financial.JournalEntry",
            document_id=draft_entry.id,
        )
        assert executions.count() == 1

    def test_submit_non_draft_fails(
        self, draft_entry, company, admin_user, period, approval_workflow
    ):
        post_journal_entry(draft_entry.id)
        with pytest.raises(PostingError, match="Cannot submit"):
            submit_for_approval(
                entry_id=draft_entry.id,
                requester=admin_user,
                company_id=company.id,
                workflow_id=approval_workflow.id,
            )

    def test_auto_select_workflow(
        self, draft_entry, company, admin_user, approval_workflow
    ):
        """Submit without workflow_id should auto-select."""
        entry = submit_for_approval(
            entry_id=draft_entry.id,
            requester=admin_user,
            company_id=company.id,
        )
        assert entry.status == "submitted"

    def test_auto_select_no_workflow_fails(self, draft_entry, company, admin_user):
        """Submit without any workflow should fail."""
        with pytest.raises(PostingError, match="No active approval workflow"):
            submit_for_approval(
                entry_id=draft_entry.id,
                requester=admin_user,
                company_id=company.id,
            )


@pytest.mark.django_db
class TestReversalPosting:
    def test_reversal_creates_posted_entry(
        self, draft_entry, company, admin_user, period, asset_account, revenue_account
    ):
        """Reverse_journal_entry should now also post the reversal."""
        from apps.financial.services.journal_service import reverse_journal_entry

        posted = post_journal_entry(draft_entry.id)
        reversal = reverse_journal_entry(posted.id, created_by_id=admin_user.id)

        assert reversal.status == "posted"
        assert reversal.reversal_of_id == posted.id

        # Original should be reversed
        posted.refresh_from_db()
        assert posted.status == "reversed"

        # Reversal should have opposite amounts
        reversal.refresh_from_db()
        assert float(reversal.total_debit) == float(posted.total_credit)
        assert float(reversal.total_credit) == float(posted.total_debit)


@pytest.mark.django_db
class TestApprovalSignal:
    def test_on_workflow_completed_approves_entry(
        self, draft_entry, company, admin_user, approval_workflow
    ):
        """Simulate workflow completion signal."""
        from apps.core.models import WorkflowExecution

        entry = submit_for_approval(
            entry_id=draft_entry.id,
            requester=admin_user,
            company_id=company.id,
            workflow_id=approval_workflow.id,
        )
        assert entry.status == "submitted"

        execution = WorkflowExecution.objects.get(
            document_type="financial.JournalEntry",
            document_id=draft_entry.id,
        )
        execution.status = "completed"
        execution.save(update_fields=["status"])

        on_workflow_completed(
            sender=WorkflowExecution,
            instance=execution,
            created=False,
            raw=False,
            update_fields=["status"],
        )

        entry.refresh_from_db()
        assert entry.status == "approved"


# ── API Tests ────────────────────────────────────────────────────


@pytest.mark.django_db
class TestPostingAPI:
    def _headers(self, user, company):
        token = AccessToken.for_user(user)
        return {
            "HTTP_AUTHORIZATION": f"Bearer {token}",
            "HTTP_X_COMPANY_ID": str(company.id),
        }

    def test_post_endpoint(self, client, admin_user, company, draft_entry, period):
        response = client.post(
            f"/api/v1/financial/journal-entries/{draft_entry.id}/post/",
            **self._headers(admin_user, company),
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "posted"

    def test_post_twice_fails(self, client, admin_user, company, draft_entry, period):
        client.post(
            f"/api/v1/financial/journal-entries/{draft_entry.id}/post/",
            **self._headers(admin_user, company),
        )
        response = client.post(
            f"/api/v1/financial/journal-entries/{draft_entry.id}/post/",
            **self._headers(admin_user, company),
        )
        assert response.status_code == 400

    def test_post_shows_in_list(self, client, admin_user, company, draft_entry, period):
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

    def test_submit_endpoint(
        self, client, admin_user, company, draft_entry, approval_workflow
    ):
        response = client.post(
            f"/api/v1/financial/journal-entries/{draft_entry.id}/submit/",
            **self._headers(admin_user, company),
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "submitted"

    def test_post_without_period_fails_api(
        self, client, admin_user, company, draft_entry
    ):
        response = client.post(
            f"/api/v1/financial/journal-entries/{draft_entry.id}/post/",
            **self._headers(admin_user, company),
        )
        assert response.status_code == 400
        data = response.json()
        assert "period" in data.get("detail", "").lower()
