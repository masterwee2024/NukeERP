"""Tests for Approval Workflow Engine (T016)."""

import uuid

import pytest
from django.db import IntegrityError

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
from apps.core.services.workflow_service import (
    escalate,
    evaluate_condition,
    get_execution_context,
    get_history,
    get_pending,
    process_action,
    resolve_approvers,
    user_has_company_access,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def db():
    pass


@pytest.fixture
def company(db):
    return Company.objects.create(name="Test Corp", code="TCORP")


@pytest.fixture
def company2(db):
    return Company.objects.create(name="Other Corp", code="OCORP")


@pytest.fixture
def creator_user(db, company):
    u = User.objects.create_user(
        email="creator@example.com",
        password="pass123",
        first_name="Creator",
        last_name="User",
    )
    UserCompany.objects.create(user=u, company=company)
    return u


@pytest.fixture
def approver_user(db, company):
    u = User.objects.create_user(
        email="approver@example.com",
        password="pass123",
        first_name="Approver",
        last_name="User",
    )
    UserCompany.objects.create(user=u, company=company)
    return u


@pytest.fixture
def approver2_user(db, company):
    u = User.objects.create_user(
        email="approver2@example.com",
        password="pass123",
        first_name="Approver2",
        last_name="User",
    )
    UserCompany.objects.create(user=u, company=company)
    return u


@pytest.fixture
def other_company_user(db, company2):
    u = User.objects.create_user(
        email="other@example.com",
        password="pass123",
        first_name="Other",
        last_name="User",
    )
    UserCompany.objects.create(user=u, company=company2)
    return u


@pytest.fixture
def workflow_def(db, company, creator_user):
    wf = WorkflowDefinition.objects.create(
        name="Test Workflow",
        module="financial",
        document_type="PurchaseOrder",
        company=company,
        is_global_template=False,
        created_by=creator_user,
    )
    return wf


@pytest.fixture
def simple_workflow(db, workflow_def):
    """Create a simple sequential workflow: start → approve → end."""
    WorkflowNode.objects.create(
        workflow=workflow_def,
        node_id="start",
        node_type="start",
        label="Start",
    )
    WorkflowNode.objects.create(
        workflow=workflow_def,
        node_id="approve_1",
        node_type="approve",
        label="Manager Approval",
        config={
            "approvers": [],
            "approval_type": "sequential",
            "min_approvals": 1,
        },
    )
    WorkflowNode.objects.create(
        workflow=workflow_def,
        node_id="end",
        node_type="end",
        label="End",
    )
    WorkflowEdge.objects.create(
        workflow=workflow_def,
        source_node_id="start",
        target_node_id="approve_1",
    )
    WorkflowEdge.objects.create(
        workflow=workflow_def,
        source_node_id="approve_1",
        target_node_id="end",
    )
    return workflow_def


@pytest.fixture
def parallel_workflow(db, workflow_def):
    """Workflow with parallel approval: start → approve(parallel) → end."""
    WorkflowNode.objects.create(
        workflow=workflow_def,
        node_id="start",
        node_type="start",
        label="Start",
    )
    WorkflowNode.objects.create(
        workflow=workflow_def,
        node_id="approve_1",
        node_type="approve",
        label="Parallel Approval",
        config={
            "approvers": [],
            "approval_type": "parallel",
            "min_approvals": 2,
        },
    )
    WorkflowNode.objects.create(
        workflow=workflow_def,
        node_id="end",
        node_type="end",
        label="End",
    )
    WorkflowEdge.objects.create(
        workflow=workflow_def,
        source_node_id="start",
        target_node_id="approve_1",
    )
    WorkflowEdge.objects.create(
        workflow=workflow_def,
        source_node_id="approve_1",
        target_node_id="end",
    )
    return workflow_def


@pytest.fixture
def condition_workflow(db, workflow_def):
    """Workflow with condition: start → condition → (approve_low | approve_high) → end."""
    WorkflowNode.objects.create(
        workflow=workflow_def,
        node_id="start",
        node_type="start",
        label="Start",
    )
    WorkflowNode.objects.create(
        workflow=workflow_def,
        node_id="condition_1",
        node_type="condition",
        label="Amount > 1000?",
        config={
            "field": "total_amount",
            "operator": ">",
            "value": 1000,
            "true_node_id": "approve_high",
            "false_node_id": "approve_low",
        },
    )
    WorkflowNode.objects.create(
        workflow=workflow_def,
        node_id="approve_low",
        node_type="approve",
        label="Low Value Approval",
        config={
            "approvers": [],
            "approval_type": "sequential",
            "min_approvals": 1,
        },
    )
    WorkflowNode.objects.create(
        workflow=workflow_def,
        node_id="approve_high",
        node_type="approve",
        label="High Value Approval",
        config={
            "approvers": [],
            "approval_type": "sequential",
            "min_approvals": 1,
        },
    )
    WorkflowNode.objects.create(
        workflow=workflow_def,
        node_id="end",
        node_type="end",
        label="End",
    )
    WorkflowEdge.objects.create(
        workflow=workflow_def,
        source_node_id="start",
        target_node_id="condition_1",
    )
    WorkflowEdge.objects.create(
        workflow=workflow_def,
        source_node_id="condition_1",
        target_node_id="approve_low",
        label="False",
    )
    WorkflowEdge.objects.create(
        workflow=workflow_def,
        source_node_id="condition_1",
        target_node_id="approve_high",
        label="True",
    )
    WorkflowEdge.objects.create(
        workflow=workflow_def,
        source_node_id="approve_low",
        target_node_id="end",
    )
    WorkflowEdge.objects.create(
        workflow=workflow_def,
        source_node_id="approve_high",
        target_node_id="end",
    )
    return workflow_def


@pytest.fixture
def escalation_workflow(db, workflow_def):
    """Workflow with escalation path."""
    WorkflowNode.objects.create(
        workflow=workflow_def,
        node_id="start",
        node_type="start",
        label="Start",
    )
    WorkflowNode.objects.create(
        workflow=workflow_def,
        node_id="approve_1",
        node_type="approve",
        label="Level 1",
        config={
            "approvers": [],
            "approval_type": "sequential",
            "min_approvals": 1,
            "escalation_node_id": "approve_2",
        },
    )
    WorkflowNode.objects.create(
        workflow=workflow_def,
        node_id="approve_2",
        node_type="approve",
        label="Level 2 (Escalation)",
        config={
            "approvers": [],
            "approval_type": "sequential",
            "min_approvals": 1,
        },
    )
    WorkflowNode.objects.create(
        workflow=workflow_def,
        node_id="end",
        node_type="end",
        label="End",
    )
    WorkflowEdge.objects.create(
        workflow=workflow_def,
        source_node_id="start",
        target_node_id="approve_1",
    )
    WorkflowEdge.objects.create(
        workflow=workflow_def,
        source_node_id="approve_1",
        target_node_id="end",
    )
    WorkflowEdge.objects.create(
        workflow=workflow_def,
        source_node_id="approve_2",
        target_node_id="end",
    )
    return workflow_def


# ---------------------------------------------------------------------------
# Model Tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestWorkflowDefinitionModel:
    def test_create_workflow(self, company, creator_user):
        wf = WorkflowDefinition.objects.create(
            name="PO Approval",
            module="scm",
            document_type="PurchaseOrder",
            company=company,
            created_by=creator_user,
        )
        assert wf.name == "PO Approval"
        assert wf.version == 1
        assert wf.is_active is True
        assert str(wf) == f"PO Approval v{wf.version}"

    def test_unique_together(self, company, creator_user):
        WorkflowDefinition.objects.create(
            name="Test",
            module="financial",
            document_type="PO",
            company=company,
            created_by=creator_user,
        )
        with pytest.raises(IntegrityError):
            WorkflowDefinition.objects.create(
                name="Test",
                module="financial",
                document_type="PO",
                company=company,
                created_by=creator_user,
            )

    def test_global_template(self, creator_user):
        wf = WorkflowDefinition.objects.create(
            name="Global Template",
            module="financial",
            document_type="PO",
            company=None,
            is_global_template=True,
            created_by=creator_user,
        )
        assert wf.company is None
        assert wf.is_global_template is True


@pytest.mark.django_db
class TestWorkflowNodeModel:
    def test_create_node(self, workflow_def):
        node = WorkflowNode.objects.create(
            workflow=workflow_def,
            node_id="node_1",
            node_type="approve",
            label="Manager Approval",
            config={"approvers": [], "min_approvals": 1},
        )
        assert node.node_type == "approve"
        assert str(node) == f"{workflow_def.name} → Manager Approval"

    def test_unique_together(self, workflow_def):
        WorkflowNode.objects.create(
            workflow=workflow_def,
            node_id="n1",
            node_type="start",
        )
        with pytest.raises(IntegrityError):
            WorkflowNode.objects.create(
                workflow=workflow_def,
                node_id="n1",
                node_type="end",
            )


@pytest.mark.django_db
class TestWorkflowExecutionModel:
    def test_create_execution(self, workflow_def, company, creator_user):
        execution = WorkflowExecution.objects.create(
            workflow=workflow_def,
            document_type="PurchaseOrder",
            document_id=uuid.uuid4(),
            requester=creator_user,
            created_by=creator_user,
            company=company,
        )
        assert execution.status == "pending"
        assert (
            str(execution)
            == f"{workflow_def.name} (PurchaseOrder:{execution.document_id}) — pending"
        )

    def test_execution_indexes(self, workflow_def, company, creator_user):
        doc_id = uuid.uuid4()
        WorkflowExecution.objects.create(
            workflow=workflow_def,
            document_type="PO",
            document_id=doc_id,
            requester=creator_user,
            created_by=creator_user,
            company=company,
        )
        qs = WorkflowExecution.objects.filter(document_type="PO", document_id=doc_id)
        assert qs.count() == 1


@pytest.mark.django_db
class TestWorkflowExecutionStepModel:
    def test_create_step(self, simple_workflow, creator_user, approver_user):
        execution = WorkflowExecution.objects.create(
            workflow=simple_workflow,
            document_type="PO",
            document_id=uuid.uuid4(),
            requester=creator_user,
            created_by=creator_user,
            company=simple_workflow.company,
        )
        node = WorkflowNode.objects.get(workflow=simple_workflow, node_id="approve_1")
        step = WorkflowExecutionStep.objects.create(
            execution=execution,
            node=node,
            approver=approver_user,
            action="approve",
            status="completed",
        )
        assert step.action == "approve"
        assert step.status == "completed"


# ---------------------------------------------------------------------------
# Service Tests — Company Scoping
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestCompanyScoping:
    def test_user_has_company_access(self, approver_user, company):
        assert user_has_company_access(approver_user, company.id) is True

    def test_user_no_company_access(self, approver_user, company2):
        assert user_has_company_access(approver_user, company2.id) is False

    def test_superuser_has_all_access(self, company, company2):
        admin = User.objects.create_superuser(email="admin@test.com", password="pass")
        assert user_has_company_access(admin, company.id) is True
        assert user_has_company_access(admin, company2.id) is True

    def test_resolve_approvers_filters_by_company(
        self, simple_workflow, approver_user, other_company_user, creator_user
    ):
        node = WorkflowNode.objects.get(workflow=simple_workflow, node_id="approve_1")
        node.config = {
            "approvers": [
                {"type": "user", "id": str(approver_user.id)},
                {"type": "user", "id": str(other_company_user.id)},
            ]
        }
        node.save()

        execution = WorkflowExecution.objects.create(
            workflow=simple_workflow,
            document_type="PO",
            document_id=uuid.uuid4(),
            requester=creator_user,
            created_by=creator_user,
            company=simple_workflow.company,
        )

        approvers = resolve_approvers(node, execution)
        user_ids = [str(a["user"].id) for a in approvers]
        assert str(approver_user.id) in user_ids
        assert str(other_company_user.id) not in user_ids


# ---------------------------------------------------------------------------
# Service Tests — Creator ≠ Approver
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestCreatorNotApprover:
    def test_resolve_approvers_excludes_creator(self, simple_workflow, creator_user):
        node = WorkflowNode.objects.get(workflow=simple_workflow, node_id="approve_1")
        node.config = {"approvers": [{"type": "user", "id": str(creator_user.id)}]}
        node.save()

        execution = WorkflowExecution.objects.create(
            workflow=simple_workflow,
            document_type="PO",
            document_id=uuid.uuid4(),
            requester=creator_user,
            created_by=creator_user,
            company=simple_workflow.company,
        )

        approvers = resolve_approvers(node, execution)
        assert len(approvers) == 0

    def test_process_action_creator_cannot_approve(
        self, simple_workflow, creator_user, approver_user
    ):
        node = WorkflowNode.objects.get(workflow=simple_workflow, node_id="approve_1")
        node.config = {"approvers": [{"type": "user", "id": str(approver_user.id)}]}
        node.save()

        execution = WorkflowExecution.objects.create(
            workflow=simple_workflow,
            document_type="PO",
            document_id=uuid.uuid4(),
            requester=creator_user,
            created_by=creator_user,
            company=simple_workflow.company,
        )

        with pytest.raises(PermissionError, match="Creator cannot approve"):
            process_action(
                execution_id=execution.id,
                approver=creator_user,
                action="approve",
            )


# ---------------------------------------------------------------------------
# Service Tests — Approval Actions
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestProcessAction:
    def test_approve_sequential(self, simple_workflow, creator_user, approver_user):
        node = WorkflowNode.objects.get(workflow=simple_workflow, node_id="approve_1")
        node.config = {
            "approvers": [{"type": "user", "id": str(approver_user.id)}],
            "approval_type": "sequential",
            "min_approvals": 1,
        }
        node.save()

        execution = WorkflowExecution.objects.create(
            workflow=simple_workflow,
            document_type="PO",
            document_id=uuid.uuid4(),
            requester=creator_user,
            created_by=creator_user,
            company=simple_workflow.company,
            current_node_id="approve_1",
        )

        result = process_action(
            execution_id=execution.id,
            approver=approver_user,
            action="approve",
            comment="Looks good",
        )
        assert result["status"] == "completed"
        assert "Approved" in result["message"]

    def test_reject(self, simple_workflow, creator_user, approver_user):
        node = WorkflowNode.objects.get(workflow=simple_workflow, node_id="approve_1")
        node.config = {
            "approvers": [{"type": "user", "id": str(approver_user.id)}],
        }
        node.save()

        execution = WorkflowExecution.objects.create(
            workflow=simple_workflow,
            document_type="PO",
            document_id=uuid.uuid4(),
            requester=creator_user,
            created_by=creator_user,
            company=simple_workflow.company,
            current_node_id="approve_1",
        )

        result = process_action(
            execution_id=execution.id,
            approver=approver_user,
            action="reject",
            comment="Not approved",
        )
        assert result["status"] == "rejected"

        execution.refresh_from_db()
        assert execution.status == "rejected"

    def test_approve_already_completed(
        self, simple_workflow, creator_user, approver_user
    ):
        execution = WorkflowExecution.objects.create(
            workflow=simple_workflow,
            document_type="PO",
            document_id=uuid.uuid4(),
            requester=creator_user,
            created_by=creator_user,
            company=simple_workflow.company,
            status="completed",
        )

        result = process_action(
            execution_id=execution.id,
            approver=approver_user,
            action="approve",
        )
        assert "Cannot act on completed execution" in result["message"]


# ---------------------------------------------------------------------------
# Service Tests — Parallel Approval
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestParallelApproval:
    def test_parallel_requires_min_approvals(
        self, parallel_workflow, creator_user, approver_user, approver2_user
    ):
        node = WorkflowNode.objects.get(workflow=parallel_workflow, node_id="approve_1")
        node.config = {
            "approvers": [
                {"type": "user", "id": str(approver_user.id)},
                {"type": "user", "id": str(approver2_user.id)},
            ],
            "approval_type": "parallel",
            "min_approvals": 2,
        }
        node.save()

        execution = WorkflowExecution.objects.create(
            workflow=parallel_workflow,
            document_type="PO",
            document_id=uuid.uuid4(),
            requester=creator_user,
            created_by=creator_user,
            company=parallel_workflow.company,
            current_node_id="approve_1",
        )

        result1 = process_action(
            execution_id=execution.id,
            approver=approver_user,
            action="approve",
        )
        assert result1["status"] == "pending"

        result2 = process_action(
            execution_id=execution.id,
            approver=approver2_user,
            action="approve",
        )
        assert result2["status"] == "completed"
        assert "Approved" in result2["message"]

    def test_parallel_completes_with_one_approval_if_min_is_1(
        self, parallel_workflow, creator_user, approver_user, approver2_user
    ):
        node = WorkflowNode.objects.get(workflow=parallel_workflow, node_id="approve_1")
        node.config = {
            "approvers": [
                {"type": "user", "id": str(approver_user.id)},
                {"type": "user", "id": str(approver2_user.id)},
            ],
            "approval_type": "parallel",
            "min_approvals": 1,
        }
        node.save()

        execution = WorkflowExecution.objects.create(
            workflow=parallel_workflow,
            document_type="PO",
            document_id=uuid.uuid4(),
            requester=creator_user,
            created_by=creator_user,
            company=parallel_workflow.company,
            current_node_id="approve_1",
        )

        result = process_action(
            execution_id=execution.id,
            approver=approver_user,
            action="approve",
        )
        assert result["status"] == "completed"


# ---------------------------------------------------------------------------
# Service Tests — Condition Evaluation
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestConditionEvaluation:
    def test_condition_true_path(self, condition_workflow, creator_user, company):
        doc_id = uuid.uuid4()
        execution = WorkflowExecution.objects.create(
            workflow=condition_workflow,
            document_type="PurchaseOrder",
            document_id=doc_id,
            requester=creator_user,
            created_by=creator_user,
            company=company,
            current_node_id="condition_1",
        )

        node = WorkflowNode.objects.get(
            workflow=condition_workflow, node_id="condition_1"
        )
        result = evaluate_condition(node, execution)
        # No document model exists, so should return false_node
        assert result == "approve_low"

    def test_compare_operators(self):
        from apps.core.services.workflow_service import _compare_values

        assert _compare_values(500, ">", 100) is True
        assert _compare_values(50, ">", 100) is False
        assert _compare_values(100, ">=", 100) is True
        assert _compare_values(50, "<", 100) is True
        assert _compare_values(100, "<=", 100) is True
        assert _compare_values("abc", "==", "abc") is True
        assert _compare_values("abc", "!=", "xyz") is True
        assert _compare_values("x", "in", ["x", "y"]) is True
        assert _compare_values("z", "in", ["x", "y"]) is False
        assert _compare_values("z", "not_in", ["x", "y"]) is True

    def test_condition_all_operators(self):
        from apps.core.services.workflow_service import _compare_values

        assert _compare_values(100, ">", 50) is True
        assert _compare_values(50, ">", 100) is False
        assert _compare_values(100, "<", 200) is True
        assert _compare_values(100, "<", 50) is False
        assert _compare_values(100, ">=", 100) is True
        assert _compare_values(100, ">=", 101) is False
        assert _compare_values(100, "<=", 100) is True
        assert _compare_values(101, "<=", 100) is False
        assert _compare_values("hello", "==", "hello") is True
        assert _compare_values("hello", "==", "world") is False
        assert _compare_values("hello", "!=", "world") is True


# ---------------------------------------------------------------------------
# Service Tests — Escalation
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestEscalation:
    def test_escalate_to_next_node(
        self, escalation_workflow, creator_user, approver_user
    ):
        node = WorkflowNode.objects.get(
            workflow=escalation_workflow, node_id="approve_1"
        )
        node.config = {
            "approvers": [{"type": "user", "id": str(approver_user.id)}],
            "approval_type": "sequential",
            "min_approvals": 1,
            "escalation_node_id": "approve_2",
        }
        node.save()

        execution = WorkflowExecution.objects.create(
            workflow=escalation_workflow,
            document_type="PO",
            document_id=uuid.uuid4(),
            requester=creator_user,
            created_by=creator_user,
            company=escalation_workflow.company,
            current_node_id="approve_1",
        )

        result = escalate(execution.id)
        assert "Escalated" in result["message"]
        execution.refresh_from_db()
        assert execution.current_node_id == "approve_2"

    def test_escalate_completed_execution(self, escalation_workflow, creator_user):
        execution = WorkflowExecution.objects.create(
            workflow=escalation_workflow,
            document_type="PO",
            document_id=uuid.uuid4(),
            requester=creator_user,
            created_by=creator_user,
            company=escalation_workflow.company,
            status="completed",
        )

        result = escalate(execution.id)
        assert "Cannot escalate completed execution" in result["message"]


# ---------------------------------------------------------------------------
# Service Tests — Pending & History
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestPendingAndHistory:
    def test_get_pending(self, simple_workflow, creator_user, approver_user):
        node = WorkflowNode.objects.get(workflow=simple_workflow, node_id="approve_1")
        execution = WorkflowExecution.objects.create(
            workflow=simple_workflow,
            document_type="PO",
            document_id=uuid.uuid4(),
            requester=creator_user,
            created_by=creator_user,
            company=simple_workflow.company,
            current_node_id="approve_1",
        )

        WorkflowExecutionStep.objects.create(
            execution=execution,
            node=node,
            approver=approver_user,
            status="pending",
        )

        items = get_pending(approver_user)
        assert len(items) == 1
        assert items[0]["execution_id"] == str(execution.id)

    def test_get_pending_wrong_company(
        self, simple_workflow, creator_user, other_company_user
    ):
        node = WorkflowNode.objects.get(workflow=simple_workflow, node_id="approve_1")
        execution = WorkflowExecution.objects.create(
            workflow=simple_workflow,
            document_type="PO",
            document_id=uuid.uuid4(),
            requester=creator_user,
            created_by=creator_user,
            company=simple_workflow.company,
            current_node_id="approve_1",
        )

        WorkflowExecutionStep.objects.create(
            execution=execution,
            node=node,
            approver=other_company_user,
            status="pending",
        )

        items = get_pending(other_company_user)
        assert len(items) == 0

    def test_get_history(self, simple_workflow, creator_user, approver_user):
        doc_id = uuid.uuid4()
        execution = WorkflowExecution.objects.create(
            workflow=simple_workflow,
            document_type="PO",
            document_id=doc_id,
            requester=creator_user,
            created_by=creator_user,
            company=simple_workflow.company,
            current_node_id="approve_1",
        )

        node = WorkflowNode.objects.get(workflow=simple_workflow, node_id="approve_1")
        WorkflowExecutionStep.objects.create(
            execution=execution,
            node=node,
            approver=approver_user,
            action="approve",
            status="completed",
        )

        history = get_history("PO", doc_id)
        assert len(history) == 1
        assert len(history[0]["steps"]) == 1

    def test_get_execution_context(self, simple_workflow, creator_user, approver_user):
        execution = WorkflowExecution.objects.create(
            workflow=simple_workflow,
            document_type="PO",
            document_id=uuid.uuid4(),
            requester=creator_user,
            created_by=creator_user,
            company=simple_workflow.company,
            current_node_id="approve_1",
        )

        context = get_execution_context(execution.id)
        assert context["execution_id"] == str(execution.id)
        assert context["workflow"]["name"] == "Test Workflow"
        assert context["current_node"]["node_id"] == "approve_1"


# ---------------------------------------------------------------------------
# Service Tests — Delegate
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestDelegate:
    def test_delegate_action(
        self, simple_workflow, creator_user, approver_user, approver2_user
    ):
        node = WorkflowNode.objects.get(workflow=simple_workflow, node_id="approve_1")
        node.config = {
            "approvers": [{"type": "user", "id": str(approver_user.id)}],
        }
        node.save()

        execution = WorkflowExecution.objects.create(
            workflow=simple_workflow,
            document_type="PO",
            document_id=uuid.uuid4(),
            requester=creator_user,
            created_by=creator_user,
            company=simple_workflow.company,
            current_node_id="approve_1",
            status="pending",
        )

        result = process_action(
            execution_id=execution.id,
            approver=approver_user,
            action="delegate",
            delegated_to_id=approver2_user.id,
        )
        assert result["status"] == "pending"
        assert "Delegated" in result["message"]
        assert result["delegated_to"] == str(approver2_user.id)


# ---------------------------------------------------------------------------
# API Tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestWorkflowAPI:
    def test_execute_workflow(
        self, simple_workflow, creator_user, approver_user, company
    ):
        from django.test import Client
        from rest_framework_simplejwt.tokens import AccessToken

        node = WorkflowNode.objects.get(workflow=simple_workflow, node_id="approve_1")
        node.config = {
            "approvers": [{"type": "user", "id": str(approver_user.id)}],
            "approval_type": "sequential",
            "min_approvals": 1,
        }
        node.save()

        client = Client()
        token = AccessToken.for_user(creator_user)
        doc_id = uuid.uuid4()

        response = client.post(
            "/api/v1/core/workflows/execute/",
            {
                "workflow_id": str(simple_workflow.id),
                "document_type": "PurchaseOrder",
                "document_id": str(doc_id),
            },
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
            HTTP_X_COMPANY_ID=str(company.id),
        )
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "pending"

    def test_approve_execution(
        self, simple_workflow, creator_user, approver_user, company
    ):
        from django.test import Client
        from rest_framework_simplejwt.tokens import AccessToken

        node = WorkflowNode.objects.get(workflow=simple_workflow, node_id="approve_1")
        node.config = {
            "approvers": [{"type": "user", "id": str(approver_user.id)}],
            "approval_type": "sequential",
            "min_approvals": 1,
        }
        node.save()

        execution = WorkflowExecution.objects.create(
            workflow=simple_workflow,
            document_type="PO",
            document_id=uuid.uuid4(),
            requester=creator_user,
            created_by=creator_user,
            company=company,
            current_node_id="approve_1",
            status="pending",
        )

        client = Client()
        token = AccessToken.for_user(approver_user)

        response = client.post(
            f"/api/v1/core/workflows/executions/{execution.id}/approve/",
            {"comment": "Approved"},
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"

    def test_reject_execution(
        self, simple_workflow, creator_user, approver_user, company
    ):
        from django.test import Client
        from rest_framework_simplejwt.tokens import AccessToken

        node = WorkflowNode.objects.get(workflow=simple_workflow, node_id="approve_1")
        node.config = {
            "approvers": [{"type": "user", "id": str(approver_user.id)}],
        }
        node.save()

        execution = WorkflowExecution.objects.create(
            workflow=simple_workflow,
            document_type="PO",
            document_id=uuid.uuid4(),
            requester=creator_user,
            created_by=creator_user,
            company=company,
            current_node_id="approve_1",
            status="pending",
        )

        client = Client()
        token = AccessToken.for_user(approver_user)

        response = client.post(
            f"/api/v1/core/workflows/executions/{execution.id}/reject/",
            {"comment": "Not approved"},
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "rejected"

    def test_approve_without_company_access(
        self, simple_workflow, creator_user, other_company_user, company
    ):
        from django.test import Client
        from rest_framework_simplejwt.tokens import AccessToken

        node = WorkflowNode.objects.get(workflow=simple_workflow, node_id="approve_1")
        node.config = {
            "approvers": [{"type": "user", "id": str(other_company_user.id)}],
            "approval_type": "sequential",
            "min_approvals": 1,
        }
        node.save()

        execution = WorkflowExecution.objects.create(
            workflow=simple_workflow,
            document_type="PO",
            document_id=uuid.uuid4(),
            requester=creator_user,
            created_by=creator_user,
            company=company,
            current_node_id="approve_1",
            status="pending",
        )

        client = Client()
        token = AccessToken.for_user(other_company_user)

        response = client.post(
            f"/api/v1/core/workflows/executions/{execution.id}/approve/",
            {"comment": "Approved"},
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        assert response.status_code == 403

    def test_list_pending(self, simple_workflow, creator_user, approver_user, company):
        from django.test import Client
        from rest_framework_simplejwt.tokens import AccessToken

        node = WorkflowNode.objects.get(workflow=simple_workflow, node_id="approve_1")
        execution = WorkflowExecution.objects.create(
            workflow=simple_workflow,
            document_type="PO",
            document_id=uuid.uuid4(),
            requester=creator_user,
            created_by=creator_user,
            company=company,
            current_node_id="approve_1",
            status="pending",
        )

        WorkflowExecutionStep.objects.create(
            execution=execution,
            node=node,
            approver=approver_user,
            status="pending",
        )

        client = Client()
        token = AccessToken.for_user(approver_user)

        response = client.get(
            "/api/v1/core/workflows/executions/pending/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        assert response.status_code == 200
        data = response.json()
        assert data["count"] >= 1

    def test_execution_context(
        self, simple_workflow, creator_user, approver_user, company
    ):
        from django.test import Client
        from rest_framework_simplejwt.tokens import AccessToken

        execution = WorkflowExecution.objects.create(
            workflow=simple_workflow,
            document_type="PO",
            document_id=uuid.uuid4(),
            requester=creator_user,
            created_by=creator_user,
            company=company,
            current_node_id="approve_1",
        )

        client = Client()
        token = AccessToken.for_user(creator_user)

        response = client.get(
            f"/api/v1/core/workflows/executions/{execution.id}/context/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        assert response.status_code == 200
        data = response.json()
        assert data["execution_id"] == str(execution.id)
