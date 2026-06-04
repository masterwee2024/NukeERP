"""Validation engine for CSV data import — validates rows against template column rules."""

import re
from datetime import datetime
from uuid import UUID

from django.apps import apps


def validate_row(row: dict, column_defs: list[dict]) -> list[dict]:
    """Validate a single mapped row against column definitions.
    Returns a list of error dicts: [{field, message}]
    """
    errors = []
    for col in column_defs:
        field_name = col["name"]
        value = row.get(field_name, "")
        rules = col.get("rules", {})
        _validate_required(field_name, value, rules, errors)
        if value is not None and value != "":
            _validate_type(field_name, value, col, rules, errors)
            _validate_format(field_name, value, col, rules, errors)
            _validate_max_length(field_name, value, rules, errors)
    return errors


def validate_row_warnings(row: dict, column_defs: list[dict]) -> list[dict]:
    """Non-blocking warnings — e.g. potential duplicates."""
    warnings = []
    for col in column_defs:
        rules = col.get("rules", {})
        if rules.get("unique"):
            pass  # uniqueness is validated in import_service against DB
    return warnings


def _validate_required(field_name: str, value, rules: dict, errors: list) -> None:
    if rules.get("required", False) and (value is None or str(value).strip() == ""):
        errors.append({"field": field_name, "message": f"{field_name} is required"})


def _validate_type(
    field_name: str, value, col: dict, rules: dict, errors: list
) -> None:
    col_type = col.get("type", "string")
    if col_type == "number":
        try:
            float(value)
        except (ValueError, TypeError):
            errors.append(
                {"field": field_name, "message": f"{field_name} must be a number"}
            )
    elif col_type == "integer":
        try:
            int(value)
        except (ValueError, TypeError):
            errors.append(
                {"field": field_name, "message": f"{field_name} must be an integer"}
            )
    elif col_type == "boolean":
        if str(value).lower() not in ("true", "false", "1", "0", "yes", "no", ""):
            errors.append(
                {"field": field_name, "message": f"{field_name} must be true/false"}
            )
    elif col_type == "email":
        if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", str(value)):
            errors.append(
                {"field": field_name, "message": f"{field_name} is not a valid email"}
            )


def _validate_format(
    field_name: str, value, col: dict, rules: dict, errors: list
) -> None:
    fmt = rules.get("format")
    if fmt == "date":
        for pattern in ("%d/%m/%Y", "%Y-%m-%d", "%m/%d/%Y"):
            try:
                datetime.strptime(str(value), pattern)
                return
            except ValueError:
                continue
        errors.append(
            {
                "field": field_name,
                "message": f"{field_name} is not a valid date (expected DD/MM/YYYY)",
            }
        )
    elif fmt == "amount":
        try:
            val = str(value).replace(",", "").replace(" ", "")
            float(val)
        except (ValueError, TypeError):
            errors.append(
                {"field": field_name, "message": f"{field_name} is not a valid amount"}
            )
    elif fmt == "email":
        if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", str(value)):
            errors.append(
                {"field": field_name, "message": f"{field_name} is not a valid email"}
            )


def _validate_max_length(field_name: str, value, rules: dict, errors: list) -> None:
    max_len = rules.get("max_length")
    if max_len and len(str(value)) > max_len:
        errors.append(
            {
                "field": field_name,
                "message": f"{field_name} exceeds max length of {max_len}",
            }
        )


def validate_unique_in_db(
    model_name: str, field_name: str, value, company_id=None
) -> bool:
    """Check if a value is unique across existing records in the DB."""
    try:
        Model = apps.get_model(model_name)
    except LookupError:
        return True
    filters = {field_name: value}
    if company_id:
        filters["company_id"] = company_id
    return not Model.objects.filter(**filters).exists()


def validate_fk_exists(model_name: str, field_value) -> bool:
    """Check if a foreign key reference exists."""
    if not field_value or str(field_value).strip() == "":
        return True
    try:
        Model = apps.get_model(model_name)
    except LookupError:
        return True
    try:
        if isinstance(field_value, str):
            try:
                UUID(field_value)
                Model.objects.get(id=field_value)
            except (ValueError, Model.DoesNotExist):
                return False
        else:
            Model.objects.get(pk=field_value)
        return True
    except Model.DoesNotExist:
        return False
