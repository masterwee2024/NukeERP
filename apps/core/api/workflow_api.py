"""Approval Workflow API endpoints (T016)."""

from uuid import UUID

from django.db import transaction
from django.db.models import Q
from ninja import Router, Schema
from ninja.errors import HttpError

from apps.core.api.auth import JWTAuth
from apps.core.mixins.models import ConcurrencyError
from apps.core.models import (
    Company,
    WorkflowDefinition,
    WorkflowEdge,
    WorkflowExecution,
    WorkflowNode,
)
from apps.core.services.workflow_service import (
    create_execution,
    get_execution_context,
    get_history,
    get_pending,
    process_action,
)

# Execution-facing router — non-admin endpoints for submitting/approving
execution_router = Router(auth=JWTAuth())

# Admin router — CRUD for workflow definitions
admin_router = Router(auth=JWTAuth())

router = execution_router


# --- Schemas ---


class ErrorResponse(Schema):
    detail: str


class ExecuteRequest(Schema):
    workflow_id: UUID
    document_type: str
    document_id: UUID


class ExecuteResponse(Schema):
    execution_id: str
    status: str
    current_node_id: str | None = None
    message: str = ""


class ActionRequest(Schema):
    comment: str = ""


class DelegateRequest(Schema):
    delegated_to_id: UUID
    comment: str = ""


class ActionResponse(Schema):
    execution_id: str
    status: str
    message: str = ""
    step_id: str | None = None
    delegated_to: str | None = None


class PendingItem(Schema):
    step_id: str
    execution_id: str
    workflow_name: str
    document_type: str
    document_id: str
    node_label: str
    node_type: str
    requested_at: str
    requester: dict | None = None
    company_id: str


class PendingResponse(Schema):
    count: int
    results: list[PendingItem]


class NodeSchema(Schema):
    node_id: str | None = None
    label: str = ""
    node_type: str = ""


class UserBrief(Schema):
    id: str | None = None
    name: str = ""
    email: str = ""


class CompanyBrief(Schema):
    id: str
    name: str


class StepSchema(Schema):
    step_id: str
    node_label: str
    node_type: str
    approver: UserBrief | None = None
    action: str
    comment: str
    status: str
    timestamp: str
    delegated_to: UserBrief | None = None


class ExecutionContextResponse(Schema):
    execution_id: str
    workflow: dict
    document_type: str
    document_id: str
    document_data: dict | None = None
    status: str
    current_node: NodeSchema
    requester: UserBrief | None = None
    created_by: UserBrief | None = None
    company: CompanyBrief
    started_at: str
    completed_at: str | None = None
    steps: list[StepSchema]
    metadata: dict = {}


class HistoryStep(Schema):
    step_id: str
    node_label: str
    node_type: str
    approver: UserBrief | None = None
    action: str
    comment: str
    status: str
    timestamp: str
    delegated_to: UserBrief | None = None


class HistoryExecution(Schema):
    execution_id: str
    workflow_name: str
    status: str
    started_at: str
    completed_at: str | None = None
    steps: list[HistoryStep]


class WorkflowNodeSchema(Schema):
    node_id: str
    node_type: str
    label: str = ""
    position_x: float = 0
    position_y: float = 0
    config: dict = {}


class WorkflowEdgeSchema(Schema):
    source_node_id: str
    target_node_id: str
    label: str = ""
    condition: dict = {}


class WorkflowCreateRequest(Schema):
    name: str
    module: str
    document_type: str
    company_id: UUID | None = None
    is_global_template: bool = False
    flow_data: dict = {}
    nodes: list[WorkflowNodeSchema] = []
    edges: list[WorkflowEdgeSchema] = []


class WorkflowUpdateRequest(Schema):
    name: str | None = None
    module: str | None = None
    document_type: str | None = None
    is_active: bool | None = None
    flow_data: dict | None = None
    nodes: list[WorkflowNodeSchema] | None = None
    edges: list[WorkflowEdgeSchema] | None = None


class WorkflowResponse(Schema):
    id: str
    name: str
    module: str
    document_type: str
    version: int
    is_active: bool
    company_id: str | None = None
    is_global_template: bool
    created_by_id: str | None = None
    flow_data: dict = {}
    nodes: list[WorkflowNodeSchema] | None = None
    edges: list[WorkflowEdgeSchema] | None = None
    created_at: str | None = None
    updated_at: str | None = None


class CloneRequest(Schema):
    company_id: UUID


# --- Helpers ---


def _get_company_id(request) -> UUID | None:
    company_id = request.headers.get("X-Company-Id")
    if company_id:
        try:
            return UUID(company_id)
        except (ValueError, AttributeError):
            pass
    return None


# --- Execution Endpoints ---


@execution_router.post(
    "/execute/",
    response={
        201: ExecuteResponse,
        400: ErrorResponse,
        404: ErrorResponse,
        403: ErrorResponse,
    },
)
def execute_workflow(request, payload: ExecuteRequest):
    """Start a workflow execution (submit for approval)."""
    company_id = _get_company_id(request)
    if not company_id:
        raise HttpError(400, "X-Company-Id header is required")

    try:
        workflow = WorkflowDefinition.objects.get(
            id=payload.workflow_id, is_active=True
        )
        if workflow.company_id and workflow.company_id != company_id:
            raise HttpError(404, "Workflow not found")
    except WorkflowDefinition.DoesNotExist:
        raise HttpError(404, "Workflow not found") from None

    execution = create_execution(
        workflow_id=payload.workflow_id,
        document_type=payload.document_type,
        document_id=payload.document_id,
        requester=request.auth,
        company_id=company_id,
        created_by=request.auth,
    )

    return 201, {
        "execution_id": str(execution.id),
        "status": execution.status,
        "current_node_id": execution.current_node_id or None,
        "message": "Execution created",
    }


@execution_router.post(
    "/executions/{execution_id}/approve/",
    response={
        200: ActionResponse,
        400: ErrorResponse,
        403: ErrorResponse,
        404: ErrorResponse,
    },
)
def approve_execution(request, execution_id: UUID, payload: ActionRequest):
    """Approve a pending execution step."""
    try:
        result = process_action(
            execution_id=execution_id,
            approver=request.auth,
            action="approve",
            comment=payload.comment,
            ip_address=request.META.get("REMOTE_ADDR"),
        )
        return 200, ActionResponse(**result)
    except PermissionError as e:
        raise HttpError(403, str(e)) from e
    except WorkflowExecution.DoesNotExist:
        raise HttpError(404, "Execution not found") from None


@execution_router.post(
    "/executions/{execution_id}/reject/",
    response={
        200: ActionResponse,
        400: ErrorResponse,
        403: ErrorResponse,
        404: ErrorResponse,
    },
)
def reject_execution(request, execution_id: UUID, payload: ActionRequest):
    """Reject a pending execution."""
    if not payload.comment:
        raise HttpError(400, "Comment is required for rejection")

    try:
        result = process_action(
            execution_id=execution_id,
            approver=request.auth,
            action="reject",
            comment=payload.comment,
            ip_address=request.META.get("REMOTE_ADDR"),
        )
        return 200, ActionResponse(**result)
    except PermissionError as e:
        raise HttpError(403, str(e)) from e
    except WorkflowExecution.DoesNotExist:
        raise HttpError(404, "Execution not found") from None


@execution_router.post(
    "/executions/{execution_id}/delegate/",
    response={
        200: ActionResponse,
        400: ErrorResponse,
        403: ErrorResponse,
        404: ErrorResponse,
    },
)
def delegate_execution(request, execution_id: UUID, payload: DelegateRequest):
    """Delegate a pending approval to another user."""
    try:
        result = process_action(
            execution_id=execution_id,
            approver=request.auth,
            action="delegate",
            comment=payload.comment,
            ip_address=request.META.get("REMOTE_ADDR"),
            delegated_to_id=payload.delegated_to_id,
        )
        return 200, ActionResponse(**result)
    except PermissionError as e:
        raise HttpError(403, str(e)) from e
    except WorkflowExecution.DoesNotExist:
        raise HttpError(404, "Execution not found") from None


@execution_router.get(
    "/executions/pending/",
    response={200: PendingResponse},
)
def list_pending(request):
    """Get all pending approvals for the current user."""
    items = get_pending(request.auth)
    return 200, {"count": len(items), "results": [PendingItem(**i) for i in items]}


@execution_router.get(
    "/executions/{execution_id}/context/",
    response={200: ExecutionContextResponse, 404: ErrorResponse},
)
def execution_context(request, execution_id: UUID):
    """Get full execution context for approval."""
    try:
        context = get_execution_context(execution_id)
        return 200, ExecutionContextResponse(**context)
    except WorkflowExecution.DoesNotExist:
        raise HttpError(404, "Execution not found") from None


@execution_router.get(
    "/history/{document_type}/{document_id}/",
    response={200: list[HistoryExecution]},
)
def approval_history(request, document_type: str, document_id: UUID):
    """Get approval history for a document."""
    history = get_history(document_type, document_id)
    return 200, [HistoryExecution(**h) for h in history]


# --- Admin Workflow CRUD ---


class AdminWorkflowListResponse(Schema):
    count: int
    results: list[WorkflowResponse]


@admin_router.get(
    "/workflows/",
    response={200: AdminWorkflowListResponse},
)
def list_workflows(
    request,
    module: str | None = None,
    document_type: str | None = None,
    company_id: UUID | None = None,
):
    """List workflow definitions."""
    qs = (
        WorkflowDefinition.objects.all()
        .select_related("company")
        .order_by("module", "document_type", "name")
    )
    if module:
        qs = qs.filter(module=module)
    if document_type:
        qs = qs.filter(document_type=document_type)
    if company_id:
        qs = qs.filter(company_id=company_id)
    else:
        request_company = _get_company_id(request)
        if request_company:
            qs = qs.filter(Q(company_id=request_company) | Q(company__isnull=True))

    items = list(qs)
    results = [_workflow_to_response(w) for w in items]
    return 200, {"count": len(results), "results": results}


@admin_router.post(
    "/workflows/",
    response={201: WorkflowResponse, 400: ErrorResponse, 403: ErrorResponse},
)
def create_workflow(request, payload: WorkflowCreateRequest):
    """Create a new workflow definition with nodes and edges."""
    company_id = payload.company_id or _get_company_id(request)

    company = None
    if company_id and not payload.is_global_template:
        company = Company.objects.filter(id=company_id).first()
        if not company:
            raise HttpError(400, "Company not found")

    with transaction.atomic():
        workflow = WorkflowDefinition.objects.create(
            name=payload.name,
            module=payload.module,
            document_type=payload.document_type,
            flow_data=payload.flow_data,
            company=company,
            is_global_template=payload.is_global_template,
            created_by=request.auth,
        )

        for node_data in payload.nodes:
            WorkflowNode.objects.create(
                workflow=workflow,
                node_id=node_data.node_id,
                node_type=node_data.node_type,
                label=node_data.label,
                position_x=node_data.position_x,
                position_y=node_data.position_y,
                config=node_data.config,
            )

        for edge_data in payload.edges:
            WorkflowEdge.objects.create(
                workflow=workflow,
                source_node_id=edge_data.source_node_id,
                target_node_id=edge_data.target_node_id,
                label=edge_data.label,
                condition=edge_data.condition,
            )

    return 201, _workflow_to_response(workflow)


@admin_router.get(
    "/workflows/{workflow_id}/",
    response={200: WorkflowResponse, 404: ErrorResponse},
)
def get_workflow(request, workflow_id: UUID):
    """Get a workflow definition with nodes and edges."""
    try:
        workflow = WorkflowDefinition.objects.select_related("company").get(
            id=workflow_id
        )
        return 200, _workflow_to_response(workflow)
    except WorkflowDefinition.DoesNotExist:
        raise HttpError(404, "Workflow not found") from None


@admin_router.put(
    "/workflows/{workflow_id}/",
    response={200: WorkflowResponse, 400: ErrorResponse, 404: ErrorResponse},
)
def update_workflow(request, workflow_id: UUID, payload: WorkflowUpdateRequest):
    """Update a workflow definition."""
    try:
        workflow = WorkflowDefinition.objects.select_related("company").get(
            id=workflow_id
        )
    except WorkflowDefinition.DoesNotExist:
        raise HttpError(404, "Workflow not found") from None

    with transaction.atomic():
        update_data = payload.model_dump(exclude_unset=True, exclude_none=True)
        nodes = update_data.pop("nodes", None)
        edges = update_data.pop("edges", None)

        for field, value in update_data.items():
            workflow.set_field(field, value)

        try:
            workflow.version += 1
            workflow.save()
        except ConcurrencyError as e:
            raise HttpError(409, str(e)) from e

        if nodes is not None:
            WorkflowNode.objects.filter(workflow=workflow).delete()
            for node_data in nodes:
                WorkflowNode.objects.create(
                    workflow=workflow,
                    node_id=node_data["node_id"],
                    node_type=node_data["node_type"],
                    label=node_data.get("label", ""),
                    position_x=node_data.get("position_x", 0),
                    position_y=node_data.get("position_y", 0),
                    config=node_data.get("config", {}),
                )

        if edges is not None:
            WorkflowEdge.objects.filter(workflow=workflow).delete()
            for edge_data in edges:
                WorkflowEdge.objects.create(
                    workflow=workflow,
                    source_node_id=edge_data["source_node_id"],
                    target_node_id=edge_data["target_node_id"],
                    label=edge_data.get("label", ""),
                    condition=edge_data.get("condition", {}),
                )

    return 200, _workflow_to_response(workflow)


@admin_router.post(
    "/workflows/{workflow_id}/clone/",
    response={201: WorkflowResponse, 400: ErrorResponse, 404: ErrorResponse},
)
def clone_workflow(request, workflow_id: UUID, payload: CloneRequest):
    """Clone a workflow to a specific company."""
    try:
        source = WorkflowDefinition.objects.select_related("company").get(
            id=workflow_id
        )
    except WorkflowDefinition.DoesNotExist:
        raise HttpError(404, "Workflow not found") from None

    company = Company.objects.filter(id=payload.company_id).first()
    if not company:
        raise HttpError(400, "Company not found")

    with transaction.atomic():
        clone = WorkflowDefinition.objects.create(
            name=source.name,
            module=source.module,
            document_type=source.document_type,
            flow_data=source.flow_data,
            company=company,
            is_global_template=False,
            created_by=request.auth,
        )

        for node in WorkflowNode.objects.filter(workflow=source):
            WorkflowNode.objects.create(
                workflow=clone,
                node_id=node.node_id,
                node_type=node.node_type,
                label=node.label,
                position_x=node.position_x,
                position_y=node.position_y,
                config=node.config,
            )

        for edge in WorkflowEdge.objects.filter(workflow=source):
            WorkflowEdge.objects.create(
                workflow=clone,
                source_node_id=edge.source_node_id,
                target_node_id=edge.target_node_id,
                label=edge.label,
                condition=edge.condition,
            )

    return 201, _workflow_to_response(clone)


# --- Helpers ---


def _workflow_to_response(workflow: WorkflowDefinition) -> dict:
    nodes = WorkflowNode.objects.filter(workflow=workflow).order_by("node_id")
    edges = WorkflowEdge.objects.filter(workflow=workflow).order_by(
        "source_node_id", "target_node_id"
    )
    return {
        "id": str(workflow.id),
        "name": workflow.name,
        "module": workflow.module,
        "document_type": workflow.document_type,
        "version": workflow.version,
        "is_active": workflow.is_active,
        "company_id": str(workflow.company_id) if workflow.company_id else None,
        "is_global_template": workflow.is_global_template,
        "created_by_id": (
            str(workflow.created_by_id) if workflow.created_by_id else None
        ),
        "flow_data": workflow.flow_data,
        "nodes": [
            {
                "node_id": n.node_id,
                "node_type": n.node_type,
                "label": n.label,
                "position_x": n.position_x,
                "position_y": n.position_y,
                "config": n.config,
            }
            for n in nodes
        ],
        "edges": [
            {
                "source_node_id": e.source_node_id,
                "target_node_id": e.target_node_id,
                "label": e.label,
                "condition": e.condition,
            }
            for e in edges
        ],
        "created_at": workflow.created_at.isoformat() if workflow.created_at else None,
        "updated_at": workflow.updated_at.isoformat() if workflow.updated_at else None,
    }
