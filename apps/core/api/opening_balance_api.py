"""Opening Balance Migration API — GL, AP, AR, inventory, asset opening balances."""

from ninja import Router, Schema
from ninja.errors import HttpError

from apps.core.models import OpeningBalanceGL
from apps.core.services import opening_balance_service

router = Router()


class MigrationCreateIn(Schema):
    go_live_date: str


class MigrationOut(Schema):
    id: str
    go_live_date: str
    status: str
    created_by_name: str
    completed_at: str | None = None

    @staticmethod
    def resolve_id(obj):
        return str(obj.id)

    @staticmethod
    def resolve_go_live_date(obj):
        return obj.go_live_date.isoformat() if obj.go_live_date else ""

    @staticmethod
    def resolve_created_by_name(obj):
        return obj.created_by.full_name if obj.created_by else ""


class ValidationOut(Schema):
    total_rows: int
    valid_count: int
    error_count: int
    rows: list


class ImportResultOut(Schema):
    success: int
    errors: int
    total: int


class SummaryOut(Schema):
    go_live_date: str
    status: str
    gl: dict
    ap: dict
    ar: dict
    inventory: dict
    assets: dict


class UploadResultOut(Schema):
    balance_type: str
    total_rows: int
    validation: list


def _get_company_id(request):
    cid = getattr(request.auth, "current_company_id", None)
    if not cid:
        raise HttpError(400, "No company selected")
    return cid


@router.post("/migrations/", response=MigrationOut)
def create_migration(request, data: MigrationCreateIn):
    """Create a new opening balance migration."""
    from datetime import datetime

    go_live = datetime.strptime(data.go_live_date, "%Y-%m-%d").date()
    return opening_balance_service.create_migration(
        company_id=_get_company_id(request),
        go_live_date=go_live,
        user=request.auth,
    )


@router.get("/migrations/{migration_id}/", response=MigrationOut)
def get_migration(request, migration_id: str):
    migration = opening_balance_service.get_migration(
        migration_id, _get_company_id(request)
    )
    if not migration:
        raise HttpError(404, "Migration not found")
    return migration


@router.get("/migrations/{migration_id}/summary/", response=SummaryOut)
def get_summary(request, migration_id: str):
    migration = opening_balance_service.get_migration(
        migration_id, _get_company_id(request)
    )
    if not migration:
        raise HttpError(404, "Migration not found")
    return opening_balance_service.get_migration_summary(migration_id)


@router.get("/migrations/", response=list[MigrationOut])
def list_migrations(request):
    return opening_balance_service.get_company_migrations(_get_company_id(request))


@router.post("/migrations/{migration_id}/complete/")
def complete_migration(request, migration_id: str):
    migration = opening_balance_service.get_migration(
        migration_id, _get_company_id(request)
    )
    if not migration:
        raise HttpError(404, "Migration not found")
    return opening_balance_service.complete_migration(migration_id)


@router.post("/migrations/{migration_id}/rollback/")
def rollback_migration(request, migration_id: str):
    migration = opening_balance_service.get_migration(
        migration_id, _get_company_id(request)
    )
    if not migration:
        raise HttpError(404, "Migration not found")
    return opening_balance_service.rollback_migration(migration_id)


@router.get("/templates/{balance_type}/csv/")
def download_csv_template(request, balance_type: str):
    """Download CSV template for a balance type (gl, ap, ar, inventory, asset)."""
    result = opening_balance_service.generate_csv_template(balance_type)
    if not result:
        raise HttpError(404, f"Unknown balance type: {balance_type}")
    from django.http import HttpResponse

    content, filename = result
    response = HttpResponse(content, content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


@router.post(
    "/migrations/{migration_id}/upload/{balance_type}/", response=UploadResultOut
)
def upload_csv(request, migration_id: str, balance_type: str):
    """Upload and validate CSV for a specific balance type (gl/ap/ar/inventory/asset)."""
    VALID_TYPES = {"gl", "ap", "ar", "inventory", "asset"}
    if balance_type not in VALID_TYPES:
        raise HttpError(
            400, f"Invalid balance type. Must be one of: {', '.join(VALID_TYPES)}"
        )

    migration = opening_balance_service.get_migration(
        migration_id, _get_company_id(request)
    )
    if not migration:
        raise HttpError(404, "Migration not found")

    uploaded = request.FILES.get("file")
    if not uploaded:
        raise HttpError(400, "No file provided")
    if not uploaded.name.endswith(".csv"):
        raise HttpError(400, "Only CSV files are supported")

    content = uploaded.read().decode("utf-8-sig")
    headers, rows = opening_balance_service.parse_csv(content)
    if not rows:
        raise HttpError(400, "CSV file is empty or has no data rows")

    validation = opening_balance_service.validate_rows(balance_type, rows)

    return {
        "balance_type": balance_type,
        "total_rows": len(rows),
        "validation": validation,
    }


@router.post(
    "/migrations/{migration_id}/import/{balance_type}/", response=ImportResultOut
)
def execute_import(request, migration_id: str, balance_type: str):
    """Execute import for a specific balance type after validation."""
    VALID_TYPES = {"gl", "ap", "ar", "inventory", "asset"}
    if balance_type not in VALID_TYPES:
        raise HttpError(400, "Invalid balance type")

    migration = opening_balance_service.get_migration(
        migration_id, _get_company_id(request)
    )
    if not migration:
        raise HttpError(404, "Migration not found")

    import_fns = {
        "gl": opening_balance_service.import_gl,
        "ap": opening_balance_service.import_ap,
        "ar": opening_balance_service.import_ar,
        "inventory": opening_balance_service.import_inventory,
        "asset": opening_balance_service.import_asset,
    }

    uploaded = request.FILES.get("file")
    if not uploaded:
        raise HttpError(400, "No file provided")
    content = uploaded.read().decode("utf-8-sig")
    _, rows = opening_balance_service.parse_csv(content)
    validation = opening_balance_service.validate_rows(balance_type, rows)
    return import_fns[balance_type](migration_id, rows, validation)


@router.post("/migrations/{migration_id}/validate-gl/")
def validate_gl(request, migration_id: str):
    """Check if GL debits = credits for this migration."""
    migration = opening_balance_service.get_migration(
        migration_id, _get_company_id(request)
    )
    if not migration:
        raise HttpError(404, "Migration not found")
    gl_rows = list(
        OpeningBalanceGL.objects.filter(migration=migration, status="imported").values()
    )
    rows = [{"debit": float(r["debit"]), "credit": float(r["credit"])} for r in gl_rows]
    return opening_balance_service.validate_gl_balance(rows)
