"""Report API — list, run, drill-down, export."""

import logging
from uuid import UUID

from django.http import StreamingHttpResponse
from ninja import Router, Schema
from ninja.errors import HttpError

from apps.core.api.auth import JWTAuth
from apps.financial.models import ReportDefinition, ReportExport, ReportParameter
from apps.financial.services.report_service import ReportService, ReportServiceError

logger = logging.getLogger(__name__)

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


class ColumnDef(Schema):
    key: str
    label: str
    type: str = "string"
    align: str = "left"
    format: str = ""
    width: str = ""


class ReportResult(Schema):
    columns: list[ColumnDef]
    rows: list[dict]
    total_rows: int
    page: int
    page_size: int
    generated_at: str
    summary: dict | None = None
    group_totals: list[dict] | None = None


class ReportDefinitionOut(Schema):
    id: str
    code: str
    name: str
    module: str
    category: str = ""
    compute_type: str
    pre_aggregated: bool = False
    supports_drill_down: bool = False
    group_field: str = ""
    show_subtotals: bool = True
    show_grand_total: bool = True
    page_size: int = 100
    is_active: bool = True

    @staticmethod
    def resolve_id(obj):
        return str(obj.id)


class ReportParameterOut(Schema):
    id: str
    key: str
    label: str
    param_type: str
    required: bool = False
    default_value: dict | list | str | int | bool | None = None
    options_source: str = ""
    validation: dict = {}
    sort_order: int = 0

    @staticmethod
    def resolve_id(obj):
        return str(obj.id)


class ExportResponse(Schema):
    export_id: str
    status: str
    download_url: str | None = None


class ExportStatusOut(Schema):
    id: str
    status: str
    format: str
    generated_at: str | None = None
    error_message: str = ""
    download_url: str | None = None


class ExportIn(Schema):
    format: str
    params: dict = {}


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/reports/", response=list[ReportDefinitionOut])
def list_reports(request, module: str = ""):
    """List available report definitions. Optionally filter by module."""
    _require_company_id(request)
    filters = {"is_active": True}
    if module:
        filters["module"] = module
    reports = ReportDefinition.objects.filter(**filters).order_by("module", "name")
    return list(reports)


@router.get("/reports/{code}/parameters/", response=list[ReportParameterOut])
def get_parameters(request, code: str):
    """Return parameter definitions for a report."""
    _require_company_id(request)
    try:
        report = ReportDefinition.objects.get(code=code, is_active=True)
    except ReportDefinition.DoesNotExist:
        raise HttpError(404, f"Report '{code}' not found") from None

    params = ReportParameter.objects.filter(report=report).order_by("sort_order")
    return list(params)


@router.get("/reports/{code}/", response=ReportResult)
def run_report(request, code: str, page: int = 1, page_size: int = 100):
    """Run a report with query parameters as filter values."""
    company_id = _require_company_id(request)

    params = dict(request.GET)
    params["page"] = page
    params["page_size"] = page_size
    # request.GET values are lists — extract single values
    params = {
        k: v[0] if isinstance(v, list) and len(v) == 1 else v for k, v in params.items()
    }

    try:
        result = ReportService().run(code, params, company_id)
        return result
    except ReportServiceError as e:
        raise HttpError(400, str(e)) from e


@router.get("/reports/{code}/drill-down/")
def drill_down(
    request, code: str, row_id: str = "", account_id: str = "", period_id: str = ""
):
    """Get drill-down detail for a report row."""
    company_id = _require_company_id(request)

    params = {}
    if account_id:
        params["account_id"] = account_id
    if period_id:
        params["period_id"] = period_id

    try:
        result = ReportService().drill_down(code, row_id, params, company_id)
        return {"results": result}
    except ReportServiceError as e:
        raise HttpError(400, str(e)) from e


@router.post("/reports/{code}/export/", response=ExportResponse)
def create_export(request, code: str, payload: ExportIn):
    """Create an async export. Stub — immediately marks as ready."""
    from django.utils import timezone

    company_id = _require_company_id(request)

    try:
        report = ReportDefinition.objects.get(code=code, is_active=True)
    except ReportDefinition.DoesNotExist:
        raise HttpError(404, f"Report '{code}' not found") from None

    import uuid

    export = ReportExport.objects.create(
        id=uuid.uuid4(),
        report=report,
        user=request.auth,
        company_id=company_id,
        format=payload.format,
        params=payload.params,
        status="generating",
        expires_at=timezone.now() + __import__("datetime").timedelta(days=1),
    )

    from apps.financial.services.export_service import generate_export

    generate_export(str(export.id))

    export.refresh_from_db()
    download_url = (
        f"/financial/exports/{export.id}/download" if export.status == "ready" else None
    )

    return {
        "export_id": str(export.id),
        "status": export.status,
        "download_url": download_url,
    }


@router.get("/exports/{id}/", response=ExportStatusOut)
def get_export_status(request, id: UUID):
    """Poll export generation status."""
    company_id = _require_company_id(request)
    try:
        export = ReportExport.objects.get(id=id, company_id=company_id)
        download_url = (
            f"/financial/exports/{id}/download" if export.status == "ready" else None
        )
        generated_at = export.generated_at.isoformat() if export.generated_at else None
        return {
            "id": str(export.id),
            "status": export.status,
            "format": export.format,
            "generated_at": generated_at,
            "error_message": export.error_message,
            "download_url": download_url,
        }
    except ReportExport.DoesNotExist:
        raise HttpError(404, "Export not found") from None


@router.get("/exports/{id}/download")
def download_export(request, id: UUID):
    """Download a completed export file."""
    company_id = _require_company_id(request)
    try:
        export = ReportExport.objects.get(id=id, company_id=company_id)
        if export.status != "ready" or not export.file:
            raise HttpError(400, "Export is not ready yet")
        return StreamingHttpResponse(
            export.file,
            content_type="text/csv",
            headers={
                "Content-Disposition": f'attachment; filename="{export.file.name}"'
            },
        )
    except ReportExport.DoesNotExist:
        raise HttpError(404, "Export not found") from None
