"""Numbering service — global policy + per-company counter."""

import datetime
from typing import Any

from django.db import transaction

from apps.core.mixins.models import ConcurrencyError
from apps.core.models import Company, CompanyNumberingSeries, NumberingSeriesPolicy

# --- Helpers ---


def _get_date_part(date_format: str) -> str:
    if not date_format:
        return ""
    now = datetime.date.today()
    fmt = date_format.replace("YYYY", now.strftime("%Y"))
    fmt = fmt.replace("YY", now.strftime("%y"))
    fmt = fmt.replace("MM", now.strftime("%m"))
    fmt = fmt.replace("DD", now.strftime("%d"))
    return fmt


def _needs_reset(assignment: CompanyNumberingSeries) -> bool:
    now = datetime.date.today()
    if assignment.reset_period == "never":
        return False
    if not assignment.last_reset_at:
        return True
    if assignment.reset_period == "yearly":
        return assignment.last_reset_at.year != now.year
    if assignment.reset_period == "monthly":
        return (
            assignment.last_reset_at.year != now.year
            or assignment.last_reset_at.month != now.month
        )
    return False


def format_number(policy: NumberingSeriesPolicy, next_number: int, padding: int) -> str:
    padded = str(next_number).zfill(padding)
    date_part = _get_date_part(policy.date_format)
    return f"{policy.prefix}{date_part}{padded}"


# --- Core ---


@transaction.atomic
def get_next_number(document_type: str, company_id: str) -> str:
    """Get next number for a document type in a company.

    Uses select_for_update() to prevent race conditions.
    """
    try:
        company = Company.objects.get(id=company_id)
    except Company.DoesNotExist:
        raise ValueError(f"Company {company_id} not found") from None

    try:
        policy = NumberingSeriesPolicy.objects.get(
            document_type=document_type, is_active=True
        )
    except NumberingSeriesPolicy.DoesNotExist:
        raise ValueError(
            f"No active numbering policy found for document_type='{document_type}'"
        ) from None

    try:
        assignment = CompanyNumberingSeries.objects.select_for_update().get(
            policy=policy, company=company, is_active=True
        )
    except CompanyNumberingSeries.DoesNotExist:
        raise ValueError(
            f"Company '{company.name}' has no active numbering assignment for "
            f"document_type='{document_type}'"
        ) from None

    if _needs_reset(assignment):
        assignment.next_number = 1
        assignment.last_reset_at = datetime.datetime.now(datetime.UTC)

    number = format_number(policy, assignment.next_number, policy.padding)
    assignment.next_number += 1
    assignment.save(update_fields=["next_number", "last_reset_at", "updated_at"])

    return number


# --- Policy CRUD ---


def list_policies() -> list[NumberingSeriesPolicy]:
    return list(
        NumberingSeriesPolicy.objects.filter(is_active=True).order_by("document_type")
    )


def create_policy(data: dict[str, Any]) -> NumberingSeriesPolicy:
    return NumberingSeriesPolicy.objects.create(
        document_type=data["document_type"],
        prefix=data.get("prefix", ""),
        date_format=data.get("date_format", ""),
        padding=data.get("padding", 6),
        description=data.get("description", ""),
    )


def update_policy(
    policy_id: str, data: dict[str, Any], original_updated_at: str | None = None
) -> NumberingSeriesPolicy:
    with transaction.atomic():
        try:
            policy = NumberingSeriesPolicy.objects.select_for_update().get(id=policy_id)
        except NumberingSeriesPolicy.DoesNotExist:
            raise ValueError("Numbering policy not found") from None

        if original_updated_at:
            from django.utils.dateparse import parse_datetime

            client_ts = parse_datetime(original_updated_at)
            if client_ts:
                db_ts = policy.updated_at
                if not db_ts:
                    raise ConcurrencyError(
                        "Record was modified by another user. Please reload and try again."
                    )
                if db_ts.tzinfo:
                    db_ts = db_ts.replace(tzinfo=None)
                if client_ts.tzinfo:
                    client_ts = client_ts.replace(tzinfo=None)
                if client_ts != db_ts:
                    raise ConcurrencyError(
                        "Record was modified by another user. Please reload and try again."
                    )

        for field in ("document_type", "prefix", "date_format", "padding", "description"):
            if field in data:
                setattr(policy, field, data[field])
        policy.save()
        return policy


def delete_policy(policy_id: str) -> None:
    try:
        policy = NumberingSeriesPolicy.objects.get(id=policy_id)
    except NumberingSeriesPolicy.DoesNotExist:
        raise ValueError("Numbering policy not found") from None
    policy.delete()


# --- Assignment CRUD ---


def get_company_assignments(policy_id: str) -> list[dict[str, Any]]:
    qs = CompanyNumberingSeries.objects.filter(
        policy_id=policy_id
    ).select_related("company")
    return [
        {
            "id": str(a.id),
            "company_id": str(a.company_id),
            "company_name": a.company.name if a.company else "",
            "next_number": a.next_number,
            "reset_period": a.reset_period,
            "last_reset_at": a.last_reset_at.isoformat() if a.last_reset_at else None,
            "is_active": a.is_active,
            "updated_at": a.updated_at.isoformat() if a.updated_at else "",
            "version": a.version,
        }
        for a in qs
    ]


def assign_company(policy_id: str, company_id: str) -> CompanyNumberingSeries:
    try:
        policy = NumberingSeriesPolicy.objects.get(id=policy_id)
    except NumberingSeriesPolicy.DoesNotExist:
        raise ValueError("Numbering policy not found") from None
    try:
        company = Company.objects.get(id=company_id)
    except Company.DoesNotExist:
        raise ValueError("Company not found") from None
    return CompanyNumberingSeries.objects.create(
        policy=policy,
        company=company,
        last_reset_at=datetime.datetime.now(datetime.UTC),
    )


def update_assignment(
    assignment_id: str, data: dict[str, Any], original_updated_at: str | None = None
) -> CompanyNumberingSeries:
    with transaction.atomic():
        try:
            assignment = CompanyNumberingSeries.objects.select_for_update().get(
                id=assignment_id
            )
        except CompanyNumberingSeries.DoesNotExist:
            raise ValueError("Company assignment not found") from None

        if original_updated_at:
            from django.utils.dateparse import parse_datetime

            client_ts = parse_datetime(original_updated_at)
            if client_ts:
                db_ts = assignment.updated_at
                if not db_ts:
                    raise ConcurrencyError(
                        "Record was modified by another user. Please reload and try again."
                    )
                if db_ts.tzinfo:
                    db_ts = db_ts.replace(tzinfo=None)
                if client_ts.tzinfo:
                    client_ts = client_ts.replace(tzinfo=None)
                if client_ts != db_ts:
                    raise ConcurrencyError(
                        "Record was modified by another user. Please reload and try again."
                    )

        for field in ("next_number", "reset_period"):
            if field in data:
                setattr(assignment, field, data[field])
        assignment.save()
        return assignment


def unassign_company(assignment_id: str) -> None:
    try:
        assignment = CompanyNumberingSeries.objects.get(id=assignment_id)
    except CompanyNumberingSeries.DoesNotExist:
        raise ValueError("Company assignment not found") from None
    assignment.delete()


def get_all_assignments(company_id: str | None = None) -> list[CompanyNumberingSeries]:
    qs = CompanyNumberingSeries.objects.select_related("policy", "company").all()
    if company_id:
        qs = qs.filter(company_id=company_id)
    return list(qs.order_by("policy__document_type"))
