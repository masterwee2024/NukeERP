"""Import API — CSV upload, validation, import execution, rollback, templates."""

from ninja import Router, Schema
from ninja.errors import HttpError

from apps.core.models import ImportJob
from apps.core.services import import_service

router = Router()


# ── Schemas ──────────────────────────────────────────────────────


class TemplateOut(Schema):
    id: str
    name: str
    entity_type: str
    description: str
    column_definitions: list

    @staticmethod
    def resolve_id(obj):
        return str(obj.id)


class JobOut(Schema):
    id: str
    template_name: str
    file_name: str
    status: str
    total_rows: int
    success_count: int
    error_count: int
    warning_count: int
    started_at: str | None = None
    completed_at: str | None = None

    @staticmethod
    def resolve_id(obj):
        return str(obj.id)

    @staticmethod
    def resolve_template_name(obj):
        return obj.template.name if obj.template else ""


class UploadResult(Schema):
    total_rows: int
    mapping: dict


class ValidationResult(Schema):
    total_rows: int
    error_count: int
    warning_count: int
    valid_count: int


class ImportResult(Schema):
    success: bool
    success_count: int = 0
    error_count: int = 0
    total_rows: int = 0
    error: str = ""


class RollbackResult(Schema):
    success: bool
    deleted_count: int = 0
    error: str = ""


class RowOut(Schema):
    id: str
    row_number: int
    raw_data: dict
    mapped_data: dict
    status: str
    errors: list
    warnings: list
    imported_record_id: str | None = None

    @staticmethod
    def resolve_id(obj):
        return str(obj.id)

    @staticmethod
    def resolve_imported_record_id(obj):
        return str(obj.imported_record_id) if obj.imported_record_id else None


class JobDetailOut(Schema):
    id: str
    template_name: str
    file_name: str
    status: str
    total_rows: int
    success_count: int
    error_count: int
    warning_count: int
    started_at: str | None = None
    completed_at: str | None = None
    error_log: str = ""
    rows: list[RowOut] = []

    @staticmethod
    def resolve_id(obj):
        return str(obj.id)

    @staticmethod
    def resolve_template_name(obj):
        return obj.template.name if obj.template else ""


class HistoryOut(Schema):
    id: str
    entity_type: str
    action: str
    record_count: int
    performed_by_name: str
    notes: str
    created_at: str

    @staticmethod
    def resolve_id(obj):
        return str(obj.id)

    @staticmethod
    def resolve_performed_by_name(obj):
        return obj.performed_by.full_name if obj.performed_by else "System"


class ColumnMappingIn(Schema):
    mapping: dict[str, str]


class UploadResponse(Schema):
    job_id: str
    total_rows: int
    mapping: dict


def _get_job(request, job_id: str) -> ImportJob:
    """Get an import job scoped to the user's current company."""
    company_id = getattr(request.user, "current_company_id", None)
    qs = ImportJob.objects.all()
    if company_id:
        qs = qs.filter(company_id=company_id)
    try:
        return qs.get(id=job_id)
    except ImportJob.DoesNotExist:
        raise HttpError(404, "Job not found") from None


# ── Endpoints


@router.get("/templates/", response=list[TemplateOut])
def list_templates(request):
    """List all available import templates."""
    return import_service.list_templates()


@router.get("/templates/by-page/{page_key}/", response=TemplateOut)
def get_template_by_page(request, page_key: str):
    """Get the import template matching a PageConfig's entity_model."""
    template = import_service.get_template_by_page(page_key)
    if not template:
        raise HttpError(404, "No import template found for this page")
    return template


@router.get("/templates/{entity_type}/", response=TemplateOut)
def get_template(request, entity_type: str):
    """Get a specific template with column definitions."""
    template = import_service.get_template(entity_type)
    if not template:
        raise HttpError(404, "Template not found")
    return template


@router.get("/templates/{entity_type}/csv/")
def download_csv_template(request, entity_type: str):
    """Download a CSV template file."""
    result = import_service.generate_csv_template(entity_type)
    if not result:
        raise HttpError(404, "Template not found")
    from django.http import HttpResponse

    content, filename = result
    response = HttpResponse(content, content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


@router.post("/upload/", response=UploadResponse)
def upload_csv(request):
    """Upload a CSV file for import."""
    entity_type = request.POST.get("entity_type") or request.GET.get("entity_type")
    if not entity_type:
        raise HttpError(400, "entity_type is required")

    template = import_service.get_template(entity_type)
    if not template:
        raise HttpError(404, f"Template '{entity_type}' not found")

    uploaded = request.FILES.get("file")
    if not uploaded:
        raise HttpError(400, "No file provided")
    if not uploaded.name.endswith(".csv"):
        raise HttpError(400, "Only CSV files are supported")

    content = uploaded.read().decode("utf-8-sig")
    job = import_service.create_job(
        template=template,
        file_name=uploaded.name,
        user=request.auth,
        company_id=getattr(request.user, "current_company_id", None),
    )
    result = import_service.process_upload(job.id, content)
    return {
        "job_id": str(job.id),
        "total_rows": result["total_rows"],
        "mapping": result["mapping"],
    }


@router.post("/upload/{job_id}/map/")
def update_column_mapping(request, job_id: str, data: ColumnMappingIn):
    """Update column mapping for a job (manual mapping)."""
    job = _get_job(request, job_id)
    template = job.template
    from apps.core.services.column_mapper import manual_map

    valid_mapping = manual_map(data.mapping, template.column_definitions)

    from apps.core.models import ImportRow

    rows = ImportRow.objects.filter(job=job)
    for row in rows:
        from apps.core.services.column_mapper import apply_mapping

        row.mapped_data = apply_mapping(row.raw_data, valid_mapping)
        row.save(update_fields=["mapped_data"])
    return {"mapping": valid_mapping}


@router.post("/jobs/{job_id}/validate/", response=ValidationResult)
def validate_job(request, job_id: str):
    """Validate all rows of an import job."""
    _get_job(request, job_id)
    return import_service.validate_job(job_id)


@router.post("/jobs/{job_id}/import/", response=ImportResult)
def execute_import(request, job_id: str):
    """Execute import for valid rows."""
    _get_job(request, job_id)
    return import_service.import_job(job_id, request.auth)


@router.post("/jobs/{job_id}/rollback/", response=RollbackResult)
def rollback_import(request, job_id: str):
    """Rollback an import — delete imported records."""
    _get_job(request, job_id)
    return import_service.rollback_job(job_id, request.auth)


@router.get("/jobs/{job_id}/", response=JobDetailOut)
def get_job_status(request, job_id: str):
    """Get import job status and row details."""
    job = _get_job(request, job_id)
    return job


@router.get("/history/", response=list[HistoryOut])
def get_import_history(request):
    """Get import history."""
    company_id = getattr(request.user, "current_company_id", None)
    return import_service.get_import_history(company_id=company_id)
