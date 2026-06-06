"""Report engine service — compute, cache, paginate, drill-down."""

import hashlib
import json
import logging
from datetime import UTC, datetime
from uuid import UUID

from django.core.cache import cache
from django.db import connection
from django.utils.module_loading import import_string

from apps.financial.models import (
    AccountPeriodBalance,
    GeneralLedger,
    ReportDefinition,
    ReportParameter,
)

logger = logging.getLogger(__name__)


def get_report_or_404(report_code: str, company_id: UUID) -> ReportDefinition:
    """Fetch a report definition by code. In production, verify company access."""
    try:
        return ReportDefinition.objects.get(code=report_code, is_active=True)
    except ReportDefinition.DoesNotExist:
        from ninja.errors import HttpError

        raise HttpError(404, f"Report '{report_code}' not found") from None


class ReportServiceError(ValueError):
    pass


class ReportService:
    """Generic report engine — supports SQL and Python compute types."""

    def run(self, report_code: str, params: dict, company_id: UUID) -> dict:
        """Full pipeline: validate params → check cache → compute → paginate → format."""
        report = get_report_or_404(report_code, company_id)
        self._validate_params(report, params)

        cache_key = self._cache_key(report_code, params, company_id)
        cached = cache.get(cache_key)
        if cached:
            return cached

        if report.compute_type == "sql":
            data = self._run_sql(report.sql_template, params, company_id)
        else:
            service_fn = import_string(report.service_method)
            data = service_fn(params, company_id)

        page = int(params.get("page", 1))
        page_size = int(params.get("page_size", report.page_size))
        paginated = self._paginate(data, page, page_size)
        formatted = self._format_columns(paginated, report)

        result = {
            "columns": self._get_columns(report),
            "rows": formatted,
            "total_rows": len(data),
            "page": page,
            "page_size": page_size,
            "generated_at": datetime.now(UTC).isoformat(),
            "summary": self._compute_summary(data, report),
            "group_totals": self._compute_group_totals(data, report),
        }

        cache.set(cache_key, result, report.cache_ttl_seconds)
        return result

    def _run_sql(self, sql_template: str, params: dict, company_id: UUID) -> list[dict]:
        """Execute parameterized SQL. Values injected via %(key)s binding."""
        sql_params = {"company_id": company_id}
        for key, value in params.items():
            if value is not None and value != "":
                sql_params[key] = value

        with connection.cursor() as cursor:
            cursor.execute(sql_template, sql_params)
            columns = [col[0] for col in cursor.description]
            return [dict(zip(columns, row, strict=False)) for row in cursor.fetchall()]

    def _cache_key(self, report_code: str, params: dict, company_id: UUID) -> str:
        raw = f"report:{report_code}:{company_id}:{json.dumps(params, sort_keys=True, default=str)}"
        return hashlib.md5(raw.encode()).hexdigest()

    def _validate_params(self, report: ReportDefinition, params: dict) -> None:
        """Check required parameters are present."""
        required_params = ReportParameter.objects.filter(
            report=report, required=True
        ).values_list("key", flat=True)
        for key in required_params:
            if key not in params or params[key] in (None, "", []):
                raise ReportServiceError(f"Required parameter '{key}' is missing")

    def _paginate(self, data: list[dict], page: int, page_size: int) -> list[dict]:
        """Slice data for the requested page."""
        start = (page - 1) * page_size
        end = start + page_size
        return data[start:end] if start < len(data) else []

    def _format_columns(self, rows: list[dict], report: ReportDefinition) -> list[dict]:
        """Apply formatting to row values based on column definitions."""
        columns = self._get_columns(report)
        formatted = []
        for row in rows:
            fmt_row = {}
            for col in columns:
                key = col["key"]
                val = row.get(key, 0)
                if col["type"] in ("decimal", "currency") and val is not None:
                    try:
                        val = round(float(val), 2)
                    except (TypeError, ValueError):
                        pass
                fmt_row[key] = val
            formatted.append(fmt_row)
        return formatted

    def _get_columns(self, report: ReportDefinition) -> list[dict]:
        """Return column definitions based on report type."""
        if report.code == "trial_balance":
            return [
                {
                    "key": "code",
                    "label": "Account Code",
                    "type": "string",
                    "align": "left",
                },
                {
                    "key": "name",
                    "label": "Account Name",
                    "type": "string",
                    "align": "left",
                },
                {
                    "key": "account_type",
                    "label": "Type",
                    "type": "string",
                    "align": "left",
                },
                {
                    "key": "opening_debit",
                    "label": "Opening DR",
                    "type": "currency",
                    "align": "right",
                },
                {
                    "key": "opening_credit",
                    "label": "Opening CR",
                    "type": "currency",
                    "align": "right",
                },
                {
                    "key": "period_debit",
                    "label": "Period DR",
                    "type": "currency",
                    "align": "right",
                },
                {
                    "key": "period_credit",
                    "label": "Period CR",
                    "type": "currency",
                    "align": "right",
                },
                {
                    "key": "closing_debit",
                    "label": "Closing DR",
                    "type": "currency",
                    "align": "right",
                },
                {
                    "key": "closing_credit",
                    "label": "Closing CR",
                    "type": "currency",
                    "align": "right",
                },
            ]
        return []

    def _compute_summary(
        self, data: list[dict], report: ReportDefinition
    ) -> dict | None:
        """Compute grand totals for currency columns."""
        if not report.show_grand_total or not data:
            return None

        columns = self._get_columns(report)
        currency_keys = [
            c["key"] for c in columns if c["type"] in ("decimal", "currency")
        ]
        summary = {}
        for key in currency_keys:
            total = sum(float(row.get(key, 0) or 0) for row in data)
            summary[key] = round(total, 2)
        return summary

    def _compute_group_totals(
        self, data: list[dict], report: ReportDefinition
    ) -> list[dict] | None:
        """Compute subtotals per group field."""
        if not report.show_subtotals or not report.group_field or not data:
            return None

        columns = self._get_columns(report)
        currency_keys = [
            c["key"] for c in columns if c["type"] in ("decimal", "currency")
        ]
        group_field = report.group_field
        groups = {}

        for row in data:
            gval = row.get(group_field, "")
            if gval not in groups:
                groups[gval] = {}
            for key in currency_keys:
                groups[gval][key] = groups[gval].get(key, 0) + float(
                    row.get(key, 0) or 0
                )

        result = []
        for gval, totals in groups.items():
            entry = {"group": gval}
            for key in currency_keys:
                entry[key] = round(totals[key], 2)
            result.append(entry)
        return result

    def drill_down(
        self, report_code: str, row_id: str, params: dict, company_id: UUID
    ) -> list[dict]:
        """Return detail transactions for a summary row."""
        report = get_report_or_404(report_code, company_id)
        if not report.supports_drill_down:
            raise ReportServiceError("This report does not support drill-down")

        account_id = params.get("account_id")
        period_id = params.get("period_id")
        if account_id and period_id:
            entries = (
                GeneralLedger.objects.filter(
                    account_id=account_id,
                    period_id=period_id,
                    company_id=company_id,
                )
                .select_related("journal_entry")
                .order_by("date", "created_at")
            )
            return [
                {
                    "date": e.date.isoformat(),
                    "entry_number": e.journal_entry.entry_number,
                    "description": e.journal_entry.description,
                    "debit": float(e.debit),
                    "credit": float(e.credit),
                    "balance": float(e.balance),
                }
                for e in entries
            ]

        raise ReportServiceError(
            "Missing drill-down parameters (account_id, period_id)"
        )


def backfill_account_period_balances(company_id: UUID | None = None):
    """Backfill AccountPeriodBalance from existing GeneralLedger entries.

    Used in data migration for historical data.
    """
    from django.db.models import Sum

    filters = {}
    if company_id:
        filters["company_id"] = company_id

    gl_entries = (
        GeneralLedger.objects.filter(**filters)
        .values("account_id", "company_id", "period_id")
        .annotate(
            total_debit=Sum("debit"),
            total_credit=Sum("credit"),
        )
    )

    for entry in gl_entries:
        AccountPeriodBalance.objects.update_or_create(
            account_id=entry["account_id"],
            company_id=entry["company_id"],
            period_id=entry["period_id"],
            defaults={
                "period_debit": entry["total_debit"],
                "period_credit": entry["total_credit"],
                "closing_debit": entry["total_debit"],
                "closing_credit": entry["total_credit"],
            },
        )
