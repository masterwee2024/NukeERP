"""Advanced audit API — export, dashboard, retention, archive."""

from uuid import UUID

from django.http import HttpResponse
from django.utils import timezone
from ninja import Router, Schema
from ninja.errors import HttpError

from apps.core.api.auth import JWTAuth
from apps.core.models import AuditExport
from apps.core.services.advanced_audit_service import (
    archive_old_logs,
    export_audit_logs,
    get_audit_dashboard,
    get_retention_policy,
    update_retention_policy,
)

router = Router(auth=JWTAuth())


def _require_superuser(request):
    if not request.auth.is_superuser:
        raise HttpError(403, "Access denied")


def _require_company_id(request) -> UUID:
    company_id = request.headers.get("x-company-id")
    if not company_id:
        raise HttpError(400, "X-Company-Id header is required")
    try:
        return UUID(company_id)
    except ValueError:
        raise HttpError(400, "Invalid X-Company-Id header") from None


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class CategoryBreakdown(Schema):
    category: str
    count: int
    percentage: float = 0.0


class UserBreakdown(Schema):
    email: str
    full_name: str = ""
    count: int


class ModelBreakdown(Schema):
    model_name: str
    count: int


class DailyTrend(Schema):
    date: str
    count: int


class AuditDashboardOut(Schema):
    total_changes: int
    period_days: int
    by_category: list[CategoryBreakdown]
    by_user: list[UserBreakdown]
    by_model: list[ModelBreakdown]
    daily_trend: list[DailyTrend]


class AuditRetentionOut(Schema):
    id: str
    company_id: str
    retention_years: int
    auto_archive: bool
    last_archive_date: str | None = None
    is_active: bool

    @staticmethod
    def resolve_id(obj):
        return str(obj.id)

    @staticmethod
    def resolve_company_id(obj):
        return str(obj.company_id)

    @staticmethod
    def resolve_last_archive_date(obj):
        return obj.last_archive_date.isoformat() if obj.last_archive_date else None


class AuditRetentionUpdateIn(Schema):
    retention_years: int
    auto_archive: bool | None = True


class ArchiveOut(Schema):
    deleted_count: int
    companies_processed: int


class AuditExportOut(Schema):
    id: str
    export_type: str
    filters: dict = {}
    record_count: int
    user_email: str = ""
    company_name: str = ""
    created_at: str = ""

    @staticmethod
    def resolve_id(obj):
        return str(obj.id)

    @staticmethod
    def resolve_user_email(obj):
        return obj.user.email if obj.user else ""

    @staticmethod
    def resolve_company_name(obj):
        return obj.company.name if obj.company else ""

    @staticmethod
    def resolve_created_at(obj):
        return obj.created_at.isoformat() if obj.created_at else ""


class AuditExportListOut(Schema):
    count: int
    results: list[AuditExportOut]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/audit-logs/dashboard/", response=AuditDashboardOut)
def dashboard(request, period_days: int = 30):
    """Get audit dashboard summary (superuser only)."""
    _require_superuser(request)
    company_id = _require_company_id(request)
    return get_audit_dashboard(company_id, period_days)


@router.get("/audit-logs/export/")
def export_audit(
    request,
    fmt: str = "csv",
    date_from: str = "",
    date_to: str = "",
    category: str = "",
    model_name: str = "",
):
    """Export audit logs as CSV (superuser only)."""
    _require_superuser(request)
    company_id = _require_company_id(request)

    content, content_type = export_audit_logs(
        fmt=fmt,
        company_id=company_id,
        date_from=date_from or None,
        date_to=date_to or None,
        category=category or None,
        model_name=model_name or None,
    )

    response = HttpResponse(content, content_type=content_type)
    response["Content-Disposition"] = (
        f'attachment; filename="audit_logs_{timezone.now().strftime("%Y%m%d")}.{fmt}"'
    )
    return response


@router.get("/audit-exports/", response=AuditExportListOut)
def list_audit_exports(request, page: int = 1, page_size: int = 20):
    """List audit export history (superuser only)."""
    _require_superuser(request)
    company_id = _require_company_id(request)

    qs = (
        AuditExport.objects.filter(company_id=company_id)
        .select_related("user", "company")
        .order_by("-created_at")
    )
    total = qs.count()
    start = (page - 1) * page_size
    end = start + page_size
    items = qs[start:end]

    return {
        "count": total,
        "results": [AuditExportOut.from_orm(item) for item in items],
    }


@router.get("/audit-retention/", response=AuditRetentionOut)
def get_retention(request):
    """Get audit retention policy for the current company (superuser only)."""
    _require_superuser(request)
    company_id = _require_company_id(request)
    policy = get_retention_policy(company_id)
    if not policy:
        raise HttpError(404, "Retention policy not found")
    return policy


@router.put("/audit-retention/", response=AuditRetentionOut)
def update_retention(request, payload: AuditRetentionUpdateIn):
    """Update audit retention policy (superuser only)."""
    _require_superuser(request)
    company_id = _require_company_id(request)

    if payload.retention_years < 1 or payload.retention_years > 20:
        raise HttpError(400, "Retention years must be between 1 and 20")

    policy = update_retention_policy(
        company_id=company_id,
        retention_years=payload.retention_years,
        auto_archive=payload.auto_archive,
    )
    return policy


@router.post("/audit-logs/archive-logs/", response=ArchiveOut)
def archive_logs(request):
    """Trigger manual archive of old audit logs (superuser only)."""
    _require_superuser(request)
    company_id = _require_company_id(request)
    return archive_old_logs(company_id)
