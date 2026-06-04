"""Import service — CSV upload, validation, bulk import, rollback, templates."""

import csv
import io
import logging
from uuid import UUID

from django.apps import apps
from django.db import transaction
from django.utils import timezone

from apps.core.models import ImportHistory, ImportJob, ImportRow, ImportTemplate
from apps.core.services.column_mapper import apply_mapping, auto_detect_columns
from apps.core.services.validation_engine import (
    validate_fk_exists,
    validate_row,
    validate_row_warnings,
    validate_unique_in_db,
)

logger = logging.getLogger(__name__)

TEMPLATES = {
    "chart-of-accounts": {
        "name": "Chart of Accounts",
        "entity_type": "chart-of-accounts",
        "description": "Import chart of accounts from CSV",
        "column_definitions": [
            {
                "name": "code",
                "label": "Code",
                "type": "string",
                "rules": {"required": True, "max_length": 50},
            },
            {
                "name": "name",
                "label": "Name",
                "type": "string",
                "rules": {"required": True, "max_length": 200},
            },
            {
                "name": "type",
                "label": "Type",
                "type": "string",
                "rules": {"required": True},
            },
            {"name": "subtype", "label": "Subtype", "type": "string", "rules": {}},
            {
                "name": "parent_code",
                "label": "Parent Code",
                "type": "string",
                "rules": {},
            },
            {"name": "mfrs_code", "label": "MFRS Code", "type": "string", "rules": {}},
        ],
    },
    "items": {
        "name": "Items",
        "entity_type": "items",
        "description": "Import item master data from CSV",
        "column_definitions": [
            {
                "name": "code",
                "label": "Code",
                "type": "string",
                "rules": {"required": True, "max_length": 50},
            },
            {
                "name": "name",
                "label": "Name",
                "type": "string",
                "rules": {"required": True, "max_length": 200},
            },
            {"name": "category", "label": "Category", "type": "string", "rules": {}},
            {"name": "uom", "label": "UoM", "type": "string", "rules": {}},
            {"name": "tax_code", "label": "Tax Code", "type": "string", "rules": {}},
            {
                "name": "cost_method",
                "label": "Cost Method",
                "type": "string",
                "rules": {},
            },
            {
                "name": "selling_price",
                "label": "Selling Price",
                "type": "number",
                "rules": {},
            },
            {
                "name": "reorder_level",
                "label": "Reorder Level",
                "type": "number",
                "rules": {},
            },
        ],
    },
    "customers": {
        "name": "Customers",
        "entity_type": "customers",
        "description": "Import customer master data from CSV",
        "column_definitions": [
            {
                "name": "code",
                "label": "Code",
                "type": "string",
                "rules": {"required": True, "max_length": 50},
            },
            {
                "name": "name",
                "label": "Name",
                "type": "string",
                "rules": {"required": True, "max_length": 200},
            },
            {
                "name": "contact_person",
                "label": "Contact Person",
                "type": "string",
                "rules": {},
            },
            {
                "name": "email",
                "label": "Email",
                "type": "string",
                "rules": {"format": "email"},
            },
            {"name": "phone", "label": "Phone", "type": "string", "rules": {}},
            {"name": "sst_no", "label": "SST No", "type": "string", "rules": {}},
            {
                "name": "credit_limit",
                "label": "Credit Limit",
                "type": "number",
                "rules": {},
            },
            {
                "name": "payment_terms",
                "label": "Payment Terms",
                "type": "string",
                "rules": {},
            },
        ],
    },
    "vendors": {
        "name": "Vendors",
        "entity_type": "vendors",
        "description": "Import vendor master data from CSV",
        "column_definitions": [
            {
                "name": "code",
                "label": "Code",
                "type": "string",
                "rules": {"required": True, "max_length": 50},
            },
            {
                "name": "name",
                "label": "Name",
                "type": "string",
                "rules": {"required": True, "max_length": 200},
            },
            {
                "name": "contact_person",
                "label": "Contact Person",
                "type": "string",
                "rules": {},
            },
            {
                "name": "email",
                "label": "Email",
                "type": "string",
                "rules": {"format": "email"},
            },
            {"name": "phone", "label": "Phone", "type": "string", "rules": {}},
            {
                "name": "payment_terms",
                "label": "Payment Terms",
                "type": "string",
                "rules": {},
            },
        ],
    },
    "employees": {
        "name": "Employees",
        "entity_type": "employees",
        "description": "Import employee master data from CSV",
        "column_definitions": [
            {
                "name": "employee_no",
                "label": "Employee No",
                "type": "string",
                "rules": {"required": True},
            },
            {
                "name": "name",
                "label": "Name",
                "type": "string",
                "rules": {"required": True, "max_length": 200},
            },
            {"name": "ic_no", "label": "IC No", "type": "string", "rules": {}},
            {
                "name": "department",
                "label": "Department",
                "type": "string",
                "rules": {},
            },
            {
                "name": "designation",
                "label": "Designation",
                "type": "string",
                "rules": {},
            },
            {"name": "grade", "label": "Grade", "type": "string", "rules": {}},
            {
                "name": "joining_date",
                "label": "Joining Date",
                "type": "string",
                "rules": {"format": "date"},
            },
            {"name": "bank_name", "label": "Bank Name", "type": "string", "rules": {}},
            {
                "name": "bank_account",
                "label": "Bank Account",
                "type": "string",
                "rules": {},
            },
        ],
    },
    "fixed-assets": {
        "name": "Fixed Assets",
        "entity_type": "fixed-assets",
        "description": "Import fixed asset register from CSV",
        "column_definitions": [
            {
                "name": "asset_code",
                "label": "Asset Code",
                "type": "string",
                "rules": {"required": True},
            },
            {
                "name": "name",
                "label": "Name",
                "type": "string",
                "rules": {"required": True, "max_length": 200},
            },
            {"name": "category", "label": "Category", "type": "string", "rules": {}},
            {
                "name": "purchase_date",
                "label": "Purchase Date",
                "type": "string",
                "rules": {"format": "date"},
            },
            {
                "name": "cost",
                "label": "Cost",
                "type": "number",
                "rules": {"required": True},
            },
            {
                "name": "accumulated_depreciation",
                "label": "Accumulated Depreciation",
                "type": "number",
                "rules": {},
            },
        ],
    },
    "exchange-rates": {
        "name": "Exchange Rates",
        "entity_type": "exchange-rates",
        "description": "Import exchange rates from CSV",
        "column_definitions": [
            {
                "name": "source_currency",
                "label": "Source Currency",
                "type": "string",
                "rules": {"required": True, "max_length": 3},
            },
            {
                "name": "target_currency",
                "label": "Target Currency",
                "type": "string",
                "rules": {"required": True, "max_length": 3},
            },
            {
                "name": "rate",
                "label": "Rate",
                "type": "number",
                "rules": {"required": True},
            },
            {
                "name": "rate_date",
                "label": "Rate Date",
                "type": "string",
                "rules": {"format": "date"},
            },
        ],
    },
}


def seed_templates():
    """Upsert all predefined templates into the database."""
    for key, data in TEMPLATES.items():
        ImportTemplate.objects.update_or_create(
            entity_type=key,
            defaults={
                "name": data["name"],
                "description": data["description"],
                "column_definitions": data["column_definitions"],
                "is_active": True,
            },
        )


def list_templates() -> list[ImportTemplate]:
    return list(ImportTemplate.objects.filter(is_active=True).order_by("name"))


def get_template(entity_type: str) -> ImportTemplate | None:
    try:
        return ImportTemplate.objects.get(entity_type=entity_type, is_active=True)
    except ImportTemplate.DoesNotExist:
        return None


def generate_csv_template(entity_type: str) -> tuple[str, str] | None:
    """Generate a CSV template with headers for the given entity type.
    Returns (csv_content, filename) or None if not found.
    """
    template = get_template(entity_type)
    if not template:
        return None
    headers = [col["label"] for col in template.column_definitions]
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(headers)
    return output.getvalue(), f"{entity_type}_template.csv"


def parse_csv(file_content: str) -> tuple[list[str], list[dict[str, str]]]:
    """Parse CSV content. Returns (headers, rows)."""
    reader = csv.DictReader(io.StringIO(file_content))
    headers = reader.fieldnames or []
    rows = []
    for row in reader:
        rows.append({k.strip(): v.strip() for k, v in row.items() if k})
    return headers, rows


def _resolve_model_name(entity_type: str) -> str | None:
    """Map entity_type to a Django model name for import."""
    mapping = _MODEL_MAPPING
    return mapping.get(entity_type)


_MODEL_MAPPING: dict[str, str] = {
    "chart-of-accounts": "financial.Account",
    "items": "scm.Item",
    "customers": "crm.Customer",
    "vendors": "scm.Vendor",
    "employees": "hrm.Employee",
    "fixed-assets": "assets.FixedAsset",
    "exchange-rates": "financial.ExchangeRate",
}


def _resolve_entity_type_from_model(model_name: str) -> str | None:
    """Reverse map from Django model name (e.g. 'scm.Item') to entity_type (e.g. 'items')."""
    reverse_mapping = {v: k for k, v in _MODEL_MAPPING.items()}
    return reverse_mapping.get(model_name)


def get_template_by_page(page_key: str) -> ImportTemplate | None:
    """Find an import template matching the PageConfig's entity_model."""
    from apps.core.models import PageConfig

    try:
        config = PageConfig.objects.get(page_key=page_key)
    except PageConfig.DoesNotExist:
        return None
    if not config.entity_model:
        return None
    entity_type = _resolve_entity_type_from_model(config.entity_model)
    if not entity_type:
        return None
    return get_template(entity_type)


def create_job(
    template: ImportTemplate,
    file_name: str,
    user,
    company_id=None,
) -> ImportJob:
    return ImportJob.objects.create(
        template=template,
        file_name=file_name,
        uploaded_by=user,
        company_id=company_id,
        status="uploaded",
    )


def process_upload(
    job_id: UUID,
    file_content: str,
    column_mapping: dict[str, str] | None = None,
) -> dict:
    """Parse CSV, map columns, create ImportRow records, run validation.
    If column_mapping is None, auto-detect is attempted.
    """
    job = ImportJob.objects.get(id=job_id)
    template = job.template
    headers, rows = parse_csv(file_content)

    if column_mapping:
        mapping = column_mapping
    else:
        mapping = auto_detect_columns(headers, template.column_definitions)

    ImportJob.objects.filter(id=job.id).update(total_rows=len(rows))

    import_rows = []
    for i, row in enumerate(rows):
        mapped = apply_mapping(row, mapping)
        import_rows.append(
            ImportRow(
                job=job,
                row_number=i + 1,
                raw_data=row,
                mapped_data=mapped,
                status="pending",
            )
        )
    ImportRow.objects.bulk_create(import_rows)

    return {"total_rows": len(rows), "mapping": mapping}


def validate_job(job_id: UUID) -> dict:
    """Validate all rows of a job. Returns error/warning counts."""
    job = ImportJob.objects.get(id=job_id)
    template = job.template
    column_defs = template.column_definitions

    ImportJob.objects.filter(id=job.id).update(status="validating")

    rows = ImportRow.objects.filter(job=job)
    error_count = 0
    warning_count = 0

    model_name = _resolve_model_name(template.entity_type)

    for row in rows:
        errors = validate_row(row.mapped_data, column_defs)
        warnings = validate_row_warnings(row.mapped_data, column_defs)

        # Check unique constraints
        for col in column_defs:
            col_rules = col.get("rules", {})
            if col_rules.get("unique") and row.mapped_data.get(col["name"]):
                is_unique = validate_unique_in_db(
                    model_name, col["name"], row.mapped_data[col["name"]]
                )
                if not is_unique:
                    errors.append(
                        {
                            "field": col["name"],
                            "message": f"{col['name']} '{row.mapped_data[col['name']]}' already exists",
                        }
                    )

            # Check FK references
            fk_model = col_rules.get("fk_model")
            if fk_model and row.mapped_data.get(col["name"]):
                exists = validate_fk_exists(fk_model, row.mapped_data[col["name"]])
                if not exists:
                    errors.append(
                        {
                            "field": col["name"],
                            "message": f"Referenced {fk_model} '{row.mapped_data[col['name']]}' not found",
                        }
                    )

        if errors:
            row.status = "error"
            row.errors = errors
            error_count += 1
        else:
            row.status = "valid"
            if warnings:
                row.warnings = warnings
                warning_count += 1

        row.save(update_fields=["status", "errors", "warnings"])

    ImportJob.objects.filter(id=job.id).update(
        status="uploaded",
        error_count=error_count,
        warning_count=warning_count,
    )

    return {
        "total_rows": job.total_rows,
        "error_count": error_count,
        "warning_count": warning_count,
        "valid_count": job.total_rows - error_count,
    }


def import_job(job_id: UUID, user) -> dict:
    """Bulk import all valid rows. Creates records and tracks history."""
    job = ImportJob.objects.get(id=job_id)
    if job.status not in ("uploaded",):
        return {
            "success": False,
            "error": f"Cannot import job with status '{job.status}'",
        }

    ImportJob.objects.filter(id=job.id).update(
        status="importing", started_at=timezone.now()
    )

    valid_rows = ImportRow.objects.filter(job=job, status="valid")
    success_count = 0
    error_count = 0

    model_name = _resolve_model_name(job.template.entity_type)
    if model_name:
        try:
            Model = apps.get_model(model_name)
        except LookupError:
            for app_config in apps.get_app_configs():
                try:
                    Model = app_config.get_model(model_name.split(".")[-1])
                except LookupError:
                    continue
            else:
                ImportJob.objects.filter(id=job.id).update(
                    status="failed", error_log=f"Model '{model_name}' not found"
                )
                return {"success": False, "error": f"Model '{model_name}' not found"}

        with transaction.atomic():
            for row in valid_rows:
                try:
                    data = {
                        k: v for k, v in row.mapped_data.items() if v not in (None, "")
                    }
                    if hasattr(Model, "company_id") and job.company_id:
                        data["company_id"] = job.company_id
                    instance = Model.objects.create(**data)
                    row.status = "imported"
                    row.imported_record_id = instance.id
                    row.save(update_fields=["status", "imported_record_id"])
                    success_count += 1
                except Exception as e:
                    row.status = "error"
                    row.errors = row.errors + [{"message": str(e)}]
                    row.save(update_fields=["status", "errors"])
                    error_count += 1
                    logger.warning("Import row %d failed: %s", row.row_number, e)
    else:
        # No model mapped — just mark rows as imported for custom handling
        for row in valid_rows:
            row.status = "imported"
            row.save(update_fields=["status"])
            success_count += 1

    ImportJob.objects.filter(id=job.id).update(
        status="completed",
        success_count=success_count,
        error_count=job.error_count + error_count,
        completed_at=timezone.now(),
    )

    ImportHistory.objects.create(
        job=job,
        entity_type=job.template.entity_type,
        action="import",
        record_count=success_count,
        performed_by=user,
        notes=f"Imported {success_count} records, {error_count} errors",
    )

    return {
        "success": True,
        "success_count": success_count,
        "error_count": error_count,
        "total_rows": job.total_rows,
    }


def rollback_job(job_id: UUID, user) -> dict:
    """Delete all records imported by this job and mark as rolled back."""
    job = ImportJob.objects.get(id=job_id)
    if job.status != "completed":
        return {
            "success": False,
            "error": f"Cannot rollback job with status '{job.status}'",
        }

    imported_rows = ImportRow.objects.filter(job=job, status="imported")
    model_name = _resolve_model_name(job.template.entity_type)
    deleted_count = 0

    if model_name:
        try:
            Model = apps.get_model(model_name)
        except LookupError:
            for app_config in apps.get_app_configs():
                try:
                    Model = app_config.get_model(model_name.split(".")[-1])
                except LookupError:
                    continue
            else:
                return {"success": False, "error": f"Model '{model_name}' not found"}

        record_ids = [
            r.imported_record_id
            for r in imported_rows
            if r.imported_record_id is not None
        ]
        if record_ids:
            deleted, _ = Model.objects.filter(id__in=record_ids).delete()
            deleted_count = deleted

    for row in imported_rows:
        row.status = "skipped"
        row.save(update_fields=["status"])

    ImportJob.objects.filter(id=job.id).update(status="rolled_back")

    ImportHistory.objects.create(
        job=job,
        entity_type=job.template.entity_type,
        action="rollback",
        record_count=deleted_count,
        performed_by=user,
        notes=f"Rolled back {deleted_count} records",
    )

    return {"success": True, "deleted_count": deleted_count}


def get_job_status(job_id: UUID) -> ImportJob | None:
    try:
        return ImportJob.objects.prefetch_related("rows").get(id=job_id)
    except ImportJob.DoesNotExist:
        return None


def get_import_history(company_id=None, limit=50):
    qs = ImportHistory.objects.select_related("job", "performed_by").order_by(
        "-created_at"
    )
    if company_id:
        qs = qs.filter(job__company_id=company_id)
    return list(qs[:limit])
