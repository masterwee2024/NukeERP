"""Account API — CRUD, tree, assignments, import."""

import csv
import io
from uuid import UUID

from django.http import HttpResponse
from ninja import Router, Schema
from ninja.errors import HttpError

from apps.core.api.auth import JWTAuth
from apps.financial.services.account_service import (
    create_account,
    delete_account,
    get_account_flat,
    get_account_tree,
    import_accounts_from_csv,
    set_company_assignments,
    update_account,
)

router = Router(auth=JWTAuth())


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


class AccountOut(Schema):
    id: str
    code: str
    name: str
    account_type: str
    subtype: str = ""
    level: int = 0
    is_group: bool = False
    is_active: bool = True
    mfrs_code: str = ""
    parent_id: str | None = None
    children: list["AccountOut"] = []


class AccountCreateIn(Schema):
    code: str
    name: str
    account_type: str
    subtype: str = ""
    parent_id: str | None = None
    is_group: bool = False
    mfrs_code: str = ""
    notes: str = ""


class AccountUpdateIn(Schema):
    name: str | None = None
    account_type: str | None = None
    subtype: str | None = None
    parent_id: str | None = None
    is_group: bool | None = None
    is_active: bool | None = None
    mfrs_code: str | None = None
    notes: str | None = None


class AccountModelOut(Schema):
    id: str
    code: str
    name: str
    account_type: str
    subtype: str = ""
    level: int = 0
    is_group: bool = False
    is_active: bool = True
    mfrs_code: str = ""
    parent_id: str | None = None

    @staticmethod
    def resolve_id(obj):
        return str(obj.id)

    @staticmethod
    def resolve_parent_id(obj):
        return str(obj.parent_id) if obj.parent_id else None


class AssignmentRecord(Schema):
    id: str
    code: str
    name: str
    is_assigned: bool = False


class AssignmentListOut(Schema):
    count: int
    results: list[AssignmentRecord]


class AssignmentIn(Schema):
    account_ids: list[str]


class AssignmentOut(Schema):
    assigned_count: int


class ImportOut(Schema):
    created: int
    errors: list[str] = []
    total: int


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/accounts/")
def list_accounts(request):
    """List accounts as a tree structure. Filtered by X-Company-Id if provided."""
    company_id = request.headers.get("x-company-id")
    try:
        cid = UUID(company_id) if company_id else None
    except ValueError:
        cid = None
    results = get_account_tree(company_id=cid)
    return {"results": results}


@router.post("/accounts/", response=AccountModelOut)
def create(request, payload: AccountCreateIn):
    """Create a new account."""
    parent_id = UUID(payload.parent_id) if payload.parent_id else None
    account = create_account(
        code=payload.code,
        name=payload.name,
        account_type=payload.account_type,
        subtype=payload.subtype,
        parent_id=parent_id,
        is_group=payload.is_group,
        mfrs_code=payload.mfrs_code,
        notes=payload.notes,
    )
    return account


@router.get("/accounts/template/")
def download_template(request):
    """Download a CSV template for account import."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        ["code", "name", "account_type", "subtype", "parent_code", "mfrs_code"]
    )
    writer.writerow(["1000", "Assets", "asset", "", "", ""])
    writer.writerow(["1100", "Current Assets", "asset", "current_asset", "1000", ""])
    writer.writerow(["1110", "Cash", "asset", "current_asset", "1100", ""])

    response = HttpResponse(output.getvalue(), content_type="text/csv")
    response["Content-Disposition"] = (
        'attachment; filename="chart_of_accounts_template.csv"'
    )
    return response


@router.post("/accounts/import/")
def import_csv(request):
    """Import accounts from CSV file upload."""
    file = request.FILES.get("file")
    if not file:
        raise HttpError(400, "CSV file is required")

    content = file.read().decode("utf-8-sig")
    result = import_accounts_from_csv(content)
    return result


@router.put("/accounts/{id}/", response=AccountModelOut)
def update(request, id: UUID, payload: AccountUpdateIn):
    """Update an existing account."""
    parent_id = UUID(payload.parent_id) if payload.parent_id else None
    account = update_account(
        account_id=id,
        name=payload.name,
        account_type=payload.account_type,
        subtype=payload.subtype,
        parent_id=parent_id,
        is_group=payload.is_group,
        is_active=payload.is_active,
        mfrs_code=payload.mfrs_code,
        notes=payload.notes,
    )
    return account


@router.delete("/accounts/{id}/")
def delete(request, id: UUID):
    """Delete an account. Blocked if it has children or transactions."""
    try:
        delete_account(id)
        return {"success": True}
    except Exception as e:
        raise HttpError(409, str(e)) from e


# ---------------------------------------------------------------------------
# Company assignments
# ---------------------------------------------------------------------------


@router.get("/accounts/assignments/{company_id}/", response=AssignmentListOut)
def list_assignments(request, company_id: UUID):
    """List all accounts with their assignment status for a company."""
    results = get_account_flat(company_id=company_id)
    return {"count": len(results), "results": results}


@router.post("/accounts/assignments/{company_id}/", response=AssignmentOut)
def set_assignments(request, company_id: UUID, payload: AssignmentIn):
    """Replace all account assignments for a company."""
    account_ids = [UUID(aid) for aid in payload.account_ids]
    count = set_company_assignments(company_id, account_ids)
    return {"assigned_count": count}
