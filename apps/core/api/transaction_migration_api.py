"""Transaction migration API endpoints."""

from datetime import datetime

from ninja import Router, Schema
from ninja.errors import HttpError

from apps.core.services.transaction_migration_service import (
    LINE_TYPE_CONFIG,
    complete_migration,
    create_migration,
    generate_csv_template,
    get_company_migrations,
    get_migration,
    get_migration_summary,
    import_lines,
    parse_csv,
    rollback_migration,
    validate_rows,
)

router = Router()


class MigrationCreateIn(Schema):
    go_live_date: str
    migration_option: str = "fresh"
    opening_migration_id: str | None = None
    notes: str = ""


class MigrationOut(Schema):
    id: str
    company_id: str
    go_live_date: str
    migration_option: str
    status: str
    completed_at: str | None = None
    notes: str = ""


class SummaryOut(Schema):
    migration_id: str
    company_id: str
    migration_option: str
    go_live_date: str
    status: str
    line_types: dict


class ImportResultOut(Schema):
    migration_id: str
    line_type: str
    total_rows: int
    valid_count: int
    error_count: int


class TemplateOut(Schema):
    line_type: str
    label: str
    csv_content: str


def _get_company_id(request):
    cid = getattr(request.auth, "current_company_id", None)
    if not cid:
        raise HttpError(400, "No company selected")
    return cid


# ── Migration CRUD ──


@router.post("/migrations/", response=MigrationOut)
def create_migration_endpoint(request, data: MigrationCreateIn):
    go_live = datetime.strptime(data.go_live_date, "%Y-%m-%d").date()
    migration = create_migration(
        company_id=_get_company_id(request),
        go_live_date=go_live,
        migration_option=data.migration_option,
        opening_migration_id=data.opening_migration_id,
        user_id=request.auth.id,
    )
    return MigrationOut(
        id=str(migration.id),
        company_id=str(migration.company_id),
        go_live_date=migration.go_live_date.isoformat(),
        migration_option=migration.migration_option,
        status=migration.status,
        notes=migration.notes,
    )


@router.get("/migrations/", response=list[MigrationOut])
def list_migrations(request):
    ms = get_company_migrations(_get_company_id(request))
    return [
        MigrationOut(
            id=str(m.id),
            company_id=str(m.company_id),
            go_live_date=m.go_live_date.isoformat(),
            migration_option=m.migration_option,
            status=m.status,
            notes=m.notes,
        )
        for m in ms
    ]


@router.get("/migrations/{migration_id}/", response=MigrationOut)
def get_migration_endpoint(request, migration_id: str):
    m = get_migration(migration_id, _get_company_id(request))
    if m is None:
        raise HttpError(404, "Migration not found")
    return MigrationOut(
        id=str(m.id),
        company_id=str(m.company_id),
        go_live_date=m.go_live_date.isoformat(),
        migration_option=m.migration_option,
        status=m.status,
        notes=m.notes,
    )


@router.get("/migrations/{migration_id}/summary/", response=SummaryOut)
def get_summary(request, migration_id: str):
    m = get_migration(migration_id, _get_company_id(request))
    if m is None:
        raise HttpError(404, "Migration not found")
    return get_migration_summary(migration_id)


# ── Import ──


@router.post("/migrations/{migration_id}/upload/{line_type}/", response=ImportResultOut)
def upload_and_validate(request, migration_id: str, line_type: str):
    if line_type not in LINE_TYPE_CONFIG:
        raise HttpError(400, f"Invalid line type: {line_type}")
    m = get_migration(migration_id, _get_company_id(request))
    if m is None:
        raise HttpError(404, "Migration not found")

    uploaded = request.FILES.get("file")
    if not uploaded:
        raise HttpError(400, "No file provided")
    if not uploaded.name.endswith(".csv"):
        raise HttpError(400, "Only CSV files are supported")

    content = uploaded.read().decode("utf-8-sig")
    _, rows = parse_csv(content)
    if not rows:
        raise HttpError(400, "CSV file is empty or has no data rows")

    validation = validate_rows(line_type, rows)
    result = import_lines(migration_id, line_type, rows, validation)
    return ImportResultOut(**result)


@router.get("/templates/{line_type}/", response=TemplateOut)
def get_template(request, line_type: str):
    cfg = LINE_TYPE_CONFIG.get(line_type)
    if cfg is None:
        raise HttpError(404, f"Unknown line type: {line_type}")
    csv_content = generate_csv_template(line_type)
    return TemplateOut(line_type=line_type, label=cfg["label"], csv_content=csv_content)


# ── Migration lifecycle ──


@router.post("/migrations/{migration_id}/complete/")
def complete_migration_endpoint(request, migration_id: str):
    m = get_migration(migration_id, _get_company_id(request))
    if m is None:
        raise HttpError(404, "Migration not found")
    try:
        return complete_migration(migration_id)
    except ValueError as e:
        raise HttpError(400, str(e)) from e


@router.post("/migrations/{migration_id}/rollback/")
def rollback_migration_endpoint(request, migration_id: str):
    m = get_migration(migration_id, _get_company_id(request))
    if m is None:
        raise HttpError(404, "Migration not found")
    try:
        return rollback_migration(migration_id)
    except ValueError as e:
        raise HttpError(400, str(e)) from e
