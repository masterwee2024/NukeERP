"""Centralized Approval Center API — T016c.

Provides cross-module, company-scoped pending approvals with quick actions and stats.
"""

from datetime import timedelta
from uuid import UUID

from django.db import transaction
from django.db.models import Count, ExpressionWrapper, F, fields
from django.utils import timezone
from ninja import Router, Schema
from ninja.errors import HttpError

from apps.core.api.auth import JWTAuth
from apps.core.models import (
    User,
    WorkflowExecution,
    WorkflowExecutionStep,
)
from apps.core.services.workflow_service import (
    get_execution_context,
    get_user_company_ids,
    process_action,
    user_has_company_access,
)

router = Router(auth=JWTAuth())

# ---------------------------------------------------------------------------
# Response Schemas
# ---------------------------------------------------------------------------


class RequesterBrief(Schema):
    id: str | None = None
    name: str = ""
    email: str = ""


class PendingApprovalItem(Schema):
    execution_id: str
    step_id: str
    document_type: str
    document_id: str
    document_number: str
    workflow_name: str
    module: str
    requester: RequesterBrief | None = None
    company_id: str
    company_name: str
    created_at: str
    overdue: bool


class PendingApprovalListOut(Schema):
    count: int
    results: list[PendingApprovalItem]


class ApprovalContextOut(Schema):
    execution_id: str
    workflow: dict
    document_type: str
    document_id: str
    document_data: dict | None = None
    status: str
    current_node: dict
    requester: RequesterBrief | None = None
    created_by: RequesterBrief | None = None
    company: dict
    started_at: str
    completed_at: str | None = None
    steps: list[dict]
    metadata: dict


class QuickActionRequest(Schema):
    comment: str = ""


class RejectRequest(Schema):
    comment: str


class DelegateRequest(Schema):
    delegated_to_id: UUID
    comment: str = ""


class ActionOut(Schema):
    execution_id: str
    status: str
    message: str = ""
    step_id: str | None = None
    delegated_to: str | None = None


class ModuleStats(Schema):
    module: str
    document_type: str
    count: int


class ApprovalStatsOut(Schema):
    total_pending: int
    overdue_count: int
    avg_resolution_hours: float | None = None
    by_module: list[ModuleStats]


class ErrorResponse(Schema):
    detail: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_OVERDUE_HOURS = 48  # default SLA threshold


def _get_company_ids(user: User) -> list[UUID]:
    """Return company IDs the user has access to."""
    return get_user_company_ids(user)


def _is_overdue(started_at) -> bool:
    """True if started_at is older than the SLA threshold."""
    return (timezone.now() - started_at) > timedelta(hours=_OVERDUE_HOURS)


def _build_document_number(execution: WorkflowExecution) -> str:
    """Return a human-readable document number from metadata or short UUID."""
    meta = execution.metadata or {}
    return (
        meta.get("document_number")
        or meta.get("reference")
        or str(execution.document_id)[:8].upper()
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get(
    "/",
    response={200: PendingApprovalListOut},
    summary="List all pending approvals for the current user",
)
def list_pending_approvals(
    request,
    module: str | None = None,
    document_type: str | None = None,
):
    """
    Returns all pending approval steps assigned to the current user,
    filtered by their accessible companies (company-scoped).
    """
    user: User = request.auth
    company_ids = _get_company_ids(user)

    steps_qs = (
        WorkflowExecutionStep.objects.filter(
            approver=user,
            status="pending",
            execution__status="pending",
            execution__company_id__in=company_ids,
        )
        .select_related(
            "execution",
            "execution__workflow",
            "execution__company",
            "execution__requester",
        )
        .order_by("execution__started_at")
    )

    if module:
        steps_qs = steps_qs.filter(execution__workflow__module=module)
    if document_type:
        steps_qs = steps_qs.filter(execution__document_type=document_type)

    results = []
    for step in steps_qs:
        ex = step.execution
        results.append(
            PendingApprovalItem(
                execution_id=str(ex.id),
                step_id=str(step.id),
                document_type=ex.document_type,
                document_id=str(ex.document_id),
                document_number=_build_document_number(ex),
                workflow_name=ex.workflow.name,
                module=ex.workflow.module,
                requester=(
                    RequesterBrief(
                        id=str(ex.requester.id),
                        name=ex.requester.full_name or ex.requester.email,
                        email=ex.requester.email,
                    )
                    if ex.requester
                    else None
                ),
                company_id=str(ex.company_id),
                company_name=ex.company.name,
                created_at=ex.started_at.isoformat(),
                overdue=_is_overdue(ex.started_at),
            )
        )

    return 200, {"count": len(results), "results": results}


@router.get(
    "/{execution_id}/context/",
    response={200: ApprovalContextOut, 404: ErrorResponse},
    summary="Get full document context + history + workflow info",
)
def get_approval_context(request, execution_id: UUID):
    """Return full execution context for displaying in ApprovalContextPanel."""
    try:
        ctx = get_execution_context(execution_id)
    except WorkflowExecution.DoesNotExist:
        raise HttpError(404, "Execution not found") from None

    return 200, ApprovalContextOut(**ctx)


@router.post(
    "/{execution_id}/quick-approve/",
    response={
        200: ActionOut,
        403: ErrorResponse,
        404: ErrorResponse,
        409: ErrorResponse,
    },
    summary="Quick-approve with optional comment",
)
def quick_approve(request, execution_id: UUID, payload: QuickActionRequest):
    """Approve the pending step for the current user on this execution."""
    user: User = request.auth
    try:
        with transaction.atomic():
            result = process_action(
                execution_id=execution_id,
                approver=user,
                action="approve",
                comment=payload.comment,
                ip_address=request.META.get("REMOTE_ADDR"),
            )
    except PermissionError as exc:
        raise HttpError(403, str(exc)) from exc
    except WorkflowExecution.DoesNotExist:
        raise HttpError(404, "Execution not found") from None

    return 200, ActionOut(**result)


@router.post(
    "/{execution_id}/quick-reject/",
    response={
        200: ActionOut,
        403: ErrorResponse,
        404: ErrorResponse,
        409: ErrorResponse,
        422: ErrorResponse,
    },
    summary="Quick-reject — comment required",
)
def quick_reject(request, execution_id: UUID, payload: RejectRequest):
    """Reject the pending step. Comment is mandatory."""
    if not payload.comment or not payload.comment.strip():
        raise HttpError(422, "Comment is required for rejection")

    user: User = request.auth
    try:
        with transaction.atomic():
            result = process_action(
                execution_id=execution_id,
                approver=user,
                action="reject",
                comment=payload.comment,
                ip_address=request.META.get("REMOTE_ADDR"),
            )
    except PermissionError as exc:
        raise HttpError(403, str(exc)) from exc
    except WorkflowExecution.DoesNotExist:
        raise HttpError(404, "Execution not found") from None

    return 200, ActionOut(**result)


@router.post(
    "/{execution_id}/delegate/",
    response={
        200: ActionOut,
        403: ErrorResponse,
        404: ErrorResponse,
    },
    summary="Delegate approval to another user",
)
def delegate_approval(request, execution_id: UUID, payload: DelegateRequest):
    """Delegate the pending step to another user within the same company."""
    user: User = request.auth

    # Verify delegate exists and has company access
    try:
        ex = WorkflowExecution.objects.select_related("company").get(id=execution_id)
    except WorkflowExecution.DoesNotExist:
        raise HttpError(404, "Execution not found") from None

    if not user_has_company_access(user, ex.company_id):
        raise HttpError(403, "You do not have access to this company")

    try:
        delegate_user = User.objects.get(id=payload.delegated_to_id, is_active=True)
    except User.DoesNotExist:
        raise HttpError(404, "Delegate user not found") from None

    if not user_has_company_access(delegate_user, ex.company_id):
        raise HttpError(403, "Delegate does not have access to this company")

    try:
        with transaction.atomic():
            result = process_action(
                execution_id=execution_id,
                approver=user,
                action="delegate",
                comment=payload.comment,
                ip_address=request.META.get("REMOTE_ADDR"),
                delegated_to_id=payload.delegated_to_id,
            )
    except PermissionError as exc:
        raise HttpError(403, str(exc)) from exc
    except WorkflowExecution.DoesNotExist:
        raise HttpError(404, "Execution not found") from None

    return 200, ActionOut(**result)


@router.get(
    "/stats/",
    response={200: ApprovalStatsOut},
    summary="Approval statistics — counts, overdue, avg resolution time",
)
def approval_stats(request):
    """
    Returns:
    - total_pending: total pending items for the current user
    - overdue_count: items older than 48 hours
    - avg_resolution_hours: average resolution time over last 30 days
    - by_module: breakdown by module/document_type
    """
    user: User = request.auth
    company_ids = _get_company_ids(user)
    overdue_threshold = timezone.now() - timedelta(hours=_OVERDUE_HOURS)
    thirty_days_ago = timezone.now() - timedelta(days=30)

    pending_steps = WorkflowExecutionStep.objects.filter(
        approver=user,
        status="pending",
        execution__status="pending",
        execution__company_id__in=company_ids,
    ).select_related("execution", "execution__workflow")

    total_pending = pending_steps.count()

    overdue_count = pending_steps.filter(
        execution__started_at__lt=overdue_threshold
    ).count()

    # Average resolution time for last 30 days (completed/rejected executions)
    resolved_qs = WorkflowExecution.objects.filter(
        company_id__in=company_ids,
        status__in=["completed", "rejected"],
        completed_at__gte=thirty_days_ago,
        completed_at__isnull=False,
    ).annotate(
        resolution_seconds=ExpressionWrapper(
            F("completed_at") - F("started_at"),
            output_field=fields.DurationField(),
        )
    )

    avg_resolution_hours: float | None = None
    if resolved_qs.exists():
        total_seconds = sum(
            (
                ex.resolution_seconds.total_seconds()
                for ex in resolved_qs
                if ex.resolution_seconds is not None
            ),
            0.0,
        )
        count = resolved_qs.count()
        if count > 0:
            avg_resolution_hours = round(total_seconds / count / 3600, 2)

    # Breakdown by module + document_type
    by_module_raw = (
        pending_steps.values("execution__workflow__module", "execution__document_type")
        .annotate(count=Count("id"))
        .order_by("-count")
    )
    by_module = [
        ModuleStats(
            module=row["execution__workflow__module"],
            document_type=row["execution__document_type"],
            count=row["count"],
        )
        for row in by_module_raw
    ]

    return 200, ApprovalStatsOut(
        total_pending=total_pending,
        overdue_count=overdue_count,
        avg_resolution_hours=avg_resolution_hours,
        by_module=by_module,
    )
