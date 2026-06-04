"""Transaction migration service — import pending PO/SO/GRN and historical journals/invoices."""

from __future__ import annotations

import csv
import io
import logging
from datetime import date
from uuid import UUID

from django.db import transaction
from django.utils import timezone

from apps.core.models import TransactionMigration, TransactionMigrationLine

logger = logging.getLogger(__name__)

LINE_TYPE_CONFIG = {
    "pending_po": {
        "label": "Pending Purchase Orders",
        "required_fields": [
            "po_number",
            "supplier_code",
            "item_code",
            "quantity",
            "unit_price",
        ],
        "optional_fields": ["order_date", "expected_date", "currency", "description"],
    },
    "pending_so": {
        "label": "Pending Sales Orders",
        "required_fields": [
            "so_number",
            "customer_code",
            "item_code",
            "quantity",
            "unit_price",
        ],
        "optional_fields": ["order_date", "required_date", "currency", "description"],
    },
    "pending_grn": {
        "label": "Pending Goods Receipt Notes",
        "required_fields": [
            "grn_number",
            "po_number",
            "item_code",
            "quantity_received",
        ],
        "optional_fields": ["received_date", "supplier_code", "remarks"],
    },
    "historical_journal": {
        "label": "Historical Journal Entries",
        "required_fields": [
            "entry_number",
            "date",
            "account_code",
            "description",
            "debit",
            "credit",
        ],
        "optional_fields": ["period", "currency"],
    },
    "historical_ap_invoice": {
        "label": "Historical AP Invoices",
        "required_fields": [
            "supplier_code",
            "invoice_no",
            "invoice_date",
            "due_date",
            "amount",
        ],
        "optional_fields": ["currency", "status", "description"],
    },
    "historical_ar_invoice": {
        "label": "Historical AR Invoices",
        "required_fields": [
            "customer_code",
            "invoice_no",
            "invoice_date",
            "due_date",
            "amount",
        ],
        "optional_fields": ["currency", "status", "description"],
    },
}

VALID_LINE_TYPES = set(LINE_TYPE_CONFIG.keys())


# ---------------------------------------------------------------------------
# Migration CRUD
# ---------------------------------------------------------------------------


def create_migration(
    company_id: UUID,
    go_live_date: date,
    migration_option: str = "fresh",
    opening_migration_id: UUID | None = None,
    user_id: UUID | None = None,
) -> TransactionMigration:
    if migration_option not in ("fresh", "full"):
        raise ValueError("migration_option must be 'fresh' or 'full'")
    return TransactionMigration.objects.create(
        company_id=company_id,
        go_live_date=go_live_date,
        migration_option=migration_option,
        opening_migration_id=opening_migration_id,
        created_by_id=user_id,
        status="draft",
    )


def get_migration(migration_id: UUID, company_id: UUID) -> TransactionMigration | None:
    try:
        return TransactionMigration.objects.get(id=migration_id, company_id=company_id)
    except TransactionMigration.DoesNotExist:
        return None


def get_company_migrations(company_id: UUID) -> list[TransactionMigration]:
    return list(
        TransactionMigration.objects.filter(company_id=company_id).order_by(
            "-created_at"
        )
    )


def get_migration_summary(migration_id: UUID) -> dict:
    migration = TransactionMigration.objects.get(id=migration_id)
    lines = TransactionMigrationLine.objects.filter(migration=migration)
    by_type: dict[str, dict] = {}
    for line_type, cfg in LINE_TYPE_CONFIG.items():
        qs = lines.filter(line_type=line_type)
        by_type[line_type] = {
            "label": cfg["label"],
            "total": qs.count(),
            "valid": qs.filter(status="valid").count(),
            "error": qs.filter(status="error").count(),
            "imported": qs.filter(status="imported").count(),
        }
    return {
        "migration_id": str(migration.id),
        "company_id": str(migration.company_id),
        "migration_option": migration.migration_option,
        "go_live_date": migration.go_live_date.isoformat(),
        "status": migration.status,
        "line_types": by_type,
    }


# ---------------------------------------------------------------------------
# CSV Parsing
# ---------------------------------------------------------------------------


def parse_csv(content: str) -> tuple[list[str], list[dict]]:
    reader = csv.DictReader(io.StringIO(content))
    rows = []
    for row in reader:
        cleaned = {k.strip(): v.strip() for k, v in row.items() if k and k.strip()}
        rows.append(cleaned)
    return reader.fieldnames or [], rows


def generate_csv_template(line_type: str) -> str:
    cfg = LINE_TYPE_CONFIG.get(line_type)
    if cfg is None:
        raise ValueError(f"Unknown line type: {line_type}")
    fields = cfg["required_fields"] + cfg["optional_fields"]
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(fields)
    writer.writerow([f"<{f}>" for f in fields])
    return output.getvalue()


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def validate_rows(line_type: str, rows: list[dict]) -> list[dict]:
    cfg = LINE_TYPE_CONFIG.get(line_type)
    if cfg is None:
        raise ValueError(f"Unknown line type: {line_type}")

    results = []
    for i, row in enumerate(rows):
        errors = []
        for field in cfg["required_fields"]:
            val = row.get(field, "")
            if not val:
                errors.append(f"Missing required field: {field}")
        if line_type == "historical_journal":
            try:
                float(row.get("debit", 0) or 0)
                float(row.get("credit", 0) or 0)
            except (ValueError, TypeError):
                errors.append("debit and credit must be numeric")
        if errors:
            results.append(
                {"row_number": i, "raw_data": row, "status": "error", "errors": errors}
            )
        else:
            results.append(
                {"row_number": i, "raw_data": row, "status": "valid", "errors": []}
            )
    return results


# ---------------------------------------------------------------------------
# Import
# ---------------------------------------------------------------------------


@transaction.atomic
def import_lines(
    migration_id: UUID, line_type: str, rows: list[dict], validation: list[dict]
) -> dict:
    if line_type not in VALID_LINE_TYPES:
        raise ValueError(f"Invalid line type: {line_type}")

    migration = TransactionMigration.objects.select_for_update().get(id=migration_id)
    migration.status = "in_progress"
    migration.save(update_fields=["status"])

    TransactionMigrationLine.objects.filter(
        migration=migration, line_type=line_type
    ).delete()

    created = 0
    for v in validation:
        TransactionMigrationLine.objects.create(
            migration=migration,
            line_type=line_type,
            row_number=v["row_number"],
            raw_data=v["raw_data"],
            data=rows[v["row_number"]] if v["row_number"] < len(rows) else {},
            status=v["status"],
            errors=v["errors"],
        )
        created += 1

    return {
        "migration_id": str(migration.id),
        "line_type": line_type,
        "total_rows": len(validation),
        "valid_count": sum(1 for v in validation if v["status"] == "valid"),
        "error_count": sum(1 for v in validation if v["status"] == "error"),
    }


# ---------------------------------------------------------------------------
# Migration lifecycle
# ---------------------------------------------------------------------------


@transaction.atomic
def complete_migration(migration_id: UUID) -> dict:
    migration = TransactionMigration.objects.select_for_update().get(id=migration_id)
    if migration.status == "completed":
        raise ValueError("Migration is already completed")
    if migration.status == "rolled_back":
        raise ValueError("Cannot complete a rolled-back migration")

    migration.status = "completed"
    migration.completed_at = timezone.now()
    migration.save(update_fields=["status", "completed_at"])

    return {
        "migration_id": str(migration.id),
        "status": "completed",
        "completed_at": migration.completed_at.isoformat(),
    }


@transaction.atomic
def rollback_migration(migration_id: UUID) -> dict:
    migration = TransactionMigration.objects.select_for_update().get(id=migration_id)
    if migration.status == "rolled_back":
        raise ValueError("Migration is already rolled back")

    TransactionMigrationLine.objects.filter(migration=migration).update(
        status="rolled_back"
    )
    migration.status = "rolled_back"
    migration.save(update_fields=["status"])

    return {
        "migration_id": str(migration.id),
        "status": "rolled_back",
    }
