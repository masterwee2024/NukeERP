"""Tests for Tax Codes & SST Engine (T029)."""

from datetime import date
from decimal import Decimal

import pytest
from rest_framework_simplejwt.tokens import AccessToken

from apps.core.models import Company, User
from apps.financial.models import TaxCode, TaxRate
from apps.financial.services.tax_service import (
    calculate_tax,
    get_effective_rate,
    get_sst_return,
)

# ── Fixtures ─────────────────────────────────────────────────────


@pytest.fixture
def admin_user(db):
    return User.objects.create_superuser(email="admin@test.com", password="admin123")


@pytest.fixture
def company(db):
    return Company.objects.create(name="Test Company", code="TC")


@pytest.fixture
def sr_code(db):
    tc = TaxCode.objects.create(
        code="SR", name="Standard Rate", rate_percent=8.00, tax_type="sales"
    )
    TaxRate.objects.create(
        tax_code=tc, rate_percent=8.00, effective_from=date(2024, 1, 1), is_current=True
    )
    return tc


@pytest.fixture
def zr_code(db):
    return TaxCode.objects.create(
        code="ZR", name="Zero-Rated", rate_percent=0, tax_type="zero_rated"
    )


@pytest.fixture
def es_code(db):
    return TaxCode.objects.create(
        code="ES", name="Exempt", rate_percent=0, tax_type="exempt"
    )


# ── Model Tests ──────────────────────────────────────────────────


@pytest.mark.django_db
class TestTaxModels:
    def test_create_tax_code(self, sr_code):
        assert "SR" in str(sr_code)
        assert "8.0" in str(sr_code)
        assert float(sr_code.rate_percent) == 8.0

    def test_create_tax_rate(self, sr_code):
        rate = TaxRate.objects.create(
            tax_code=sr_code, rate_percent=6.00, effective_from=date(2025, 3, 1)
        )
        assert str(rate) == "SR @ 6.0% from 2025-03-01"


# ── Service Tests ────────────────────────────────────────────────


@pytest.mark.django_db
class TestTaxService:
    def test_get_effective_rate(self, sr_code):
        rate = get_effective_rate(sr_code.id, date(2025, 1, 1))
        assert rate is not None
        assert float(rate.rate_percent) == 8.00

    def test_get_effective_rate_no_match(self):
        code = TaxCode.objects.create(
            code="NEW", name="New", rate_percent=0, tax_type="exempt"
        )
        rate = get_effective_rate(code.id, date(2025, 1, 1))
        assert rate is None

    def test_calculate_tax_sr(self, sr_code):
        result = calculate_tax(Decimal("1000"), sr_code.id, date(2025, 1, 1))
        assert result["tax_amount"] == 80.00
        assert result["rate_percent"] == 8.00

    def test_calculate_tax_zero_rated(self, zr_code):
        result = calculate_tax(Decimal("1000"), zr_code.id)
        assert result["tax_amount"] == 0
        assert result["tax_type"] == "zero_rated"

    def test_rate_change_effective_date(self, sr_code):
        TaxRate.objects.create(
            tax_code=sr_code,
            rate_percent=6.00,
            effective_from=date(2025, 3, 1),
            is_current=False,
        )

        result_old = calculate_tax(Decimal("1000"), sr_code.id, date(2025, 2, 1))
        assert result_old["rate_percent"] == 8.00

        result_new = calculate_tax(Decimal("1000"), sr_code.id, date(2025, 3, 15))
        assert result_new["rate_percent"] == 6.00

    def test_sst_return_empty(self, company):
        result = get_sst_return(company.id, 2026, 6)
        assert result["period"] == "2026-06"
        assert result["total_output_tax"] == 0


# ── API Tests ────────────────────────────────────────────────────


@pytest.mark.django_db
class TestTaxAPI:
    def _headers(self, user, company):
        token = AccessToken.for_user(user)
        return {
            "HTTP_AUTHORIZATION": f"Bearer {token}",
            "HTTP_X_COMPANY_ID": str(company.id),
        }

    def test_list_tax_codes(self, client, admin_user, company, sr_code, zr_code):
        response = client.get(
            "/api/v1/financial/tax-codes/", **self._headers(admin_user, company)
        )
        assert response.status_code == 200
        data = response.json()
        assert data["count"] >= 2

    def test_create_tax_code(self, client, admin_user, company):
        response = client.post(
            "/api/v1/financial/tax-codes/",
            {
                "code": "NEW",
                "name": "New Code",
                "rate_percent": 5.0,
                "tax_type": "sales",
            },
            content_type="application/json",
            **self._headers(admin_user, company),
        )
        assert response.status_code == 200
        assert response.json()["code"] == "NEW"

    def test_calculate_endpoint(self, client, admin_user, company, sr_code):
        response = client.post(
            "/api/v1/financial/tax-calculate/",
            {
                "amount": 1000,
                "tax_code_id": str(sr_code.id),
                "entry_date": "2025-01-01",
            },
            content_type="application/json",
            **self._headers(admin_user, company),
        )
        assert response.status_code == 200
        data = response.json()
        assert data["tax_amount"] == 80.0

    def test_sst_return_endpoint(self, client, admin_user, company):
        response = client.get(
            "/api/v1/financial/sst-return/2026/6/",
            **self._headers(admin_user, company),
        )
        assert response.status_code == 200
        data = response.json()
        assert data["period"] == "2026-06"

    def test_create_tax_rate(self, client, admin_user, company, sr_code):
        response = client.post(
            "/api/v1/financial/tax-rates/",
            {
                "tax_code_id": str(sr_code.id),
                "rate_percent": 6.0,
                "effective_from": "2025-03-01",
            },
            content_type="application/json",
            **self._headers(admin_user, company),
        )
        assert response.status_code == 200
        assert response.json()["rate_percent"] == 6.0
