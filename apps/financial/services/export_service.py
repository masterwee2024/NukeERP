"""Export service — CSV, HTML (PDF/Excel fallback)."""

import csv
import io
import logging
from html import escape

from django.http import StreamingHttpResponse

from apps.financial.models import ReportExport
from apps.financial.services.report_service import ReportService

logger = logging.getLogger(__name__)

CONTENT_TYPES = {
    "csv": "text/csv",
    "pdf": "text/html",
    "xlsx": "text/html",
}

FILE_EXTENSIONS = {
    "csv": "csv",
    "pdf": "html",
    "xlsx": "html",
}


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
    """Generate an export file.

    CSV → real CSV
    PDF → HTML table (renders in browser, print-to-PDF)
    XLSX → HTML table (Excel can open .xls HTML)
    """

    try:
        export = ReportExport.objects.select_related("report").get(id=export_id)
        if export.format == "csv":
            _generate_csv_export(export)
        else:
            _generate_html_export(export)
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
    ext = FILE_EXTENSIONS[export.format]
    export.file.save(f"{export.report.code}_{export.id}.{ext}", ContentFile(content))
    export.status = "ready"
    export.generated_at = None
    from django.utils import timezone

    export.generated_at = timezone.now()
    export.save(update_fields=["status", "generated_at", "file", "updated_at"])


def _generate_html_export(export: ReportExport):
    """Generate an HTML table export (fallback for PDF/XLSX stubs)."""
    from django.core.files.base import ContentFile

    from apps.financial.models import FinancialPeriod

    data = ReportService().run(export.report.code, export.params, export.company_id)
    cols = data["columns"]

    # Resolve period names from UUIDs in params
    period_names = []
    for key in ("period_from", "period_to"):
        pid = export.params.get(key)
        if pid:
            try:
                p = FinancialPeriod.objects.get(id=pid)
                period_names.append(p.name)
            except Exception:
                period_names.append(str(pid))
    period_label = " — ".join(period_names) if period_names else ""

    generated_label = (
        export.generated_at.strftime("%Y-%m-%d %H:%M") if export.generated_at else "N/A"
    )

    html_parts = ["<!DOCTYPE html><html><head><meta charset='utf-8'>"]
    html_parts.append(f"<title>{escape(export.report.name)}</title>")
    html_parts.append("<style>")
    html_parts.append("body{font-family:sans-serif;margin:2rem}")
    html_parts.append("h1{font-size:1.25rem;color:#333;margin-bottom:0.25rem}")
    html_parts.append(".meta{font-size:0.8rem;color:#666;margin-bottom:0.25rem}")
    html_parts.append("table{border-collapse:collapse;width:100%;margin-top:1rem}")
    html_parts.append(
        "th,td{border:1px solid #ccc;padding:6px 10px;text-align:left;font-size:0.875rem}"
    )
    html_parts.append("th{background:#f5f5f5;font-weight:600}")
    html_parts.append("tr:nth-child(even){background:#fafafa}")
    html_parts.append(
        ".footer{border-top:1px solid #ddd;margin-top:1.5rem;padding-top:0.75rem;font-size:0.75rem;color:#999;text-align:center}"
    )
    html_parts.append("</style></head><body>")

    # Header
    html_parts.append(f"<h1>{escape(export.report.name)}</h1>")
    if period_label:
        html_parts.append(f"<p class='meta'>Period: {escape(period_label)}</p>")
    html_parts.append(
        f"<p class='meta'>Generated: {generated_label} &mdash; {len(data['rows'])} rows</p>"
    )

    # Table
    html_parts.append("<table><thead><tr>")
    for c in cols:
        html_parts.append(f"<th>{escape(c['label'])}</th>")
    html_parts.append("</tr></thead><tbody>")
    for row in data["rows"]:
        html_parts.append("<tr>")
        for c in cols:
            val = row.get(c["key"], "")
            html_parts.append(f"<td>{escape(str(val))}</td>")
        html_parts.append("</tr>")
    html_parts.append("</tbody></table>")

    # Footer
    html_parts.append(
        "<div class='footer'>End of Report &mdash; "
        f"{len(data['rows'])} rows &mdash; Generated {generated_label}</div>"
    )
    html_parts.append("</body></html>")

    content = "".join(html_parts).encode("utf-8")
    ext = FILE_EXTENSIONS[export.format]
    export.file.save(f"{export.report.code}_{export.id}.{ext}", ContentFile(content))
    export.status = "ready"
    from django.utils import timezone

    export.generated_at = timezone.now()
    export.save(update_fields=["status", "generated_at", "file", "updated_at"])
