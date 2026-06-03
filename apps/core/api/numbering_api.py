"""Numbering series API — global policy + per-company assignment."""

from uuid import UUID

from ninja import Router, Schema
from ninja.errors import HttpError

from apps.core.mixins.models import ConcurrencyError
from apps.core.models import NumberingSeriesPolicy
from apps.core.services import numbering_service

router = Router()


# --- Schemas ---


class PolicyCreateSchema(Schema):
    document_type: str
    prefix: str = ""
    date_format: str = ""
    padding: int = 6
    description: str = ""


class PolicyUpdateSchema(Schema):
    document_type: str | None = None
    prefix: str | None = None
    date_format: str | None = None
    padding: int | None = None
    description: str | None = None
    updated_at: str | None = None


class AssignmentOut(Schema):
    id: str
    company_id: str
    company_name: str = ""
    next_number: int
    reset_period: str
    last_reset_at: str | None = None
    is_active: bool = True
    updated_at: str = ""
    version: int = 1


class PolicyOut(Schema):
    id: str
    document_type: str
    prefix: str = ""
    date_format: str = ""
    padding: int
    description: str = ""
    is_active: bool = True
    created_at: str = ""
    updated_at: str = ""
    version: int = 1
    company_assignments: list[AssignmentOut] = []


class PolicyListOut(Schema):
    id: str
    document_type: str
    prefix: str = ""
    date_format: str = ""
    padding: int
    description: str = ""
    is_active: bool = True

    @staticmethod
    def resolve_id(obj):
        return str(obj.id)


class AssignSchema(Schema):
    company_id: str


class AssignmentUpdateSchema(Schema):
    next_number: int | None = None
    reset_period: str | None = None
    updated_at: str | None = None


class NumberingNextOut(Schema):
    number: str
    document_type: str


# --- Helpers ---


def _policy_to_out(policy: NumberingSeriesPolicy) -> PolicyOut:
    assignments = numbering_service.get_company_assignments(str(policy.id))
    return PolicyOut(
        id=str(policy.id),
        document_type=policy.document_type,
        prefix=policy.prefix,
        date_format=policy.date_format,
        padding=policy.padding,
        description=policy.description,
        is_active=policy.is_active,
        created_at=policy.created_at.isoformat() if policy.created_at else "",
        updated_at=policy.updated_at.isoformat() if policy.updated_at else "",
        version=policy.version,
        company_assignments=assignments,
    )


# --- Policy Endpoints ---


@router.get("/numbering-policies/", response=list[PolicyListOut])
def list_policies(request):
    """List all numbering policies (superuser only)."""
    if not request.auth.is_superuser:
        raise HttpError(403, "Access denied")
    return numbering_service.list_policies()


@router.post("/numbering-policies/", response=PolicyOut)
def create_policy(request, payload: PolicyCreateSchema):
    """Create a new global numbering policy."""
    if not request.auth.is_superuser:
        raise HttpError(403, "Access denied")
    try:
        policy = numbering_service.create_policy(payload.model_dump())
        return _policy_to_out(policy)
    except Exception as e:
        raise HttpError(400, str(e)) from e


@router.get("/numbering-policies/{policy_id}/", response=PolicyOut)
def get_policy(request, policy_id: UUID):
    """Get a numbering policy with its company assignments."""
    if not request.auth.is_superuser:
        raise HttpError(403, "Access denied")
    try:
        policy = NumberingSeriesPolicy.objects.get(id=policy_id)
        return _policy_to_out(policy)
    except NumberingSeriesPolicy.DoesNotExist:
        raise HttpError(404, "Policy not found") from None


@router.put("/numbering-policies/{policy_id}/", response=PolicyOut)
def update_policy(request, policy_id: UUID, payload: PolicyUpdateSchema):
    """Update a numbering policy."""
    if not request.auth.is_superuser:
        raise HttpError(403, "Access denied")
    try:
        policy = numbering_service.update_policy(
            str(policy_id),
            payload.model_dump(exclude_unset=True),
            original_updated_at=payload.updated_at,
        )
        return _policy_to_out(policy)
    except ConcurrencyError as e:
        raise HttpError(409, str(e)) from e
    except ValueError as e:
        raise HttpError(404, str(e)) from e


@router.delete("/numbering-policies/{policy_id}/")
def delete_policy(request, policy_id: UUID):
    """Delete a numbering policy (cascades to assignments)."""
    if not request.auth.is_superuser:
        raise HttpError(403, "Access denied")
    try:
        numbering_service.delete_policy(str(policy_id))
        return {"detail": "Numbering policy deleted"}
    except ValueError as e:
        raise HttpError(404, str(e)) from e


# --- Assignment Endpoints ---


@router.post(
    "/numbering-policies/{policy_id}/assign/",
    response=AssignmentOut,
)
def assign_company(request, policy_id: UUID, payload: AssignSchema):
    """Assign a numbering policy to a company."""
    if not request.auth.is_superuser:
        raise HttpError(403, "Access denied")
    try:
        numbering_service.assign_company(str(policy_id), payload.company_id)
        return numbering_service.get_company_assignments(str(policy_id))[0]
    except ValueError as e:
        raise HttpError(400, str(e)) from e


@router.put(
    "/numbering-policies/{policy_id}/assign/{assignment_id}/",
    response=AssignmentOut,
)
def update_assignment(
    request,
    policy_id: UUID,
    assignment_id: UUID,
    payload: AssignmentUpdateSchema,
):
    """Update a company's numbering assignment (next_number, reset_period)."""
    if not request.auth.is_superuser:
        raise HttpError(403, "Access denied")
    try:
        numbering_service.update_assignment(
            str(assignment_id),
            payload.model_dump(exclude_unset=True),
            original_updated_at=payload.updated_at,
        )
        assignments = numbering_service.get_company_assignments(str(policy_id))
        for a in assignments:
            if a["id"] == str(assignment_id):
                return a
        raise HttpError(404, "Assignment not found in policy")
    except ConcurrencyError as e:
        raise HttpError(409, str(e)) from e
    except ValueError as e:
        raise HttpError(404, str(e)) from e


@router.delete(
    "/numbering-policies/{policy_id}/assign/{assignment_id}/",
)
def unassign_company(request, policy_id: UUID, assignment_id: UUID):
    """Remove a company's numbering assignment."""
    if not request.auth.is_superuser:
        raise HttpError(403, "Access denied")
    try:
        numbering_service.unassign_company(str(assignment_id))
        return {"detail": "Company unassigned"}
    except ValueError as e:
        raise HttpError(404, str(e)) from e


# --- Utility Endpoint ---


@router.get("/numbering-series/next/", response=NumberingNextOut)
def get_next_number(request, document_type: str, company_id: str):
    """Get next number for a document type (utility endpoint)."""
    if not request.auth.is_superuser:
        raise HttpError(403, "Access denied")
    try:
        number = numbering_service.get_next_number(document_type, company_id)
        return {"number": number, "document_type": document_type}
    except ValueError as e:
        raise HttpError(400, str(e)) from e
