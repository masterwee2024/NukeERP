"""Advanced audit service — bulk ops, login, export, config, file, approval tracking."""

import csv
import io
import logging
from datetime import timedelta
from uuid import UUID

from django.db import transaction
from django.db.models import Count
from django.utils import timezone

from apps.core.models import (
    AuditExport,
    AuditLog,
    AuditLogBulk,
    AuditRetention,
    Company,
    User,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Bulk operation audit
# ---------------------------------------------------------------------------


@transaction.atomic
def log_bulk_operation(
    operation_type: str,
    description: str,
    records: list,
    user: User | None = None,
    ip_address: str | None = None,
    company: Company | None = None,
) -> AuditLogBulk:
    """Create a bulk operation audit entry with linked individual audit logs."""
    bulk_op = AuditLogBulk.objects.create(
        operation_type=operation_type,
        description=description,
        record_count=len(records),
        affected_models=list(
            {r.get("model_name", "") for r in records if isinstance(r, dict)}
        ),
        user=user,
        ip_address=ip_address,
        company=company,
    )
    return bulk_op


# ---------------------------------------------------------------------------
# Login/logout audit
# ---------------------------------------------------------------------------


def log_login_action(
    user: User,
    action: str,
    ip_address: str | None = None,
    metadata: dict | None = None,
) -> AuditLog:
    """Log a login/logout event to the audit log."""
    return AuditLog.objects.create(
        model_name="auth.User",
        record_id=str(user.id),
        action=action,
        category="login",
        changes={},
        metadata=metadata or {},
        user=user,
        ip_address=ip_address,
        company=getattr(user, "current_company", None),
    )


# ---------------------------------------------------------------------------
# Export tracking
# ---------------------------------------------------------------------------


@transaction.atomic
def log_export(
    export_type: str,
    filters: dict,
    record_count: int,
    user: User | None = None,
    company: Company | None = None,
    file_path: str = "",
) -> AuditExport:
    """Log a data export operation."""
    export = AuditExport.objects.create(
        export_type=export_type,
        filters=filters,
        record_count=record_count,
        user=user,
        company=company,
        file_path=file_path,
    )

    AuditLog.objects.create(
        model_name="AuditExport",
        record_id=str(export.id),
        action="create",
        category="export",
        changes={
            "export_type": {"old": None, "new": export_type},
            "record_count": {"old": None, "new": record_count},
        },
        metadata={
            "export_type": export_type,
            "record_count": record_count,
            "filters": filters,
        },
        user=user,
        ip_address=None,
        company=company,
    )

    return export


# ---------------------------------------------------------------------------
# Configuration change audit
# ---------------------------------------------------------------------------


def log_config_change(
    model_name: str,
    record_id: str,
    changes: dict,
    user: User | None = None,
    ip_address: str | None = None,
    company: Company | None = None,
) -> AuditLog:
    """Log a configuration change directly (for non-AuditConfigMixin models)."""
    return AuditLog.objects.create(
        model_name=model_name,
        record_id=record_id,
        action="update",
        category="config",
        changes=changes,
        user=user,
        ip_address=ip_address,
        company=company,
    )


# ---------------------------------------------------------------------------
# File attachment audit
# ---------------------------------------------------------------------------


def log_file_action(
    action: str,
    file_name: str,
    user: User | None = None,
    ip_address: str | None = None,
    company: Company | None = None,
    metadata: dict | None = None,
) -> AuditLog:
    """Log a file upload/download/delete action."""
    return AuditLog.objects.create(
        model_name="Attachment",
        record_id="",
        action=action,
        category="file",
        changes={},
        metadata={"file_name": file_name, **(metadata or {})},
        user=user,
        ip_address=ip_address,
        company=company,
    )


# ---------------------------------------------------------------------------
# Approval audit linkage
# ---------------------------------------------------------------------------


def log_approval_action(
    execution_id: UUID,
    action: str,
    user: User | None = None,
    ip_address: str | None = None,
    company: Company | None = None,
    metadata: dict | None = None,
) -> AuditLog:
    """Log an approval action (approve/reject/delegate) to the audit log."""
    return AuditLog.objects.create(
        model_name="WorkflowExecution",
        record_id=str(execution_id),
        action=action,
        category="approval",
        changes={},
        metadata={"execution_id": str(execution_id), **(metadata or {})},
        user=user,
        ip_address=ip_address,
        company=company,
    )


# ---------------------------------------------------------------------------
# Retention policy
# ---------------------------------------------------------------------------


def get_retention_policy(company_id: UUID) -> AuditRetention | None:
    """Get the retention policy for a company, creating a default if none exists."""
    try:
        return AuditRetention.objects.get(company_id=company_id, is_active=True)
    except AuditRetention.DoesNotExist:
        try:
            company = Company.objects.get(id=company_id)
            policy, _ = AuditRetention.objects.get_or_create(
                company=company,
                defaults={
                    "retention_years": 7,
                    "auto_archive": True,
                    "is_active": True,
                },
            )
            return policy
        except Company.DoesNotExist:
            return None


def update_retention_policy(
    company_id: UUID, retention_years: int, auto_archive: bool | None = None
) -> AuditRetention:
    """Update or create retention policy for a company."""
    policy, _ = AuditRetention.objects.update_or_create(
        company_id=company_id,
        defaults={
            "retention_years": retention_years,
            "auto_archive": auto_archive if auto_archive is not None else True,
            "is_active": True,
        },
    )
    return policy


# ---------------------------------------------------------------------------
# Archive old logs
# ---------------------------------------------------------------------------


@transaction.atomic
def archive_old_logs(company_id: UUID | None = None) -> dict:
    """Archive (delete) audit logs older than the retention period.

    Args:
        company_id: If provided, only archive for this company. Otherwise, all companies.

    Returns:
        dict with 'deleted_count' and 'companies_processed'.
    """
    total_deleted = 0
    companies_processed = 0

    companies = (
        Company.objects.filter(id=company_id) if company_id else Company.objects.all()
    )

    for company in companies:
        policy = get_retention_policy(company.id)
        if not policy or not policy.is_active:
            continue

        cutoff = timezone.now() - timedelta(days=policy.retention_years * 365)
        qs = AuditLog.objects.filter(company=company, timestamp__lt=cutoff)
        count = qs.count()
        if count == 0:
            continue
        deleted, _ = qs.delete()
        total_deleted += deleted
        companies_processed += 1

        policy.last_archive_date = timezone.now()
        policy.save(update_fields=["last_archive_date"])

    return {"deleted_count": total_deleted, "companies_processed": companies_processed}


# ---------------------------------------------------------------------------
# Export audit logs
# ---------------------------------------------------------------------------


def export_audit_logs(
    fmt: str,
    company_id: UUID | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    category: str | None = None,
    model_name: str | None = None,
    user_id: UUID | None = None,
) -> tuple[str, str]:
    """Export audit logs as CSV or Excel-compatible CSV.

    Returns (content, content_type).
    """
    qs = AuditLog.objects.select_related("user", "company").order_by("-timestamp")

    if company_id:
        qs = qs.filter(company_id=company_id)
    if date_from:
        qs = qs.filter(timestamp__gte=date_from)
    if date_to:
        qs = qs.filter(timestamp__lte=date_to)
    if category:
        qs = qs.filter(category=category)
    if model_name:
        qs = qs.filter(model_name__icontains=model_name)
    if user_id:
        qs = qs.filter(user_id=user_id)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "Timestamp",
            "Category",
            "Action",
            "Model",
            "Record ID",
            "User",
            "Company",
            "IP Address",
            "Changes",
        ]
    )

    for log in qs.iterator(chunk_size=500):
        writer.writerow(
            [
                log.timestamp.isoformat() if log.timestamp else "",
                log.category,
                log.action,
                log.model_name,
                log.record_id,
                log.user.email if log.user else "",
                log.company.name if log.company else "",
                log.ip_address or "",
                str(log.changes),
            ]
        )

    content = output.getvalue()
    content_type = "text/csv" if fmt == "csv" else "text/csv"
    return content, content_type


# ---------------------------------------------------------------------------
# Audit dashboard
# ---------------------------------------------------------------------------


def get_audit_dashboard(company_id: UUID, period_days: int = 30) -> dict:
    """Get audit dashboard summary statistics."""
    since = timezone.now() - timedelta(days=period_days)

    base_qs = AuditLog.objects.filter(company_id=company_id, timestamp__gte=since)

    total_changes = base_qs.count()

    # By category
    category_counts = dict(base_qs.values_list("category").annotate(count=Count("id")))
    category_total = sum(category_counts.values())
    by_category = [
        {
            "category": cat,
            "count": count,
            "percentage": (
                round(count / category_total * 100, 1) if category_total else 0
            ),
        }
        for cat, count in sorted(
            category_counts.items(), key=lambda x: x[1], reverse=True
        )
    ]

    # By user (top 10)
    user_qs = (
        base_qs.values("user__email", "user__first_name", "user__last_name")
        .annotate(count=Count("id"))
        .order_by("-count")[:10]
    )
    by_user = [
        {
            "email": u["user__email"] or "System",
            "full_name": f"{u['user__first_name'] or ''} {u['user__last_name'] or ''}".strip(),
            "count": u["count"],
        }
        for u in user_qs
    ]

    # By model (top 10)
    model_qs = (
        base_qs.values("model_name").annotate(count=Count("id")).order_by("-count")[:10]
    )
    by_model = [{"model_name": m["model_name"], "count": m["count"]} for m in model_qs]

    # Daily trend
    daily_qs = (
        base_qs.extra({"date": "date(timestamp)"})
        .values("date")
        .annotate(count=Count("id"))
        .order_by("date")
    )
    daily_trend = [
        {
            "date": (
                d["date"].isoformat()
                if hasattr(d["date"], "isoformat")
                else str(d["date"])
            ),
            "count": d["count"],
        }
        for d in daily_qs
    ]

    return {
        "total_changes": total_changes,
        "period_days": period_days,
        "by_category": by_category,
        "by_user": by_user,
        "by_model": by_model,
        "daily_trend": daily_trend,
    }
