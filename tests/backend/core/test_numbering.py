"""Tests for Numbering Series — model, service, API."""

import datetime

import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError

from apps.core.models import Company, NumberingSeries

User = get_user_model()


# --- Fixtures ---


@pytest.fixture
def admin_user(db):
    return User.objects.create_superuser(email="admin@test.com", password="admin123")


@pytest.fixture
def regular_user(db):
    return User.objects.create_user(email="user@test.com", password="user123")


@pytest.fixture
def company(db):
    return Company.objects.create(name="Test Company", code="TC")


@pytest.fixture
def series(db, company):
    return NumberingSeries.objects.create(
        document_type="invoice",
        prefix="INV-",
        date_format="YYYYMM",
        next_number=1,
        reset_period="yearly",
        padding=6,
        company=company,
        description="Test Invoice",
        last_reset_at=datetime.datetime.now(datetime.UTC),
    )


# --- Model Tests ---


@pytest.mark.django_db
class TestNumberingSeriesModel:
    def test_str(self, series):
        assert str(series) == "INV-invoice"

    def test_unique_constraint(self, company, series):
        with pytest.raises(IntegrityError):
            NumberingSeries.objects.create(
                document_type="invoice",
                prefix="INV-",
                company=company,
            )

    def test_default_values(self, company):
        s = NumberingSeries.objects.create(document_type="new_doc", company=company)
        assert s.next_number == 1
        assert s.reset_period == "yearly"
        assert s.padding == 6
        assert s.is_active is True

    def test_same_doc_type_different_company(self, db):
        c1 = Company.objects.create(name="Company A", code="CA")
        c2 = Company.objects.create(name="Company B", code="CB")
        s1 = NumberingSeries.objects.create(document_type="invoice", company=c1)
        s2 = NumberingSeries.objects.create(document_type="invoice", company=c2)
        assert s1.id != s2.id
        assert str(s1.id) != str(s2.id)


# --- Service Tests ---


@pytest.mark.django_db
class TestNumberingService:
    def test_get_next_number_sequential(self, company, series):
        from apps.core.services.numbering_service import get_next_number

        today = datetime.date.today()
        date_part = today.strftime("%Y%m")
        num1 = get_next_number("invoice", company.id)
        assert num1 == f"INV-{date_part}000001"
        num2 = get_next_number("invoice", company.id)
        assert num2 == f"INV-{date_part}000002"
        num3 = get_next_number("invoice", company.id)
        assert num3 == f"INV-{date_part}000003"

    def test_get_next_number_no_date_format(self, company):
        NumberingSeries.objects.create(
            document_type="employee",
            prefix="EMP-",
            date_format="",
            next_number=1,
            reset_period="never",
            padding=4,
            company=company,
            last_reset_at=datetime.datetime.now(datetime.UTC),
        )
        from apps.core.services.numbering_service import get_next_number

        num = get_next_number("employee", company.id)
        assert num == "EMP-0001"

    def test_get_next_number_raises_on_missing(self, company):
        from apps.core.services.numbering_service import get_next_number

        with pytest.raises(ValueError, match="No active numbering series"):
            get_next_number("nonexistent", company.id)

    def test_get_next_number_raises_on_inactive(self, company):
        NumberingSeries.objects.create(
            document_type="inactive_doc",
            prefix="INA-",
            company=company,
            is_active=False,
        )
        from apps.core.services.numbering_service import get_next_number

        with pytest.raises(ValueError, match="No active numbering series"):
            get_next_number("inactive_doc", company.id)

    def test_list_series(self, company, series):
        from apps.core.services.numbering_service import list_series

        result = list_series(company.id)
        assert len(result) == 1
        assert result[0].id == series.id

    def test_list_series_all(self, db):
        c1 = Company.objects.create(name="C1", code="C1")
        c2 = Company.objects.create(name="C2", code="C2")
        NumberingSeries.objects.create(document_type="doc1", company=c1)
        NumberingSeries.objects.create(document_type="doc2", company=c2)
        from apps.core.services.numbering_service import list_series

        result = list_series()
        assert len(result) == 2

    def test_create_series(self, company):
        from apps.core.services.numbering_service import create_series

        s = create_series(
            {
                "document_type": "po",
                "prefix": "PO-",
                "date_format": "YYYYMM",
                "company_id": company.id,
            }
        )
        assert s.document_type == "po"
        assert s.prefix == "PO-"

    def test_update_series(self, series):
        from apps.core.services.numbering_service import update_series

        updated = update_series(str(series.id), {"prefix": "NEW-"})
        assert updated.prefix == "NEW-"

    def test_delete_series(self, series):
        from apps.core.services.numbering_service import delete_series

        sid = str(series.id)
        delete_series(sid)
        assert NumberingSeries.objects.filter(id=sid).count() == 0


@pytest.mark.django_db
class TestNumberingServiceYearReset:
    """Test yearly and monthly reset logic."""

    def test_yearly_reset(self, company):
        from apps.core.services.numbering_service import get_next_number

        s = NumberingSeries.objects.create(
            document_type="yearly_doc",
            prefix="YR-",
            date_format="YYYY",
            next_number=100,
            reset_period="yearly",
            company=company,
        )
        # Simulate last reset was last year by directly updating the field
        from django.db import connection

        with connection.cursor() as cursor:
            cursor.execute(
                "UPDATE core_numbering_series SET last_reset_at = %s WHERE id = %s",
                [datetime.datetime(datetime.date.today().year - 1, 12, 15), s.id],
            )
        s.refresh_from_db()

        num = get_next_number("yearly_doc", company.id)
        year_str = datetime.date.today().strftime("%Y")
        assert num == f"YR-{year_str}000001"

    def test_no_reset_same_year(self, company):
        import datetime

        from apps.core.services.numbering_service import get_next_number

        NumberingSeries.objects.create(
            document_type="no_reset_doc",
            prefix="NR-",
            date_format="YYYY",
            next_number=50,
            reset_period="yearly",
            company=company,
            last_reset_at=datetime.datetime.now(datetime.UTC),
        )

        num = get_next_number("no_reset_doc", company.id)
        year_str = datetime.date.today().strftime("%Y")
        assert num == f"NR-{year_str}000050"


# --- API Tests ---


@pytest.mark.django_db
class TestNumberingAPI:
    def test_list_unauthenticated(self, client):
        response = client.get("/api/v1/core/admin/numbering-series/")
        assert response.status_code == 401

    def test_list_regular_user(self, client, regular_user, series):
        from rest_framework_simplejwt.tokens import AccessToken

        token = AccessToken.for_user(regular_user)
        response = client.get(
            "/api/v1/core/admin/numbering-series/", HTTP_AUTHORIZATION=f"Bearer {token}"
        )
        assert response.status_code == 403

    def test_list_admin(self, client, admin_user, series):
        from rest_framework_simplejwt.tokens import AccessToken

        token = AccessToken.for_user(admin_user)
        response = client.get(
            "/api/v1/core/admin/numbering-series/", HTTP_AUTHORIZATION=f"Bearer {token}"
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert data[0]["document_type"] == "invoice"

    def test_create_admin(self, client, admin_user, company):
        from rest_framework_simplejwt.tokens import AccessToken

        token = AccessToken.for_user(admin_user)
        payload = {
            "document_type": "test_doc",
            "prefix": "TST-",
            "date_format": "YYMM",
            "company_id": company.id,
        }
        response = client.post(
            "/api/v1/core/admin/numbering-series/",
            data=payload,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        assert response.status_code == 200
        data = response.json()
        assert data["document_type"] == "test_doc"
        assert data["prefix"] == "TST-"

    def test_get_next_admin(self, client, admin_user, company, series):
        from rest_framework_simplejwt.tokens import AccessToken

        token = AccessToken.for_user(admin_user)
        response = client.get(
            f"/api/v1/core/admin/numbering-series/next/?document_type=invoice&company_id={company.id}",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        assert response.status_code == 200
        data = response.json()
        assert data["document_type"] == "invoice"
        assert data["number"].startswith("INV-")

    def test_update_admin(self, client, admin_user, series):
        from rest_framework_simplejwt.tokens import AccessToken

        token = AccessToken.for_user(admin_user)
        payload = {
            "prefix": "INV2-",
            "description": "Updated invoice series",
            "updated_at": series.updated_at.isoformat() if series.updated_at else "",
        }
        response = client.put(
            f"/api/v1/core/admin/numbering-series/{series.id}/",
            data=payload,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        assert response.status_code == 200
        data = response.json()
        assert data["prefix"] == "INV2-"
        assert data["description"] == "Updated invoice series"

    def test_update_409_conflict(self, client, admin_user, series):
        from rest_framework_simplejwt.tokens import AccessToken

        token = AccessToken.for_user(admin_user)
        # Send a stale updated_at
        payload = {
            "prefix": "STALE-",
            "updated_at": "2020-01-01T00:00:00",
        }
        response = client.put(
            f"/api/v1/core/admin/numbering-series/{series.id}/",
            data=payload,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        assert response.status_code == 409

    def test_update_404(self, client, admin_user):
        import uuid

        from rest_framework_simplejwt.tokens import AccessToken

        token = AccessToken.for_user(admin_user)
        response = client.put(
            f"/api/v1/core/admin/numbering-series/{uuid.uuid4()}/",
            data={"prefix": "FAKE-"},
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        assert response.status_code == 404

    def test_delete_admin(self, client, admin_user, series):
        from rest_framework_simplejwt.tokens import AccessToken

        token = AccessToken.for_user(admin_user)
        response = client.delete(
            f"/api/v1/core/admin/numbering-series/{series.id}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        assert response.status_code == 200
        assert response.json()["detail"] == "Numbering series deleted"
