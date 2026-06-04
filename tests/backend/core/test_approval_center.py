"""Tests for Centralized Approval Center API (T016c)."""

import uuid

import pytest
from django.utils import timezone
from rest_framework_simplejwt.tokens import AccessToken

from apps.core.models import (
    Company,
    User,
    UserCompany,
    WorkflowDefinition,
    WorkflowEdge,
    WorkflowExecution,
    WorkflowExecutionStep,
    WorkflowNode,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def company(db):
    return Company.objects.create(name="Approval Corp", code="ACORP")


@pytest.fixture
def company2(db):
    return Company.objects.create(name="Other Corp", code="OCORP2")


@pytest.fixture
def requester(db, company):
    u = User.objects.create_user(
        email="requester@ac.test",
        password="pass123",
        first_name="Request",
        last_name="User",
    )
    UserCompany.objects.create(user=u, company=company)
    return u


@pytest.fixture
def approver(db, company):
    u = User.objects.create_user(
        email="approver@ac.test",
        password="pass123",
        first_name="Approver",
        last_name="User",
    )
    UserCompany.objects.create(user=u, company=company)
    return u


@pytest.fixture
def approver2(db, company):
    u = User.objects.create_user(
        email="approver2@ac.test",
        password="pass123",
        first_name="Approver2",
        last_name="User",
    )
    UserCompany.objects.create(user=u, company=company)
    return u


@pytest.fixture
def other_company_user(db, company2):
    u = User.objects.create_user(
        email="other@ac.test",
        password="pass123",
        first_name="Other",
        last_name="User",
    )
    UserCompany.objects.create(user=u, company=company2)
    return u


def _jwt(user: User) -> str:
    """Return a Bearer token string for the given user."""
    return str(AccessToken.for_user(user))


@pytest.fixture
def workflow_def(db, company, requester):
    wf = WorkflowDefinition.objects.create(
        name="AC Workflow",
        module="financial",
        document_type="Invoice",
        company=company,
        created_by=requester,
    )
    # start → approve_1 → end
    WorkflowNode.objects.create(
        workflow=wf, node_id="start", node_type="start", label="Start"
    )
    WorkflowNode.objects.create(
        workflow=wf,
        node_id="approve_1",
        node_type="approve",
        label="Manager Approval",
        config={"approvers": [], "approval_type": "sequential", "min_approvals": 1},
    )
    WorkflowNode.objects.create(
        workflow=wf, node_id="end", node_type="end", label="End"
    )
    WorkflowEdge.objects.create(
        workflow=wf, source_node_id="start", target_node_id="approve_1"
    )
    WorkflowEdge.objects.create(
        workflow=wf, source_node_id="approve_1", target_node_id="end"
    )
    return wf


@pytest.fixture
def pending_execution(db, workflow_def, company, requester, approver):
    """An execution with a pending step for `approver`."""
    node = WorkflowNode.objects.get(workflow=workflow_def, node_id="approve_1")
    ex = WorkflowExecution.objects.create(
        workflow=workflow_def,
        document_type="Invoice",
        document_id=uuid.uuid4(),
        requester=requester,
        created_by=requester,
        company=company,
        status="pending",
        current_node_id="approve_1",
    )
    WorkflowExecutionStep.objects.create(
        execution=ex, node=node, approver=approver, status="pending"
    )
    return ex


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _auth_headers(user: User) -> dict:
    return {"HTTP_AUTHORIZATION": f"Bearer {_jwt(user)}"}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestListPendingApprovals:
    def test_returns_own_pending_only(
        self, client, pending_execution, approver, requester
    ):
        """Approver sees their pending item; requester does not."""
        resp = client.get(
            "/api/v1/core/approval-center/",
            **_auth_headers(approver),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 1
        assert data["results"][0]["execution_id"] == str(pending_execution.id)

        # Requester should not see it (not their pending step)
        resp2 = client.get(
            "/api/v1/core/approval-center/",
            **_auth_headers(requester),
        )
        assert resp2.status_code == 200
        assert resp2.json()["count"] == 0

    def test_filter_by_module(self, client, pending_execution, approver):
        """Filter by module returns correct items."""
        resp = client.get(
            "/api/v1/core/approval-center/?module=financial",
            **_auth_headers(approver),
        )
        assert resp.status_code == 200
        assert resp.json()["count"] == 1

        resp2 = client.get(
            "/api/v1/core/approval-center/?module=scm",
            **_auth_headers(approver),
        )
        assert resp2.status_code == 200
        assert resp2.json()["count"] == 0


@pytest.mark.django_db
class TestApprovalContext:
    def test_get_context(self, client, pending_execution, approver):
        resp = client.get(
            f"/api/v1/core/approval-center/{pending_execution.id}/context/",
            **_auth_headers(approver),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["execution_id"] == str(pending_execution.id)
        assert data["document_type"] == "Invoice"

    def test_context_not_found(self, client, approver):
        fake_id = uuid.uuid4()
        resp = client.get(
            f"/api/v1/core/approval-center/{fake_id}/context/",
            **_auth_headers(approver),
        )
        assert resp.status_code == 404


@pytest.mark.django_db
class TestQuickApprove:
    def test_quick_approve(self, client, pending_execution, approver):
        """Approving moves execution to completed."""
        resp = client.post(
            f"/api/v1/core/approval-center/{pending_execution.id}/quick-approve/",
            data={"comment": "Looks good"},
            content_type="application/json",
            **_auth_headers(approver),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "completed"

        pending_execution.refresh_from_db()
        assert pending_execution.status == "completed"

    def test_approve_not_found(self, client, approver):
        fake_id = uuid.uuid4()
        resp = client.post(
            f"/api/v1/core/approval-center/{fake_id}/quick-approve/",
            data={"comment": ""},
            content_type="application/json",
            **_auth_headers(approver),
        )
        assert resp.status_code == 404


@pytest.mark.django_db
class TestQuickRejectRequiresComment:
    def test_reject_without_comment_returns_422(
        self, client, pending_execution, approver
    ):
        """Reject with empty comment must return 422."""
        resp = client.post(
            f"/api/v1/core/approval-center/{pending_execution.id}/quick-reject/",
            data={"comment": ""},
            content_type="application/json",
            **_auth_headers(approver),
        )
        assert resp.status_code == 422

    def test_reject_with_comment_succeeds(self, client, pending_execution, approver):
        resp = client.post(
            f"/api/v1/core/approval-center/{pending_execution.id}/quick-reject/",
            data={"comment": "Does not meet policy"},
            content_type="application/json",
            **_auth_headers(approver),
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "rejected"

        pending_execution.refresh_from_db()
        assert pending_execution.status == "rejected"


@pytest.mark.django_db
class TestDelegate:
    def test_delegate_to_user(self, client, pending_execution, approver, approver2):
        resp = client.post(
            f"/api/v1/core/approval-center/{pending_execution.id}/delegate/",
            data={
                "delegated_to_id": str(approver2.id),
                "comment": "Please handle this",
            },
            content_type="application/json",
            **_auth_headers(approver),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "Delegated" in data["message"] or data["status"] == "pending"

    def test_delegate_to_other_company_user_rejected(
        self, client, pending_execution, approver, other_company_user
    ):
        resp = client.post(
            f"/api/v1/core/approval-center/{pending_execution.id}/delegate/",
            data={
                "delegated_to_id": str(other_company_user.id),
                "comment": "Delegate",
            },
            content_type="application/json",
            **_auth_headers(approver),
        )
        assert resp.status_code == 403


@pytest.mark.django_db
class TestApprovalStats:
    def test_stats_returns_correct_counts(self, client, pending_execution, approver):
        resp = client.get(
            "/api/v1/core/approval-center/stats/",
            **_auth_headers(approver),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_pending"] == 1
        assert data["overdue_count"] == 0
        assert isinstance(data["by_module"], list)
        assert data["by_module"][0]["module"] == "financial"

    def test_stats_overdue(self, client, pending_execution, approver):
        """Force overdue by backdating started_at."""
        WorkflowExecution.objects.filter(id=pending_execution.id).update(
            started_at=timezone.now() - timezone.timedelta(hours=72)
        )
        resp = client.get(
            "/api/v1/core/approval-center/stats/",
            **_auth_headers(approver),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["overdue_count"] >= 1


@pytest.mark.django_db
class TestCompanyScoping:
    def test_other_company_user_cannot_see_approvals(
        self, client, pending_execution, other_company_user
    ):
        """User from a different company should not see approvals."""
        resp = client.get(
            "/api/v1/core/approval-center/",
            **_auth_headers(other_company_user),
        )
        assert resp.status_code == 200
        assert resp.json()["count"] == 0


@pytest.mark.django_db
class TestVersionCheck:
    def test_concurrent_update_is_handled(
        self, client, pending_execution, approver, approver2
    ):
        """Second approval after first completion should fail gracefully."""
        # First approval — succeeds
        resp1 = client.post(
            f"/api/v1/core/approval-center/{pending_execution.id}/quick-approve/",
            data={"comment": "First approver"},
            content_type="application/json",
            **_auth_headers(approver),
        )
        assert resp1.status_code == 200

        # Second approver tries to approve same (now completed) execution
        node = WorkflowNode.objects.get(
            workflow=pending_execution.workflow, node_id="approve_1"
        )
        WorkflowExecutionStep.objects.create(
            execution=pending_execution,
            node=node,
            approver=approver2,
            status="pending",
        )
        resp2 = client.post(
            f"/api/v1/core/approval-center/{pending_execution.id}/quick-approve/",
            data={"comment": "Second approver"},
            content_type="application/json",
            **_auth_headers(approver2),
        )
        # Should return 200 but with a "Cannot act" message (already completed)
        assert resp2.status_code == 200
        assert "Cannot act" in resp2.json().get("message", "")
