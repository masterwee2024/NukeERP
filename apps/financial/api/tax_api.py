"""Tax Code API — CRUD, rate lookup, SST-02 return."""

from datetime import date
from uuid import UUID

from ninja import Router, Schema
from ninja.errors import HttpError

from apps.core.api.auth import JWTAuth
from apps.financial.models import TaxCode, TaxRate
from apps.financial.services.tax_service import (
    calculate_tax,
    get_sst_return,
)

router = Router(auth=JWTAuth())


def _require_company_id(request) -> UUID:
    company_id = request.headers.get("x-company-id")
    if not company_id:
        raise HttpError(400, "X-Company-Id header is required")
    try:
        return UUID(company_id)
    except ValueError:
        raise HttpError(400, "Invalid X-Company-Id header") from None


class TaxCodeOut(Schema):
    id: str
    code: str
    name: str
    rate_percent: float = 0
    tax_type: str
    is_active: bool = True
    description: str = ""

    @staticmethod
    def resolve_id(obj):
        return str(obj.id)


class TaxCodeCreateIn(Schema):
    code: str
    name: str
    rate_percent: float = 0
    tax_type: str
    is_active: bool = True
    description: str = ""


class TaxCodeUpdateIn(Schema):
    name: str | None = None
    rate_percent: float | None = None
    tax_type: str | None = None
    is_active: bool | None = None
    description: str | None = None


class TaxRateOut(Schema):
    id: str
    tax_code_id: str
    rate_percent: float
    effective_from: str
    effective_to: str | None = None
    is_current: bool = True

    @staticmethod
    def resolve_id(obj):
        return str(obj.id)

    @staticmethod
    def resolve_tax_code_id(obj):
        return str(obj.tax_code_id)

    @staticmethod
    def resolve_effective_from(obj):
        return obj.effective_from.isoformat() if obj.effective_from else ""

    @staticmethod
    def resolve_effective_to(obj):
        return obj.effective_to.isoformat() if obj.effective_to else None


class TaxRateCreateIn(Schema):
    tax_code_id: str
    rate_percent: float
    effective_from: str
    effective_to: str | None = None


class TaxCalcIn(Schema):
    amount: float
    tax_code_id: str
    entry_date: str | None = None


class TaxCalcOut(Schema):
    tax_amount: float
    rate_percent: float
    tax_code_code: str
    tax_code_name: str
    tax_type: str


class SstReturnOut(Schema):
    period: str
    total_output_tax: float
    total_input_tax: float
    net_tax_payable: float
    taxable_sales: float
    taxable_purchases: float


# ── Tax Code CRUD ────────────────────────────────────────────────


@router.get("/tax-codes/")
def list_tax_codes(request):
    codes = TaxCode.objects.all().order_by("code")
    return {"count": codes.count(), "results": [TaxCodeOut.from_orm(c) for c in codes]}


@router.post("/tax-codes/", response=TaxCodeOut)
def create_tax_code(request, payload: TaxCodeCreateIn):
    code = TaxCode.objects.create(
        code=payload.code,
        name=payload.name,
        rate_percent=payload.rate_percent,
        tax_type=payload.tax_type,
        is_active=payload.is_active,
        description=payload.description,
    )
    return code


@router.put("/tax-codes/{id}/", response=TaxCodeOut)
def update_tax_code(request, id: UUID, payload: TaxCodeUpdateIn):
    try:
        code = TaxCode.objects.get(id=id)
    except TaxCode.DoesNotExist:
        raise HttpError(404, "Tax code not found") from None

    if payload.name is not None:
        code.name = payload.name
    if payload.rate_percent is not None:
        code.rate_percent = payload.rate_percent
    if payload.tax_type is not None:
        code.tax_type = payload.tax_type
    if payload.is_active is not None:
        code.is_active = payload.is_active
    if payload.description is not None:
        code.description = payload.description
    code.save()
    return code


# ── Tax Rate ─────────────────────────────────────────────────────


@router.get("/tax-rates/")
def list_tax_rates(request, tax_code_id: str = ""):
    qs = TaxRate.objects.select_related("tax_code").all()
    if tax_code_id:
        qs = qs.filter(tax_code_id=tax_code_id)
    return {"count": qs.count(), "results": [TaxRateOut.from_orm(r) for r in qs]}


@router.post("/tax-rates/", response=TaxRateOut)
def create_tax_rate(request, payload: TaxRateCreateIn):
    try:
        effective_from = date.fromisoformat(payload.effective_from)
    except ValueError:
        raise HttpError(400, "Invalid effective_from date") from None

    effective_to = None
    if payload.effective_to:
        try:
            effective_to = date.fromisoformat(payload.effective_to)
        except ValueError:
            raise HttpError(400, "Invalid effective_to date") from None

    rate = TaxRate.objects.create(
        tax_code_id=payload.tax_code_id,
        rate_percent=payload.rate_percent,
        effective_from=effective_from,
        effective_to=effective_to,
    )
    return rate


# ── Tax Calculation ──────────────────────────────────────────────


@router.post("/tax-calculate/", response=TaxCalcOut)
def calculate(request, payload: TaxCalcIn):
    entry_date = None
    if payload.entry_date:
        try:
            entry_date = date.fromisoformat(payload.entry_date)
        except ValueError:
            raise HttpError(400, "Invalid entry_date") from None

    try:
        result = calculate_tax(
            amount=payload.amount,
            tax_code_id=UUID(payload.tax_code_id),
            entry_date=entry_date,
        )
        return {"tax_amount": float(result["tax_amount"]), **result}
    except TaxCode.DoesNotExist:
        raise HttpError(404, "Tax code not found") from None


# ── SST-02 Return ────────────────────────────────────────────────


@router.get("/sst-return/{year}/{month}/", response=SstReturnOut)
def sst_return(request, year: int, month: int):
    company_id = _require_company_id(request)
    return get_sst_return(company_id, year, month)
