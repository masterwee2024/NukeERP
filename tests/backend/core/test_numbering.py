"""Tests for Numbering Series — global policy + per-company assignment."""

import datetime

import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError

from apps.core.models import (
    Company,
    CompanyNumberingSeries,
    NumberingSeriesPolicy,
)

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
def company_b(db):
    return Company.objects.create(name="Company B", code="CB")


@pytest.fixture
def policy(db):
    return NumberingSeriesPolicy.objects.create(
        document_type="invoice",
        prefix="INV-",
        date_format="YYYYMM",
        padding=6,
        description="Test Invoice",
    )


@pytest.fixture
def assignment(db, policy, company):
    return CompanyNumberingSeries.objects.create(
        policy=policy,
        company=company,
        next_number=1,
        reset_period="yearly",
        last_reset_at=datetime.datetime.now(datetime.UTC),
    )


# --- Model Tests ---


@pytest.mark.django_db
class TestNumberingSeriesPolicyModel:
    def test_str(self, policy):
        assert str(policy) == "INV-invoice"

    def test_document_type_unique(self, policy):
        with pytest.raises(IntegrityError):
            NumberingSeriesPolicy.objects.create(document_type="invoice")

    def test_default_values(self):
        p = NumberingSeriesPolicy.objects.create(document_type="new_doc")
        assert p.padding == 6
        assert p.is_active is True


@pytest.mark.django_db
class TestCompanyNumberingSeriesModel:
    def test_str(self, assignment, company):
        assert str(assignment) == f"INV-invoice @ {company.name}"

    def test_unique_constraint(self, policy, company, assignment):
        with pytest.raises(IntegrityError):
            CompanyNumberingSeries.objects.create(
                policy=policy, company=company, next_number=1,
            )

    def test_default_values(self, policy, company):
        a = CompanyNumberingSeries.objects.create(policy=policy, company=company)
        assert a.next_number == 1
        assert a.reset_period == "yearly"
        assert a.is_active is True

    def test_same_policy_different_company(self, policy, company, company_b):
        a1 = CompanyNumberingSeries.objects.create(policy=policy, company=company)
        a2 = CompanyNumberingSeries.objects.create(policy=policy, company=company_b)
        assert a1.id != a2.id


# --- Service Tests ---


@pytest.mark.django_db
class TestNumberingService:
    def test_get_next_number_sequential(self, company, policy, assignment):
        from apps.core.services.numbering_service import get_next_number

        today = datetime.date.today()
        date_part = today.strftime("%Y%m")
        num1 = get_next_number("invoice", company.id)
        assert num1 == f"INV-{date_part}000001"
        num2 = get_next_number("invoice", company.id)
        assert num2 == f"INV-{date_part}000002"
        num3 = get_next_number("invoice", company.id)
        assert num3 == f"INV-{date_part}000003"

    def test_get_next_number_no_date_format(self, company, company_b):
        p = NumberingSeriesPolicy.objects.create(
            document_type="employee", prefix="EMP-", date_format="", padding=4,
        )
        CompanyNumberingSeries.objects.create(
            policy=p, company=company, next_number=1, reset_period="never",
        )
        from apps.core.services.numbering_service import get_next_number

        num = get_next_number("employee", company.id)
        assert num == "EMP-0001"

    def test_get_next_number_raises_on_missing_policy(self, company):
        from apps.core.services.numbering_service import get_next_number

        with pytest.raises(ValueError, match="No active numbering policy"):
            get_next_number("nonexistent", company.id)

    def test_get_next_number_raises_on_inactive_policy(self, company):
        p = NumberingSeriesPolicy.objects.create(
            document_type="inactive_doc", prefix="INA-", is_active=False,
        )
        CompanyNumberingSeries.objects.create(policy=p, company=company)
        from apps.core.services.numbering_service import get_next_number

        with pytest.raises(ValueError, match="No active numbering policy"):
            get_next_number("inactive_doc", company.id)

    def test_get_next_number_raises_on_missing_assignment(self, company, policy):
        from apps.core.services.numbering_service import get_next_number

        with pytest.raises(ValueError, match="no active numbering assignment"):
            get_next_number("invoice", company.id)

    def test_list_policies(self, policy):
        from apps.core.services.numbering_service import list_policies

        result = list_policies()
        assert len(result) == 1
        assert result[0].id == policy.id

    def test_create_policy(self):
        from apps.core.services.numbering_service import create_policy

        p = create_policy({"document_type": "po", "prefix": "PO-", "date_format": "YYYYMM"})
        assert p.document_type == "po"
        assert p.prefix == "PO-"

    def test_update_policy(self, policy):
        from apps.core.services.numbering_service import update_policy

        updated = update_policy(str(policy.id), {"prefix": "NEW-"})
        assert updated.prefix == "NEW-"

    def test_delete_policy(self, policy):
        from apps.core.services.numbering_service import delete_policy

        pid = str(policy.id)
        delete_policy(pid)
        assert NumberingSeriesPolicy.objects.filter(id=pid).count() == 0

    def test_assign_company(self, policy, company):
        from apps.core.services.numbering_service import assign_company

        a = assign_company(str(policy.id), str(company.id))
        assert a.company_id == company.id
        assert a.policy_id == policy.id

    def test_update_assignment(self, assignment):
        from apps.core.services.numbering_service import update_assignment

        updated = update_assignment(str(assignment.id), {"next_number": 99})
        assert updated.next_number == 99

    def test_unassign_company(self, assignment):
        from apps.core.services.numbering_service import unassign_company

        aid = str(assignment.id)
        unassign_company(aid)
        assert CompanyNumberingSeries.objects.filter(id=aid).count() == 0


# --- Year Reset Tests ---


@pytest.mark.django_db
class TestNumberingYearReset:
    def test_yearly_reset(self, company):
        from apps.core.services.numbering_service import get_next_number

        p = NumberingSeriesPolicy.objects.create(
            document_type="yearly_doc", prefix="YR-", date_format="YYYY",
        )
        a = CompanyNumberingSeries.objects.create(
            policy=p, company=company, next_number=100, reset_period="yearly",
        )
        # Simulate last reset was last year
        from django.db import connection

        with connection.cursor() as cursor:
            cursor.execute(
                "UPDATE core_company_numbering_series SET last_reset_at = %s WHERE id = %s",
                [datetime.datetime(datetime.date.today().year - 1, 12, 15), a.id],
            )
        a.refresh_from_db()

        num = get_next_number("yearly_doc", company.id)
        year_str = datetime.date.today().strftime("%Y")
        assert num == f"YR-{year_str}000001"

    def test_no_reset_same_year(self, company):
        from apps.core.services.numbering_service import get_next_number

        p = NumberingSeriesPolicy.objects.create(
            document_type="no_reset_doc", prefix="NR-", date_format="YYYY",
        )
        CompanyNumberingSeries.objects.create(
            policy=p, company=company, next_number=50, reset_period="yearly",
            last_reset_at=datetime.datetime.now(datetime.UTC),
        )
        num = get_next_number("no_reset_doc", company.id)
        year_str = datetime.date.today().strftime("%Y")
        assert num == f"NR-{year_str}000050"


# --- API Tests ---


@pytest.mark.django_db
class TestNumberingAPI:
    def test_list_unauthenticated(self, client):
        response = client.get("/api/v1/core/admin/numbering-policies/")
        assert response.status_code == 401

    def test_list_regular_user(self, client, regular_user, policy):
        from rest_framework_simplejwt.tokens import AccessToken

        token = AccessToken.for_user(regular_user)
        response = client.get(
            "/api/v1/core/admin/numbering-policies/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        assert response.status_code == 403

    def test_list_admin(self, client, admin_user, policy):
        from rest_framework_simplejwt.tokens import AccessToken

        token = AccessToken.for_user(admin_user)
        response = client.get(
            "/api/v1/core/admin/numbering-policies/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        assert response.status_code == 200
        assert len(response.json()) >= 1

    def test_create_admin(self, client, admin_user):
        from rest_framework_simplejwt.tokens import AccessToken

        token = AccessToken.for_user(admin_user)
        payload = {
            "document_type": "test_doc",
            "prefix": "TST-",
            "date_format": "YYMM",
        }
        response = client.post(
            "/api/v1/core/admin/numbering-policies/",
            data=payload,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        assert response.status_code == 200
        data = response.json()
        assert data["document_type"] == "test_doc"
        assert data["prefix"] == "TST-"

    def test_get_policy_detail(self, client, admin_user, policy, assignment):
        from rest_framework_simplejwt.tokens import AccessToken

        token = AccessToken.for_user(admin_user)
        response = client.get(
            f"/api/v1/core/admin/numbering-policies/{policy.id}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        assert response.status_code == 200
        data = response.json()
        assert data["document_type"] == "invoice"
        assert len(data["company_assignments"]) == 1

    def test_get_next_admin(self, client, admin_user, company, policy, assignment):
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

    def test_update_policy_admin(self, client, admin_user, policy):
        from rest_framework_simplejwt.tokens import AccessToken

        token = AccessToken.for_user(admin_user)
        payload = {
            "prefix": "INV2-",
            "description": "Updated policy",
            "updated_at": policy.updated_at.isoformat() if policy.updated_at else "",
        }
        response = client.put(
            f"/api/v1/core/admin/numbering-policies/{policy.id}/",
            data=payload,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        assert response.status_code == 200
        data = response.json()
        assert data["prefix"] == "INV2-"
        assert data["description"] == "Updated policy"

    def test_update_409_conflict(self, client, admin_user, policy):
        from rest_framework_simplejwt.tokens import AccessToken

        token = AccessToken.for_user(admin_user)
        payload = {"prefix": "STALE-", "updated_at": "2020-01-01T00:00:00"}
        response = client.put(
            f"/api/v1/core/admin/numbering-policies/{policy.id}/",
            data=payload,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        assert response.status_code == 409

    def test_update_policy_404(self, client, admin_user):
        import uuid
        from rest_framework_simplejwt.tokens import AccessToken

        token = AccessToken.for_user(admin_user)
        response = client.put(
            f"/api/v1/core/admin/numbering-policies/{uuid.uuid4()}/",
            data={"prefix": "FAKE-"},
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        assert response.status_code == 404

    def test_delete_policy_admin(self, client, admin_user, policy):
        from rest_framework_simplejwt.tokens import AccessToken

        token = AccessToken.for_user(admin_user)
        response = client.delete(
            f"/api/v1/core/admin/numbering-policies/{policy.id}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        assert response.status_code == 200
        assert response.json()["detail"] == "Numbering policy deleted"

    def test_assign_company_admin(self, client, admin_user, policy, company):
        from rest_framework_simplejwt.tokens import AccessToken

        token = AccessToken.for_user(admin_user)
        response = client.post(
            f"/api/v1/core/admin/numbering-policies/{policy.id}/assign/",
            data={"company_id": str(company.id)},
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        assert response.status_code == 200
        data = response.json()
        assert data["company_name"] == "Test Company"

    def test_update_assignment_admin(self, client, admin_user, policy, assignment):
        from rest_framework_simplejwt.tokens import AccessToken

        token = AccessToken.for_user(admin_user)
        payload = {"next_number": 999, "updated_at": assignment.updated_at.isoformat() if assignment.updated_at else ""}
        response = client.put(
            f"/api/v1/core/admin/numbering-policies/{policy.id}/assign/{assignment.id}/",
            data=payload,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        assert response.status_code == 200
        assert response.json()["next_number"] == 999

    def test_unassign_company_admin(self, client, admin_user, policy, assignment):
        from rest_framework_simplejwt.tokens import AccessToken

        token = AccessToken.for_user(admin_user)
        response = client.delete(
            f"/api/v1/core/admin/numbering-policies/{policy.id}/assign/{assignment.id}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        assert response.status_code == 200
