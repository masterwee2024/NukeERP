"""Workflow service — approval workflow engine with company-scoped logic."""

import logging
from datetime import datetime
from uuid import UUID

from django.db import transaction
from django.db.models import Model
from django.utils import timezone

from apps.core.models import (
    Channel,
    Company,
    User,
    UserCompany,
    WorkflowDefinition,
    WorkflowEdge,
    WorkflowExecution,
    WorkflowExecutionStep,
    WorkflowNode,
)
from apps.core.services.messaging_service import send_system_message

logger = logging.getLogger(__name__)


def _get_model_for_document(document_type: str) -> type[Model] | None:
    """Resolve document_type string to Django model."""
    try:
        app_label, model_name = document_type.split(".")
        from django.apps import apps

        return apps.get_model(app_label, model_name)
    except (ValueError, LookupError):
        return None


def _get_node(workflow, node_id: str) -> WorkflowNode | None:
    try:
        return WorkflowNode.objects.get(workflow=workflow, node_id=node_id)
    except WorkflowNode.DoesNotExist:
        return None


def _get_start_node(workflow) -> WorkflowNode | None:
    return WorkflowNode.objects.filter(workflow=workflow, node_type="start").first()


def _get_edges_from(workflow, source_node_id: str) -> list[WorkflowEdge]:
    return list(
        WorkflowEdge.objects.filter(workflow=workflow, source_node_id=source_node_id)
    )


def _get_edges_to(workflow, target_node_id: str) -> list[WorkflowEdge]:
    return list(
        WorkflowEdge.objects.filter(workflow=workflow, target_node_id=target_node_id)
    )


def get_user_company_ids(user: User) -> list[UUID]:
    """Return list of company IDs the user has access to."""
    return list(
        UserCompany.objects.filter(user=user).values_list("company_id", flat=True)
    )


def user_has_company_access(user: User, company_id: UUID) -> bool:
    """Check if user has UserCompany access to the given company."""
    if user.is_superuser:
        return True
    return UserCompany.objects.filter(user=user, company_id=company_id).exists()


def _create_pending_steps_for_current_node(execution: WorkflowExecution) -> None:
    """Resolve approvers for current node, create pending steps, and send notifications."""
    if execution.status != "pending" or not execution.current_node_id:
        return

    current_node = _get_node(execution.workflow, execution.current_node_id)
    if not current_node or current_node.node_type != "approve":
        return

    # Delete existing pending steps for this node to avoid duplicates
    WorkflowExecutionStep.objects.filter(
        execution=execution, node=current_node, status="pending"
    ).delete()

    approvers = resolve_approvers(current_node, execution)

    # Import inline to avoid circular import issues
    from apps.core.services.notification_service import send_notification
    from apps.core.tasks import send_approval_email

    for entry in approvers:
        user = entry["user"]

        # Create pending step
        WorkflowExecutionStep.objects.create(
            execution=execution, node=current_node, approver=user, status="pending"
        )

        # Send Notification
        title = f"Approval Required: {execution.document_type}"
        message = (
            f"You have a new approval request for {execution.document_type} "
            f"#{execution.document_id} submitted by {execution.requester.full_name or execution.requester.email}."
        )
        link = f"/app/{execution.workflow.module}/{execution.workflow.document_type.lower()}s"

        send_notification(
            recipient=user,
            slug="approval_request",
            title=title,
            message=message,
            link=link,
            company=execution.company,
        )

        # Dispatch async approval email with secure links
        send_approval_email.delay(str(execution.id), str(user.id))


# ---------------------------------------------------------------------------
# Main service functions
# ---------------------------------------------------------------------------


def resolve_approvers(node: WorkflowNode, execution: WorkflowExecution) -> list[dict]:
    """Get potential approvers for a node.

    Filters by UserCompany access, excludes the creator (creator≠approver).
    Returns list of {user: User, type: str} dicts.
    """
    config = node.config or {}
    approvers_config = config.get("approvers", [])
    if not approvers_config:
        return []

    from django.contrib.auth.models import Group

    candidate_users: list[User] = []
    for entry in approvers_config:
        approver_type = entry.get("type", "user")
        approver_id = entry.get("id")
        if not approver_id:
            continue
        if approver_type == "user":
            try:
                u = User.objects.get(id=approver_id, is_active=True)
                candidate_users.append(u)
            except User.DoesNotExist:
                continue
        elif approver_type == "role":
            try:
                group = Group.objects.get(id=approver_id)
                for u in group.user_set.filter(is_active=True):
                    candidate_users.append(u)
            except Group.DoesNotExist:
                continue

    company_id = execution.company_id
    valid_users = []
    seen = set()
    for u in candidate_users:
        if u.id in seen:
            continue
        seen.add(u.id)
        if u.id == execution.created_by_id:
            continue
        if not user_has_company_access(u, company_id):
            continue
        valid_users.append({"user": u, "type": "user"})

    return valid_users


def create_execution(
    workflow_id: UUID,
    document_type: str,
    document_id: UUID,
    requester: User,
    company_id: UUID,
    created_by: User | None = None,
) -> WorkflowExecution:
    """Create a workflow execution and advance to first actionable node."""
    workflow = WorkflowDefinition.objects.get(id=workflow_id, is_active=True)
    company = Company.objects.get(id=company_id)

    if created_by is None:
        created_by = requester

    execution = WorkflowExecution.objects.create(
        workflow=workflow,
        document_type=document_type,
        document_id=document_id,
        status="pending",
        requester=requester,
        created_by=created_by,
        company=company,
    )

    start_node = _get_start_node(workflow)
    if start_node:
        execution.current_node_id = _advance_past_non_approval_nodes(
            workflow, start_node.node_id, execution
        )

    execution.save(update_fields=["current_node_id"])
    _create_pending_steps_for_current_node(execution)

    _post_approval_system_message(execution, workflow)

    return execution


def _post_approval_system_message(execution, workflow):
    try:
        channel = Channel.objects.filter(
            company=execution.company,
            type="system",
            name__iexact="approvals",
        ).first()
        if not channel:
            return

        pending_steps = WorkflowExecutionStep.objects.filter(
            execution=execution, status="pending"
        ).select_related("approver")

        approver_mentions = " ".join(
            f"@{step.approver.email.split('@')[0]}"
            for step in pending_steps
            if step.approver
        )

        meta = execution.metadata or {}
        doc_number = meta.get("document_number") or str(execution.document_id)[:8]
        send_system_message(
            channel=channel,
            content=f"{approver_mentions} Please approve {execution.document_type} #{doc_number} ({execution.requester.email})",
            link_type="approval",
            link_id=execution.id,
        )
    except Exception as exc:
        logger.warning("System message skipped for execution %s: %s", execution.id, exc)


def _advance_past_non_approval_nodes(
    workflow: WorkflowDefinition,
    from_node_id: str,
    execution: WorkflowExecution,
) -> str:
    """Walk from a node until we find an approve/end node or run out of edges."""
    current_node_id = from_node_id
    visited = set()

    while current_node_id not in visited:
        visited.add(current_node_id)
        node = _get_node(workflow, current_node_id)
        if not node:
            break

        if node.node_type == "approve":
            return current_node_id

        if node.node_type == "end":
            return current_node_id

        if node.node_type == "condition":
            next_id = evaluate_condition(node, execution)
            if next_id:
                current_node_id = next_id
                continue
            break

        if node.node_type in ("start", "notify", "action"):
            edges = _get_edges_from(workflow, current_node_id)
            if edges:
                current_node_id = edges[0].target_node_id
                continue
            break

        break

    return current_node_id


def evaluate_condition(node: WorkflowNode, execution: WorkflowExecution) -> str | None:
    """Evaluate a condition node against the document data.

    Returns target_node_id for true/false branch, or None on error.
    """
    config = node.config or {}
    field = config.get("field")
    operator = config.get("operator")
    value = config.get("value")
    true_node_id = config.get("true_node_id")
    false_node_id = config.get("false_node_id")

    if not all([field, operator, true_node_id, false_node_id]):
        return None

    doc_value = _get_document_field_value(
        execution.document_type, execution.document_id, field
    )
    if doc_value is None:
        return false_node_id

    result = _compare_values(doc_value, operator, value)
    return true_node_id if result else false_node_id


def _get_document_field_value(
    document_type: str, document_id: UUID, field: str
) -> object | None:
    """Fetch a field value from the document model."""
    model = _get_model_for_document(document_type)
    if not model:
        return None
    try:
        obj = model.objects.get(id=document_id)
        return getattr(obj, field, None)
    except model.DoesNotExist:
        return None
    except AttributeError:
        return None
    except Exception:
        return None


def _compare_values(doc_value: object, operator: str, value: object) -> bool:
    """Compare a document field value against a condition value."""
    try:
        if operator == "==":
            return doc_value == value
        elif operator == "!=":
            return doc_value != value
        elif operator == ">":
            return float(doc_value) > float(value)  # type: ignore
        elif operator == "<":
            return float(doc_value) < float(value)  # type: ignore
        elif operator == ">=":
            return float(doc_value) >= float(value)  # type: ignore
        elif operator == "<=":
            return float(doc_value) <= float(value)  # type: ignore
        elif operator == "in":
            if isinstance(value, list):
                return doc_value in value
            return str(doc_value) in str(value)
        elif operator == "not_in":
            if isinstance(value, list):
                return doc_value not in value
            return str(doc_value) not in str(value)
    except (TypeError, ValueError):
        return False
    return False


@transaction.atomic
def process_action(
    execution_id: UUID,
    approver: User,
    action: str,
    comment: str = "",
    ip_address: str | None = None,
    delegated_to_id: UUID | None = None,
) -> dict:
    """Process an approval action (approve/reject/delegate).

    Validates company access, creator≠approver, records step, advances workflow.
    Returns dict with execution info and next steps.
    """
    execution = WorkflowExecution.objects.select_for_update().get(id=execution_id)

    if execution.status != "pending":
        return {
            "execution_id": str(execution.id),
            "status": execution.status,
            "message": f"Cannot act on {execution.status} execution",
        }

    if not user_has_company_access(approver, execution.company_id):
        raise PermissionError("Approver does not have access to this company")

    if approver.id == execution.created_by_id:
        raise PermissionError("Creator cannot approve own transaction")

    current_node = _get_node(execution.workflow, execution.current_node_id)
    if not current_node:
        return {
            "execution_id": str(execution.id),
            "status": execution.status,
            "message": "No current node found",
        }

    # Delete the current approver's pending step
    WorkflowExecutionStep.objects.filter(
        execution=execution, node=current_node, approver=approver, status="pending"
    ).delete()

    step = WorkflowExecutionStep.objects.create(
        execution=execution,
        node=current_node,
        approver=approver,
        action=action,
        comment=comment,
        status="completed",
        ip_address=ip_address,
        delegated_to=(
            User.objects.get(id=delegated_to_id) if delegated_to_id else None
        ),
    )

    if action == "reject":
        execution.status = "rejected"
        execution.completed_at = timezone.now()
        execution.save(update_fields=["status", "completed_at"])
        return {
            "execution_id": str(execution.id),
            "status": "rejected",
            "message": "Transaction rejected",
            "step_id": str(step.id),
        }

    if action == "delegate":
        if not delegated_to_id:
            return {
                "execution_id": str(execution.id),
                "status": execution.status,
                "message": "delegated_to_id is required for delegation",
            }
        if not user_has_company_access(step.delegated_to, execution.company_id):
            raise PermissionError("Delegate does not have access to this company")

        # Create new pending step for the delegate
        WorkflowExecutionStep.objects.create(
            execution=execution,
            node=current_node,
            approver=step.delegated_to,
            status="pending",
        )

        # Notify the delegate
        title = f"Approval Request Delegated: {execution.document_type}"
        message = (
            f"You have been delegated an approval request for {execution.document_type} "
            f"#{execution.document_id} by {approver.full_name or approver.email}."
        )
        link = f"/app/{execution.workflow.module}/{execution.workflow.document_type.lower()}s"

        from apps.core.services.notification_service import send_notification
        from apps.core.tasks import send_approval_email

        send_notification(
            recipient=step.delegated_to,
            slug="approval_request",
            title=title,
            message=message,
            link=link,
            company=execution.company,
        )

        send_approval_email.delay(str(execution.id), str(step.delegated_to.id))

        return {
            "execution_id": str(execution.id),
            "status": execution.status,
            "message": "Delegated to another approver",
            "step_id": str(step.id),
            "delegated_to": str(delegated_to_id),
        }

    if action == "approve":
        node_config = current_node.config or {}
        approval_type = node_config.get("approval_type", "sequential")
        min_approvals = node_config.get("min_approvals", 1)

        if approval_type == "parallel":
            completed_count = WorkflowExecutionStep.objects.filter(
                execution=execution,
                node=current_node,
                action="approve",
                status="completed",
            ).count()

            if completed_count >= min_approvals:
                _advance_to_next_node(execution, current_node)
            else:
                execution.save(update_fields=[])
        else:
            _advance_to_next_node(execution, current_node)

        return {
            "execution_id": str(execution.id),
            "status": execution.status,
            "message": (
                "Approved — transaction completed"
                if execution.status == "completed"
                else "Approved — waiting for next approval"
            ),
            "step_id": str(step.id),
        }

    return {
        "execution_id": str(execution.id),
        "status": execution.status,
        "message": f"Unknown action: {action}",
    }


def _advance_to_next_node(
    execution: WorkflowExecution, current_node: WorkflowNode
) -> None:
    """Advance execution to the next node after approval."""
    edges = _get_edges_from(execution.workflow, current_node.node_id)
    if not edges:
        execution.status = "completed"
        execution.completed_at = timezone.now()
        execution.save(update_fields=["status", "completed_at"])
        return

    next_node_id = _advance_past_non_approval_nodes(
        execution.workflow, edges[0].target_node_id, execution
    )
    execution.refresh_from_db()
    execution.current_node_id = next_node_id

    next_node = _get_node(execution.workflow, next_node_id)
    if next_node and next_node.node_type == "end":
        execution.status = "completed"
        execution.completed_at = timezone.now()
        execution.save(update_fields=["current_node_id", "status", "completed_at"])
    else:
        execution.save(update_fields=["current_node_id"])
        _create_pending_steps_for_current_node(execution)


def escalate(execution_id: UUID) -> dict:
    """Escalate an execution to the next level or mark as escalated."""
    execution = WorkflowExecution.objects.get(id=execution_id)

    if execution.status != "pending":
        return {
            "execution_id": str(execution.id),
            "status": execution.status,
            "message": f"Cannot escalate {execution.status} execution",
        }

    current_node = _get_node(execution.workflow, execution.current_node_id)
    if not current_node:
        return {
            "execution_id": str(execution.id),
            "status": execution.status,
            "message": "No current node found",
        }

    node_config = current_node.config or {}
    escalation_node_id = node_config.get("escalation_node_id")

    if escalation_node_id:
        next_id = _advance_past_non_approval_nodes(
            execution.workflow, escalation_node_id, execution
        )
        execution.current_node_id = next_id
        execution.save(update_fields=["current_node_id"])
        _create_pending_steps_for_current_node(execution)
        return {
            "execution_id": str(execution.id),
            "status": execution.status,
            "message": f"Escalated to node {escalation_node_id}",
        }

    if execution.created_by_id:
        execution.status = "cancelled"
        execution.completed_at = timezone.now()
        execution.save(update_fields=["status", "completed_at"])
        return {
            "execution_id": str(execution.id),
            "status": "cancelled",
            "message": "No escalation path — execution cancelled",
        }

    return {
        "execution_id": str(execution.id),
        "status": execution.status,
        "message": "No escalation path defined",
    }


def get_pending(user: User) -> list[dict]:
    """Get all pending approvals for a user across accessible companies."""
    company_ids = get_user_company_ids(user)

    steps = list(
        WorkflowExecutionStep.objects.filter(
            approver=user,
            status="pending",
            execution__status="pending",
            execution__company_id__in=company_ids,
        ).select_related("execution", "execution__workflow", "node")
    )

    return [
        {
            "step_id": str(s.id),
            "execution_id": str(s.execution_id),
            "workflow_name": s.execution.workflow.name,
            "document_type": s.execution.document_type,
            "document_id": str(s.execution.document_id),
            "node_label": s.node.label if s.node else "",
            "node_type": s.node.node_type if s.node else "",
            "requested_at": s.execution.started_at.isoformat(),
            "requester": (
                {
                    "id": str(s.execution.requester.id),
                    "name": s.execution.requester.full_name,
                    "email": s.execution.requester.email,
                }
                if s.execution.requester
                else None
            ),
            "company_id": str(s.execution.company_id),
        }
        for s in steps
    ]


def get_history(document_type: str, document_id: UUID) -> list[dict]:
    """Get full approval history for a document."""
    executions = WorkflowExecution.objects.filter(
        document_type=document_type, document_id=document_id
    ).order_by("started_at")

    result = []
    for execution in executions:
        steps = (
            WorkflowExecutionStep.objects.filter(execution=execution)
            .select_related("approver", "node")
            .order_by("timestamp")
        )

        result.append(
            {
                "execution_id": str(execution.id),
                "workflow_name": execution.workflow.name,
                "status": execution.status,
                "started_at": execution.started_at.isoformat(),
                "completed_at": (
                    execution.completed_at.isoformat()
                    if execution.completed_at
                    else None
                ),
                "steps": [
                    {
                        "step_id": str(s.id),
                        "node_label": s.node.label if s.node else "",
                        "node_type": s.node.node_type if s.node else "",
                        "approver": (
                            {
                                "id": str(s.approver.id),
                                "name": s.approver.full_name,
                                "email": s.approver.email,
                            }
                            if s.approver
                            else None
                        ),
                        "action": s.action,
                        "comment": s.comment,
                        "status": s.status,
                        "timestamp": s.timestamp.isoformat(),
                        "delegated_to": (
                            {
                                "id": str(s.delegated_to.id),
                                "name": s.delegated_to.full_name,
                            }
                            if s.delegated_to
                            else None
                        ),
                    }
                    for s in steps
                ],
            }
        )

    return result


def get_execution_context(execution_id: UUID) -> dict:
    """Get full execution context including document data and approval history."""
    execution = WorkflowExecution.objects.select_related(
        "workflow", "company", "requester", "created_by"
    ).get(id=execution_id)

    current_node = _get_node(execution.workflow, execution.current_node_id)

    steps = (
        WorkflowExecutionStep.objects.filter(execution=execution)
        .select_related("approver", "node", "delegated_to")
        .order_by("timestamp")
    )

    model = _get_model_for_document(execution.document_type)
    document_data = None
    if model:
        try:
            obj = model.objects.get(id=execution.document_id)
            document_data = _model_to_dict(obj)
        except model.DoesNotExist:
            document_data = None

    return {
        "execution_id": str(execution.id),
        "workflow": {
            "id": str(execution.workflow_id),
            "name": execution.workflow.name,
            "module": execution.workflow.module,
            "document_type": execution.workflow.document_type,
        },
        "document_type": execution.document_type,
        "document_id": str(execution.document_id),
        "document_data": document_data,
        "status": execution.status,
        "current_node": {
            "node_id": current_node.node_id if current_node else None,
            "label": current_node.label if current_node else "",
            "node_type": current_node.node_type if current_node else "",
        },
        "requester": {
            "id": str(execution.requester.id) if execution.requester else None,
            "name": execution.requester.full_name if execution.requester else "",
            "email": execution.requester.email if execution.requester else "",
        },
        "created_by": {
            "id": str(execution.created_by.id) if execution.created_by else None,
            "name": execution.created_by.full_name if execution.created_by else "",
            "email": execution.created_by.email if execution.created_by else "",
        },
        "company": {
            "id": str(execution.company_id),
            "name": execution.company.name,
        },
        "started_at": execution.started_at.isoformat(),
        "completed_at": (
            execution.completed_at.isoformat() if execution.completed_at else None
        ),
        "steps": [
            {
                "step_id": str(s.id),
                "node_label": s.node.label if s.node else "",
                "node_type": s.node.node_type if s.node else "",
                "approver": (
                    {
                        "id": str(s.approver.id),
                        "name": s.approver.full_name or s.approver.email,
                    }
                    if s.approver
                    else None
                ),
                "action": s.action,
                "comment": s.comment,
                "status": s.status,
                "timestamp": s.timestamp.isoformat(),
                "delegated_to": (
                    {
                        "id": str(s.delegated_to.id),
                        "name": s.delegated_to.full_name or s.delegated_to.email,
                    }
                    if s.delegated_to
                    else None
                ),
            }
            for s in steps
        ],
        "metadata": execution.metadata,
    }


def _model_to_dict(obj: Model) -> dict:
    """Convert a Django model instance to a dict."""

    result = {}
    for field in obj._meta.fields:
        name = field.name
        value = getattr(obj, name)
        if isinstance(value, UUID):
            result[name] = str(value)
        elif isinstance(value, datetime):
            result[name] = value.isoformat()
        elif hasattr(value, "pk"):
            result[name] = str(value.pk) if value else None
        else:
            result[name] = value
    return result
