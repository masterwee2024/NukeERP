"""Audit log API — read-only list/detail with filters."""

from uuid import UUID

from django.db.models import Q
from ninja import Router, Schema
from ninja.errors import HttpError

from apps.core.models import AuditLog

router = Router()


class AuditLogOut(Schema):
    id: str
    model_name: str
    record_id: str = ""
    action: str
    category: str = "crud"
    changes: dict = {}
    metadata: dict = {}
    user_name: str = ""
    ip_address: str | None = None
    company_name: str = ""
    timestamp: str = ""

    @staticmethod
    def resolve_id(obj):
        return str(obj.id)

    @staticmethod
    def resolve_user_name(obj):
        return obj.user.full_name if obj.user else "System"

    @staticmethod
    def resolve_company_name(obj):
        return obj.company.name if obj.company else ""

    @staticmethod
    def resolve_timestamp(obj):
        return obj.timestamp.isoformat() if obj.timestamp else ""


class AuditLogListOut(Schema):
    count: int
    results: list[AuditLogOut]


@router.get("/audit-logs/", response=AuditLogListOut)
def list_audit_logs(
    request,
    page: int = 1,
    page_size: int = 50,
    model_name: str = "",
    action: str = "",
    user_id: str = "",
    record_id: str = "",
    date_from: str = "",
    date_to: str = "",
    search: str = "",
):
    """List audit logs with filters (superuser only)."""
    if not request.auth.is_superuser:
        raise HttpError(403, "Access denied")

    qs = AuditLog.objects.all()

    if model_name:
        qs = qs.filter(model_name__icontains=model_name)
    if action:
        qs = qs.filter(action=action)
    if user_id:
        try:
            uuid_obj = UUID(user_id)
            qs = qs.filter(user_id=uuid_obj)
        except ValueError:
            pass
    if record_id:
        qs = qs.filter(record_id__icontains=record_id)
    if date_from:
        qs = qs.filter(timestamp__gte=date_from)
    if date_to:
        qs = qs.filter(timestamp__lte=date_to)
    if search:
        qs = qs.filter(
            Q(model_name__icontains=search)
            | Q(action__icontains=search)
            | Q(record_id__icontains=search)
            | Q(ip_address__icontains=search)
        )

    qs = qs.select_related("user", "company").order_by("-timestamp")

    total = qs.count()
    start = (page - 1) * page_size
    end = start + page_size
    items = qs[start:end]

    return {
        "count": total,
        "results": [AuditLogOut.from_orm(item) for item in items],
    }


@router.get("/audit-logs/{id}/", response=AuditLogOut)
def get_audit_log(request, id: UUID):
    """Get a single audit log entry with full change diff (superuser only)."""
    if not request.auth.is_superuser:
        raise HttpError(403, "Access denied")
    try:
        log = AuditLog.objects.select_related("user", "company").get(id=id)
        return log
    except AuditLog.DoesNotExist:
        raise HttpError(404, "Audit log not found") from None


@router.get("/audit-logs/model/{model_name}/{record_id}/", response=list[AuditLogOut])
def get_record_audit_trail(request, model_name: str, record_id: str):
    """Get all audit log entries for a specific record (superuser only)."""
    if not request.auth.is_superuser:
        raise HttpError(403, "Access denied")
    logs = (
        AuditLog.objects.filter(model_name=model_name, record_id=record_id)
        .select_related("user", "company")
        .order_by("timestamp")
    )
    return list(logs)
