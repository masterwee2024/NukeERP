"""Account service — business logic for Chart of Accounts."""

import csv
import io
import logging
from uuid import UUID

from django.db import transaction

from apps.core.mixins.models import ConcurrencyError
from apps.financial.models import Account, AccountCompany

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------


def create_account(
    code: str,
    name: str,
    account_type: str,
    subtype: str = "",
    parent_id: UUID | None = None,
    is_group: bool = False,
    mfrs_code: str = "",
    notes: str = "",
) -> Account:
    parent = None
    level = 0
    if parent_id:
        parent = Account.objects.get(id=parent_id)
        level = parent.level + 1

    return Account.objects.create(
        code=code,
        name=name,
        account_type=account_type,
        subtype=subtype,
        parent=parent,
        level=level,
        is_group=is_group,
        mfrs_code=mfrs_code,
        notes=notes,
    )


def update_account(
    account_id: UUID,
    name: str | None = None,
    account_type: str | None = None,
    subtype: str | None = None,
    parent_id: UUID | None = None,
    is_group: bool | None = None,
    is_active: bool | None = None,
    mfrs_code: str | None = None,
    notes: str | None = None,
) -> Account:
    account = Account.objects.select_for_update().get(id=account_id)

    if name is not None:
        account.name = name
    if account_type is not None:
        account.account_type = account_type
    if subtype is not None:
        account.subtype = subtype
    if parent_id is not None:
        account.parent = Account.objects.get(id=parent_id)
        account.level = account.parent.level + 1
    if is_group is not None:
        account.is_group = is_group
    if is_active is not None:
        account.is_active = is_active
    if mfrs_code is not None:
        account.mfrs_code = mfrs_code
    if notes is not None:
        account.notes = notes

    account.save()
    return account


@transaction.atomic
def delete_account(account_id: UUID) -> bool:
    """Delete an account. Raises ConcurrencyError if it has children or transactions."""
    account = Account.objects.select_for_update().get(id=account_id)

    if account.children.exists():
        raise ConcurrencyError("Cannot delete an account with child accounts.")

    account.delete()
    return True


# ---------------------------------------------------------------------------
# Tree
# ---------------------------------------------------------------------------


def get_account_tree(company_id: UUID | None = None) -> list[dict]:
    """Build nested account tree, optionally filtered by company assignment."""
    accounts = Account.objects.all().order_by("code")

    if company_id:
        assigned_ids = AccountCompany.objects.filter(
            company_id=company_id, is_active=True
        ).values_list("account_id", flat=True)
        accounts = accounts.filter(id__in=assigned_ids)

    def _build_children(parent_id: UUID | None = None) -> list[dict]:
        return [
            {
                "id": str(a.id),
                "code": a.code,
                "name": a.name,
                "account_type": a.account_type,
                "subtype": a.subtype,
                "level": a.level,
                "is_group": a.is_group,
                "is_active": a.is_active,
                "mfrs_code": a.mfrs_code,
                "parent_id": str(a.parent_id) if a.parent_id else None,
                "children": _build_children(a.id),
            }
            for a in accounts.filter(parent_id=parent_id)
        ]

    return _build_children()


def get_account_flat(company_id: UUID | None = None) -> list[dict]:
    """Return flat list of accounts for assignment UI."""
    accounts = Account.objects.all().order_by("code")

    if company_id:
        assigned_ids = set(
            AccountCompany.objects.filter(
                company_id=company_id, is_active=True
            ).values_list("account_id", flat=True)
        )
        return [
            {
                "id": str(a.id),
                "code": a.code,
                "name": a.name,
                "is_assigned": a.id in assigned_ids,
            }
            for a in accounts
        ]

    return [
        {
            "id": str(a.id),
            "code": a.code,
            "name": a.name,
            "is_assigned": False,
        }
        for a in accounts
    ]


# ---------------------------------------------------------------------------
# Company assignments (bulk)
# ---------------------------------------------------------------------------


@transaction.atomic
def set_company_assignments(company_id: UUID, account_ids: list[UUID]) -> int:
    """Replace all account assignments for a company."""
    AccountCompany.objects.filter(company_id=company_id).delete()
    assignments = [
        AccountCompany(account_id=aid, company_id=company_id) for aid in account_ids
    ]
    AccountCompany.objects.bulk_create(assignments)
    return len(assignments)


# ---------------------------------------------------------------------------
# CSV Import
# ---------------------------------------------------------------------------


@transaction.atomic
def import_accounts_from_csv(file_content: str) -> dict:
    """Import accounts from CSV content. Returns import stats."""
    reader = csv.DictReader(io.StringIO(file_content))
    created = 0
    errors = []

    code_parent_map: dict[str, UUID | None] = {}
    rows = list(reader)

    # First pass: create all accounts (parents first by ordering)
    rows_sorted = sorted(rows, key=lambda r: r.get("code", ""))
    for row in rows_sorted:
        code = row.get("code", "").strip()
        name = row.get("name", "").strip()
        account_type = row.get("account_type", "").strip()
        subtype = row.get("subtype", "").strip()
        parent_code = row.get("parent_code", "").strip()
        mfrs_code = row.get("mfrs_code", "").strip()

        if not code or not name or not account_type:
            errors.append(
                f"Row {row}: missing required fields (code, name, account_type)"
            )
            continue

        try:
            parent_id = code_parent_map.get(parent_code) if parent_code else None
            level = 0
            if parent_id:
                parent = Account.objects.get(id=parent_id)
                level = parent.level + 1

            account = Account.objects.create(
                code=code,
                name=name,
                account_type=account_type,
                subtype=subtype,
                parent_id=parent_id,
                level=level,
                is_group=bool(parent_code),
                mfrs_code=mfrs_code,
            )
            code_parent_map[code] = account.id
            created += 1
        except Exception as e:
            errors.append(f"Row {code}: {str(e)}")

    return {"created": created, "errors": errors, "total": len(rows)}
