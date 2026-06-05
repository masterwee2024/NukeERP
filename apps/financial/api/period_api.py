"""Period Management API — list, close, reopen, year-end close."""

import logging
from uuid import UUID

from ninja import Router, Schema
from ninja.errors import HttpError

from apps.core.api.auth import JWTAuth
from apps.financial.models import FinancialPeriod, FinancialYear
from apps.financial.services.period_service import (
    PeriodError,
    close_period,
    create_initial_periods,
    reopen_period,
    year_end_close,
)

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


class FinancialPeriodOut(Schema):
    id: str
    financial_year_id: str | None = None
    name: str
    start_date: str
    end_date: str
    is_open: bool
    is_closed: bool

    @staticmethod
    def resolve_id(obj):
        return str(obj.id)

    @staticmethod
    def resolve_financial_year_id(obj):
        return str(obj.financial_year_id) if obj.financial_year_id else None

    @staticmethod
    def resolve_start_date(obj):
        return obj.start_date.isoformat() if obj.start_date else ""

    @staticmethod
    def resolve_end_date(obj):
        return obj.end_date.isoformat() if obj.end_date else ""


class FinancialYearOut(Schema):
    id: str
    name: str
    start_date: str
    end_date: str
    is_closed: bool
    periods: list[FinancialPeriodOut] = []

    @staticmethod
    def resolve_id(obj):
        return str(obj.id)

    @staticmethod
    def resolve_start_date(obj):
        return obj.start_date.isoformat() if obj.start_date else ""

    @staticmethod
    def resolve_end_date(obj):
        return obj.end_date.isoformat() if obj.end_date else ""


class PeriodActionOut(Schema):
    id: str
    name: str
    is_open: bool

    @staticmethod
    def resolve_id(obj):
        return str(obj.id)


class YearEndCloseIn(Schema):
    retained_earnings_account_id: str | None = None


class YearEndCloseOut(Schema):
    closed_year: str
    new_year: str
    new_year_name: str
    net_income_transferred: float
    total_lines_created: int


class ErrorOut(Schema):
    detail: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("/periods/", response={200: list[FinancialPeriodOut]})
def list_periods(request):
    """List all financial periods for the current company."""
    company_id = _require_company_id(request)
    periods = (
        FinancialPeriod.objects.filter(company_id=company_id)
        .select_related("financial_year")
        .order_by("start_date")
    )
    return list(periods)


@router.get(
    "/periods/{id}/",
    response={200: FinancialPeriodOut, 404: ErrorOut},
)
def get_period(request, id: UUID):
    """Get a single financial period."""
    company_id = _require_company_id(request)
    try:
        return FinancialPeriod.objects.get(id=id, company_id=company_id)
    except FinancialPeriod.DoesNotExist:
        raise HttpError(404, "Period not found") from None


@router.post(
    "/periods/{id}/close/",
    response={200: PeriodActionOut, 400: ErrorOut, 404: ErrorOut},
)
def close(request, id: UUID):
    """Close a financial period."""
    try:
        period = close_period(id)
        return period
    except PeriodError as e:
        raise HttpError(400, str(e)) from e
    except FinancialPeriod.DoesNotExist:
        raise HttpError(404, "Period not found") from None


@router.post(
    "/periods/{id}/reopen/",
    response={200: PeriodActionOut, 400: ErrorOut, 404: ErrorOut},
)
def reopen(request, id: UUID):
    """Reopen a closed financial period."""
    try:
        period = reopen_period(id)
        return period
    except PeriodError as e:
        raise HttpError(400, str(e)) from e
    except FinancialPeriod.DoesNotExist:
        raise HttpError(404, "Period not found") from None


@router.get("/financial-years/")
def list_years(request):
    """List all financial years with periods."""
    company_id = _require_company_id(request)
    years = FinancialYear.objects.filter(company_id=company_id).order_by("-start_date")
    result = []
    for year in years:
        periods = list(
            FinancialPeriod.objects.filter(financial_year=year).order_by("start_date")
        )
        result.append(
            {
                "id": str(year.id),
                "name": year.name,
                "start_date": year.start_date.isoformat(),
                "end_date": year.end_date.isoformat(),
                "is_closed": year.is_closed,
                "periods": [
                    {
                        "id": str(p.id),
                        "financial_year_id": str(p.financial_year_id),
                        "name": p.name,
                        "start_date": p.start_date.isoformat(),
                        "end_date": p.end_date.isoformat(),
                        "is_open": p.is_open,
                        "is_closed": p.is_closed,
                    }
                    for p in periods
                ],
            }
        )
    return result


@router.post(
    "/financial-years/{id}/year-end-close/",
    response={200: YearEndCloseOut, 400: ErrorOut, 404: ErrorOut},
)
def year_end(request, id: UUID, payload: YearEndCloseIn = None):
    """Perform year-end close: transfer P&L, create new year, lock old year."""
    try:
        re_account_id = None
        if payload and payload.retained_earnings_account_id:
            re_account_id = UUID(payload.retained_earnings_account_id)
        result = year_end_close(id, retained_earnings_account_id=re_account_id)
        return result
    except PeriodError as e:
        raise HttpError(400, str(e)) from e
    except FinancialYear.DoesNotExist:
        raise HttpError(404, "Financial year not found") from None


@router.post("/init-periods/")
def init_periods(request):
    """Create initial financial year and 12 monthly periods for a company."""
    company_id = _require_company_id(request)

    if FinancialPeriod.objects.filter(company_id=company_id).exists():
        raise HttpError(400, "Periods already exist for this company")

    from datetime import date

    year = date.today().year if date.today().month < 10 else date.today().year
    fin_year = create_initial_periods(company_id, year=year)

    periods = list(
        FinancialPeriod.objects.filter(financial_year=fin_year).order_by("start_date")
    )
    return {
        "id": str(fin_year.id),
        "name": fin_year.name,
        "start_date": fin_year.start_date.isoformat(),
        "end_date": fin_year.end_date.isoformat(),
        "is_closed": fin_year.is_closed,
        "periods": [
            {
                "id": str(p.id),
                "financial_year_id": str(p.financial_year_id),
                "name": p.name,
                "start_date": p.start_date.isoformat(),
                "end_date": p.end_date.isoformat(),
                "is_open": p.is_open,
                "is_closed": p.is_closed,
            }
            for p in periods
        ],
    }
