"""Opening balance migration service — GL, AP, AR, inventory, asset opening balances."""

import csv
import io
import logging
from datetime import date
from decimal import Decimal
from uuid import UUID

from django.db import transaction
from django.utils import timezone

from apps.core.models import (
    OpeningBalanceAP,
    OpeningBalanceAR,
    OpeningBalanceAsset,
    OpeningBalanceGL,
    OpeningBalanceInventory,
    OpeningBalanceMigration,
)

logger = logging.getLogger(__name__)


def create_migration(
    company_id: UUID, go_live_date: date, user
) -> OpeningBalanceMigration:
    return OpeningBalanceMigration.objects.create(
        company_id=company_id,
        go_live_date=go_live_date,
        status="draft",
        created_by=user,
    )


def get_migration(
    migration_id: UUID, company_id: UUID | None = None
) -> OpeningBalanceMigration | None:
    qs = OpeningBalanceMigration.objects.filter(id=migration_id)
    if company_id:
        qs = qs.filter(company_id=company_id)
    return qs.first()


def parse_csv(content: str) -> tuple[list[str], list[dict[str, str]]]:
    reader = csv.DictReader(io.StringIO(content))
    headers = reader.fieldnames or []
    rows = [{k.strip(): v.strip() for k, v in row.items() if k} for row in reader]
    return headers, rows


COLUMN_DEFS = {
    "gl": [
        {"name": "account_code", "label": "Account Code", "required": True},
        {"name": "account_name", "label": "Account Name", "required": False},
        {"name": "debit", "label": "Debit", "required": False},
        {"name": "credit", "label": "Credit", "required": False},
    ],
    "ap": [
        {"name": "supplier_code", "label": "Supplier Code", "required": True},
        {"name": "invoice_no", "label": "Invoice No", "required": True},
        {"name": "invoice_date", "label": "Invoice Date", "required": True},
        {"name": "due_date", "label": "Due Date", "required": True},
        {"name": "amount", "label": "Amount", "required": True},
        {"name": "currency", "label": "Currency", "required": False},
    ],
    "ar": [
        {"name": "customer_code", "label": "Customer Code", "required": True},
        {"name": "invoice_no", "label": "Invoice No", "required": True},
        {"name": "invoice_date", "label": "Invoice Date", "required": True},
        {"name": "due_date", "label": "Due Date", "required": True},
        {"name": "amount", "label": "Amount", "required": True},
        {"name": "currency", "label": "Currency", "required": False},
    ],
    "inventory": [
        {"name": "item_code", "label": "Item Code", "required": True},
        {"name": "warehouse_code", "label": "Warehouse Code", "required": True},
        {"name": "quantity", "label": "Quantity", "required": True},
        {"name": "unit_cost", "label": "Unit Cost", "required": True},
    ],
    "asset": [
        {"name": "asset_code", "label": "Asset Code", "required": True},
        {"name": "name", "label": "Name", "required": True},
        {"name": "category", "label": "Category", "required": False},
        {"name": "purchase_date", "label": "Purchase Date", "required": True},
        {"name": "cost", "label": "Cost", "required": True},
        {
            "name": "accumulated_depreciation",
            "label": "Accumulated Depreciation",
            "required": False,
        },
        {"name": "useful_life", "label": "Useful Life (years)", "required": False},
    ],
}


def generate_csv_template(balance_type: str) -> tuple[str, str] | None:
    cols = COLUMN_DEFS.get(balance_type)
    if not cols:
        return None
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([c["label"] for c in cols])
    return output.getvalue(), f"opening_{balance_type}_template.csv"


def validate_rows(balance_type: str, rows: list[dict]) -> list[dict]:
    cols = COLUMN_DEFS.get(balance_type, [])
    errors = []
    for i, row in enumerate(rows):
        row_errors = []
        for col in cols:
            if col["required"] and not row.get(col["name"], "").strip():
                row_errors.append(f"{col['label']} is required")
        if balance_type == "gl":
            try:
                d = Decimal(str(row.get("debit", 0) or 0))
                c = Decimal(str(row.get("credit", 0) or 0))
                if d == 0 and c == 0:
                    row_errors.append("Debit or Credit must be > 0")
            except (ValueError, TypeError):
                row_errors.append("Invalid debit/credit amount")
        elif balance_type in ("ap", "ar"):
            try:
                amt = Decimal(str(row.get("amount", 0) or 0))
                if amt <= 0:
                    row_errors.append("Amount must be > 0")
            except (ValueError, TypeError):
                row_errors.append("Invalid amount")
        elif balance_type == "inventory":
            try:
                qty = Decimal(str(row.get("quantity", 0) or 0))
                cost = Decimal(str(row.get("unit_cost", 0) or 0))
                if qty < 0:
                    row_errors.append("Quantity cannot be negative")
                if cost <= 0:
                    row_errors.append("Unit cost must be > 0")
            except (ValueError, TypeError):
                row_errors.append("Invalid quantity or cost")
        elif balance_type == "asset":
            try:
                cst = Decimal(str(row.get("cost", 0) or 0))
                if cst <= 0:
                    row_errors.append("Cost must be > 0")
                accum = Decimal(str(row.get("accumulated_depreciation", 0) or 0))
                if accum > cst:
                    row_errors.append("Accumulated depreciation cannot exceed cost")
            except (ValueError, TypeError):
                row_errors.append("Invalid cost or depreciation")
        errors.append({"row": i + 1, "errors": row_errors, "data": row})
    return errors


def validate_gl_balance(rows: list[dict]) -> dict:
    total_dr = sum(Decimal(str(r.get("debit", 0) or 0)) for r in rows)
    total_cr = sum(Decimal(str(r.get("credit", 0) or 0)) for r in rows)
    return {
        "total_debit": float(total_dr),
        "total_credit": float(total_cr),
        "balanced": total_dr == total_cr,
        "difference": float(abs(total_dr - total_cr)),
    }


def import_gl(migration_id: UUID, rows: list[dict], validation: list[dict]) -> dict:
    migration = OpeningBalanceMigration.objects.get(id=migration_id)
    success = 0
    errors = 0
    for v in validation:
        if v["errors"]:
            OpeningBalanceGL.objects.create(
                migration=migration,
                row_number=v["row"],
                status="error",
                errors=v["errors"],
            )
            errors += 1
        else:
            row = v["data"]
            OpeningBalanceGL.objects.create(
                migration=migration,
                account_code=row.get("account_code", ""),
                account_name=row.get("account_name", ""),
                debit=Decimal(str(row.get("debit", 0) or 0)),
                credit=Decimal(str(row.get("credit", 0) or 0)),
                row_number=v["row"],
                status="imported",
            )
            success += 1
    return {"success": success, "errors": errors, "total": len(rows)}


def import_ap(migration_id: UUID, rows: list[dict], validation: list[dict]) -> dict:
    migration = OpeningBalanceMigration.objects.get(id=migration_id)
    success = 0
    errors = 0
    for v in validation:
        if v["errors"]:
            OpeningBalanceAP.objects.create(
                migration=migration,
                row_number=v["row"],
                status="error",
                errors=v["errors"],
            )
            errors += 1
        else:
            row = v["data"]
            OpeningBalanceAP.objects.create(
                migration=migration,
                supplier_code=row.get("supplier_code", ""),
                invoice_no=row.get("invoice_no", ""),
                invoice_date=row.get("invoice_date"),
                due_date=row.get("due_date"),
                amount=Decimal(str(row.get("amount", 0) or 0)),
                currency=row.get("currency", "MYR"),
                row_number=v["row"],
                status="imported",
            )
            success += 1
    return {"success": success, "errors": errors, "total": len(rows)}


def import_ar(migration_id: UUID, rows: list[dict], validation: list[dict]) -> dict:
    migration = OpeningBalanceMigration.objects.get(id=migration_id)
    success = 0
    errors = 0
    for v in validation:
        if v["errors"]:
            OpeningBalanceAR.objects.create(
                migration=migration,
                row_number=v["row"],
                status="error",
                errors=v["errors"],
            )
            errors += 1
        else:
            row = v["data"]
            OpeningBalanceAR.objects.create(
                migration=migration,
                customer_code=row.get("customer_code", ""),
                invoice_no=row.get("invoice_no", ""),
                invoice_date=row.get("invoice_date"),
                due_date=row.get("due_date"),
                amount=Decimal(str(row.get("amount", 0) or 0)),
                currency=row.get("currency", "MYR"),
                row_number=v["row"],
                status="imported",
            )
            success += 1
    return {"success": success, "errors": errors, "total": len(rows)}


def import_inventory(
    migration_id: UUID, rows: list[dict], validation: list[dict]
) -> dict:
    migration = OpeningBalanceMigration.objects.get(id=migration_id)
    success = 0
    errors = 0
    for v in validation:
        if v["errors"]:
            OpeningBalanceInventory.objects.create(
                migration=migration,
                row_number=v["row"],
                status="error",
                errors=v["errors"],
            )
            errors += 1
        else:
            row = v["data"]
            OpeningBalanceInventory.objects.create(
                migration=migration,
                item_code=row.get("item_code", ""),
                warehouse_code=row.get("warehouse_code", ""),
                quantity=Decimal(str(row.get("quantity", 0) or 0)),
                unit_cost=Decimal(str(row.get("unit_cost", 0) or 0)),
                row_number=v["row"],
                status="imported",
            )
            success += 1
    return {"success": success, "errors": errors, "total": len(rows)}


def import_asset(migration_id: UUID, rows: list[dict], validation: list[dict]) -> dict:
    migration = OpeningBalanceMigration.objects.get(id=migration_id)
    success = 0
    errors = 0
    for v in validation:
        if v["errors"]:
            OpeningBalanceAsset.objects.create(
                migration=migration,
                row_number=v["row"],
                status="error",
                errors=v["errors"],
            )
            errors += 1
        else:
            row = v["data"]
            OpeningBalanceAsset.objects.create(
                migration=migration,
                asset_code=row.get("asset_code", ""),
                name=row.get("name", ""),
                category=row.get("category", ""),
                purchase_date=row.get("purchase_date"),
                cost=Decimal(str(row.get("cost", 0) or 0)),
                accumulated_depreciation=Decimal(
                    str(row.get("accumulated_depreciation", 0) or 0)
                ),
                useful_life=int(row["useful_life"]) if row.get("useful_life") else None,
                row_number=v["row"],
                status="imported",
            )
            success += 1
    return {"success": success, "errors": errors, "total": len(rows)}


def get_migration_summary(migration_id: UUID) -> dict:
    migration = OpeningBalanceMigration.objects.get(id=migration_id)
    gl_count = OpeningBalanceGL.objects.filter(
        migration=migration, status="imported"
    ).count()
    gl_errors = OpeningBalanceGL.objects.filter(
        migration=migration, status="error"
    ).count()
    ap_count = OpeningBalanceAP.objects.filter(
        migration=migration, status="imported"
    ).count()
    ap_errors = OpeningBalanceAP.objects.filter(
        migration=migration, status="error"
    ).count()
    ar_count = OpeningBalanceAR.objects.filter(
        migration=migration, status="imported"
    ).count()
    ar_errors = OpeningBalanceAR.objects.filter(
        migration=migration, status="error"
    ).count()
    inv_count = OpeningBalanceInventory.objects.filter(
        migration=migration, status="imported"
    ).count()
    inv_errors = OpeningBalanceInventory.objects.filter(
        migration=migration, status="error"
    ).count()
    asset_count = OpeningBalanceAsset.objects.filter(
        migration=migration, status="imported"
    ).count()
    asset_errors = OpeningBalanceAsset.objects.filter(
        migration=migration, status="error"
    ).count()

    gl_rows = OpeningBalanceGL.objects.filter(migration=migration)
    total_dr = sum(r.debit for r in gl_rows)
    total_cr = sum(r.credit for r in gl_rows)

    return {
        "go_live_date": migration.go_live_date.isoformat(),
        "status": migration.status,
        "gl": {
            "success": gl_count,
            "errors": gl_errors,
            "total_debit": float(total_dr),
            "total_credit": float(total_cr),
        },
        "ap": {"success": ap_count, "errors": ap_errors},
        "ar": {"success": ar_count, "errors": ar_errors},
        "inventory": {"success": inv_count, "errors": inv_errors},
        "assets": {"success": asset_count, "errors": asset_errors},
    }


def complete_migration(migration_id: UUID) -> dict:
    with transaction.atomic():
        migration = OpeningBalanceMigration.objects.select_for_update().get(
            id=migration_id
        )
        if migration.status != "draft":
            return {
                "success": False,
                "error": f"Cannot complete migration with status '{migration.status}'",
            }
        migration.status = "completed"
        migration.completed_at = timezone.now()
        migration.save(update_fields=["status", "completed_at"])
    return {"success": True, "status": "completed"}


def rollback_migration(migration_id: UUID) -> dict:
    with transaction.atomic():
        migration = OpeningBalanceMigration.objects.select_for_update().get(
            id=migration_id
        )
        if migration.status not in ("draft", "completed"):
            return {
                "success": False,
                "error": f"Cannot rollback migration with status '{migration.status}'",
            }
        OpeningBalanceGL.objects.filter(migration=migration).delete()
        OpeningBalanceAP.objects.filter(migration=migration).delete()
        OpeningBalanceAR.objects.filter(migration=migration).delete()
        OpeningBalanceInventory.objects.filter(migration=migration).delete()
        OpeningBalanceAsset.objects.filter(migration=migration).delete()
        migration.status = "rolled_back"
        migration.save(update_fields=["status"])
    return {"success": True, "deleted": True}


def get_company_migrations(company_id: UUID) -> list[OpeningBalanceMigration]:
    return list(
        OpeningBalanceMigration.objects.filter(company_id=company_id).order_by(
            "-created_at"
        )
    )
