"""Approval Workflow Policy API (T016d) — CRUD + test mode."""

from datetime import datetime
from uuid import UUID

from ninja import Router, Schema
from ninja.errors import HttpError

from apps.core.api.auth import JWTAuth
from apps.core.models import ApprovalPolicy, Company, WorkflowDefinition
from apps.core.services.policy_service import resolve_workflow

router = Router(auth=JWTAuth())


class ErrorResponse(Schema):
    detail: str


class PolicyOut(Schema):
    id: str
    name: str
    workflow_id: str
    workflow_name: str = ""
    module: str
    document_type: str
    conditions: list = []
    priority: int
    is_active: bool
    company_id: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @staticmethod
    def resolve_id(obj):
        return str(obj.id)

    @staticmethod
    def resolve_workflow_id(obj):
        return str(obj.workflow_id)

    @staticmethod
    def resolve_workflow_name(obj):
        return obj.workflow.name if obj.workflow_id else ""

    @staticmethod
    def resolve_company_id(obj):
        return str(obj.company_id) if obj.company_id else None


class PolicyCreateIn(Schema):
    name: str
    workflow_id: UUID
    module: str
    document_type: str
    conditions: list = []
    priority: int = 100
    is_active: bool = True
    company_id: UUID | None = None


class PolicyUpdateIn(Schema):
    name: str | None = None
    workflow_id: UUID | None = None
    conditions: list | None = None
    priority: int | None = None
    is_active: bool | None = None


class PolicyListOut(Schema):
    count: int
    results: list[PolicyOut]


class TestPolicyIn(Schema):
    module: str
    document_type: str
    document_data: dict = {}
    company_id: UUID | None = None


class TestPolicyOut(Schema):
    matched: bool
    policy_name: str | None = None
    workflow_name: str | None = None
    workflow_id: str | None = None


@router.get("/", response={200: PolicyListOut})
def list_policies(
    request,
    module: str | None = None,
    document_type: str | None = None,
    company_id: UUID | None = None,
):
    """List approval policies with optional filters."""
    qs = (
        ApprovalPolicy.objects.select_related("workflow")
        .all()
        .order_by("module", "document_type", "priority", "name")
    )
    if module:
        qs = qs.filter(module=module)
    if document_type:
        qs = qs.filter(document_type=document_type)
    if company_id:
        qs = qs.filter(company_id=company_id)

    items = list(qs)
    return {"count": len(items), "results": items}


@router.post("/", response={201: PolicyOut, 400: ErrorResponse, 404: ErrorResponse})
def create_policy(request, payload: PolicyCreateIn):
    """Create an approval policy."""
    workflow = WorkflowDefinition.objects.filter(
        id=payload.workflow_id, is_active=True
    ).first()
    if not workflow:
        raise HttpError(404, "Workflow not found")

    company = None
    if payload.company_id:
        company = Company.objects.filter(id=payload.company_id).first()
        if not company:
            raise HttpError(400, "Company not found")

    policy = ApprovalPolicy.objects.create(
        name=payload.name,
        workflow=workflow,
        module=payload.module,
        document_type=payload.document_type,
        conditions=payload.conditions,
        priority=payload.priority,
        is_active=payload.is_active,
        company=company,
    )
    return 201, policy


@router.put("/{policy_id}/", response={200: PolicyOut, 404: ErrorResponse})
def update_policy(request, policy_id: UUID, payload: PolicyUpdateIn):
    """Update an approval policy."""
    try:
        policy = ApprovalPolicy.objects.select_related("workflow").get(id=policy_id)
    except ApprovalPolicy.DoesNotExist:
        raise HttpError(404, "Policy not found") from None

    update_data = payload.model_dump(exclude_unset=True, exclude_none=True)

    if "workflow_id" in update_data:
        workflow = WorkflowDefinition.objects.filter(
            id=update_data["workflow_id"]
        ).first()
        if not workflow:
            raise HttpError(404, "Workflow not found")
        policy.workflow = workflow
        del update_data["workflow_id"]

    for field, value in update_data.items():
        setattr(policy, field, value)

    policy.save()
    return policy


@router.delete("/{policy_id}/", response={200: dict, 404: ErrorResponse})
def delete_policy(request, policy_id: UUID):
    """Soft-delete (deactivate) an approval policy."""
    try:
        policy = ApprovalPolicy.objects.get(id=policy_id)
    except ApprovalPolicy.DoesNotExist:
        raise HttpError(404, "Policy not found") from None

    policy.is_active = False
    policy.save()
    return {"detail": f"Policy '{policy.name}' deactivated"}


@router.post("/test-match/", response={200: TestPolicyOut, 400: ErrorResponse})
def test_policy(request, payload: TestPolicyIn):
    """Test which policy/worflow would be selected for given document data."""
    if not payload.document_data:
        raise HttpError(400, "document_data is required")

    workflow = resolve_workflow(
        module=payload.module,
        document_type=payload.document_type,
        document_data=payload.document_data,
        company_id=payload.company_id,
    )

    if workflow:
        return {
            "matched": True,
            "policy_name": None,
            "workflow_name": workflow.name,
            "workflow_id": str(workflow.id),
        }

    return {
        "matched": False,
        "policy_name": None,
        "workflow_name": None,
        "workflow_id": None,
    }
