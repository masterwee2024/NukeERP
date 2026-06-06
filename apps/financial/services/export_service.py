"""Export service — CSV streaming, PDF stub."""

import csv
import io
import logging

from django.http import StreamingHttpResponse

from apps.financial.models import ReportExport
from apps.financial.services.report_service import ReportService

logger = logging.getLogger(__name__)


def stream_csv(report_code: str, params: dict, user) -> StreamingHttpResponse:
    """Stream report data as CSV with a StreamingHttpResponse."""
    data = ReportService().run(report_code, params, user)

    pseudo_buffer = io.StringIO()
    writer = csv.writer(pseudo_buffer)

    def generate():
        headers = [c["label"] for c in data["columns"]]
        pseudo_buffer.seek(0)
        pseudo_buffer.truncate(0)
        writer.writerow(headers)
        yield pseudo_buffer.getvalue()

        for row in data["rows"]:
            pseudo_buffer.seek(0)
            pseudo_buffer.truncate(0)
            writer.writerow(str(row.get(c["key"], "")) for c in data["columns"])
            yield pseudo_buffer.getvalue()

    response = StreamingHttpResponse(generate(), content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="{report_code}.csv"'
    return response


def generate_export(export_id: str):
    """Generate an export. Stub — sets status to 'ready' immediately.

    In production, this would be a Celery task. For now, CSV is synchronous
    and PDF is a placeholder.
    """

    try:
        export = ReportExport.objects.select_related("report").get(id=export_id)
        if export.format == "csv":
            _generate_csv_export(export)
        elif export.format == "pdf":
            _generate_pdf_stub(export)
        elif export.format == "xlsx":
            _generate_xlsx_stub(export)
    except Exception as e:
        logger.exception("Export generation failed for %s", export_id)
        ReportExport.objects.filter(id=export_id).update(
            status="failed",
            error_message=str(e),
        )


def _generate_csv_export(export: ReportExport):
    """Generate CSV content inline for a ReportExport record."""
    from django.core.files.base import ContentFile

    data = ReportService().run(export.report.code, export.params, export.company_id)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([c["label"] for c in data["columns"]])
    for row in data["rows"]:
        writer.writerow(str(row.get(c["key"], "")) for c in data["columns"])

    content = output.getvalue().encode("utf-8-sig")
    export.file.save(f"{export.report.code}_{export.id}.csv", ContentFile(content))
    export.status = "ready"
    export.generated_at = None
    from django.utils import timezone

    export.generated_at = timezone.now()
    export.save(update_fields=["status", "generated_at", "file", "updated_at"])


def _generate_pdf_stub(export: ReportExport):
    """Placeholder for PDF generation."""
    from django.utils import timezone

    export.status = "ready"
    export.generated_at = timezone.now()
    export.save(update_fields=["status", "generated_at", "updated_at"])


def _generate_xlsx_stub(export: ReportExport):
    """Placeholder for Excel generation."""
    from django.utils import timezone

    export.status = "ready"
    export.generated_at = timezone.now()
    export.save(update_fields=["status", "generated_at", "updated_at"])
