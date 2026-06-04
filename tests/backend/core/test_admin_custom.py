"""Tests for Django Admin Customization (T020)."""

import pytest
from django.test import Client

from apps.core.models import Company, Permission, Role, User, UserCompany

# ── Fixtures ─────────────────────────────────────────────────────


@pytest.fixture
def admin_user(db):
    user = User.objects.create_superuser(
        email="admin@test.com",
        password="admin123",
        first_name="Admin",
        last_name="User",
    )
    return user


@pytest.fixture
def regular_user(db):
    return User.objects.create_user(
        email="user@test.com",
        password="user123",
        first_name="Regular",
        last_name="User",
        is_staff=True,
    )


@pytest.fixture
def company(db):
    return Company.objects.create(name="Test Company", code="TC", is_active=True)


@pytest.fixture
def other_company(db):
    return Company.objects.create(name="Other Company", code="OC", is_active=True)


@pytest.fixture
def admin_client(admin_user):
    client = Client()
    client.force_login(admin_user)
    return client


@pytest.fixture
def regular_client(regular_user, company):
    client = Client()
    UserCompany.objects.create(user=regular_user, company=company, is_default=True)
    client.force_login(regular_user)
    return client


# ── Admin Site Tests ─────────────────────────────────────────────


@pytest.mark.django_db
class TestAdminSite:
    def test_admin_login_page(self, client):
        response = client.get("/admin/login/")
        assert response.status_code == 200
        assert "pyERP" in response.content.decode()

    def test_admin_index_superuser(self, admin_client):
        response = admin_client.get("/admin/")
        assert response.status_code == 200
        content = response.content.decode()
        assert "pyERP" in content or "Administration" in content

    def test_dashboard_superuser(self, admin_client):
        response = admin_client.get("/admin/dashboard/")
        assert response.status_code == 200


# ── Company Filter Tests ─────────────────────────────────────────


@pytest.mark.django_db
class TestCompanyFilter:
    def test_superuser_sees_all_companies(self, admin_client, company, other_company):
        response = admin_client.get("/admin/core/company/")
        assert response.status_code == 200
        content = response.content.decode()
        assert "Test Company" in content
        assert "Other Company" in content

    def test_regular_user_sees_only_assigned_companies(
        self, regular_client, company, other_company
    ):
        response = regular_client.get("/admin/core/company/")
        assert response.status_code == 200
        content = response.content.decode()
        assert "Test Company" in content
        assert "Other Company" not in content

    def test_superuser_access_to_all_models(self, admin_client):
        response = admin_client.get("/admin/core/user/")
        assert response.status_code == 200


# ── Custom Actions Tests ─────────────────────────────────────────


@pytest.mark.django_db
class TestCustomActions:
    def test_export_csv_action(self, admin_client, company):
        response = admin_client.post(
            "/admin/core/company/",
            {
                "action": "export_as_csv",
                "_selected_action": [company.pk],
            },
        )
        assert response.status_code == 200
        assert response["Content-Type"] == "text/csv"
        content = response.content.decode()
        assert "Test Company" in content
        assert "TC" in content

    def test_bulk_activate_action(self, admin_client):
        inactive = User.objects.create_user(
            email="inactive@test.com", password="pwd", is_active=False
        )
        response = admin_client.post(
            "/admin/core/user/",
            {
                "action": "bulk_activate",
                "_selected_action": [inactive.pk],
            },
            follow=True,
        )
        assert response.status_code == 200
        inactive.refresh_from_db()
        assert inactive.is_active is True

    def test_bulk_deactivate_action(self, admin_client):
        active = User.objects.create_user(
            email="active@test.com", password="pwd", is_active=True
        )
        response = admin_client.post(
            "/admin/core/user/",
            {
                "action": "bulk_deactivate",
                "_selected_action": [active.pk],
            },
            follow=True,
        )
        assert response.status_code == 200
        active.refresh_from_db()
        assert active.is_active is False


# ── Model Admin Tests ────────────────────────────────────────────


@pytest.mark.django_db
class TestModelAdmins:
    def test_company_admin_list(self, admin_client, company):
        response = admin_client.get("/admin/core/company/")
        assert response.status_code == 200

    def test_user_admin_list(self, admin_client, admin_user):
        response = admin_client.get("/admin/core/user/")
        assert response.status_code == 200

    def test_role_admin_list(self, admin_client):
        Role.objects.create(name="Test Role", is_active=True)
        response = admin_client.get("/admin/core/role/")
        assert response.status_code == 200

    def test_permission_admin_list(self, admin_client):
        Permission.objects.create(
            module="core", action="create", codename="core_create"
        )
        response = admin_client.get("/admin/core/permission/")
        assert response.status_code == 200

    def test_menu_admin_list(self, admin_client):
        response = admin_client.get("/admin/core/menu/")
        assert response.status_code == 200

    def test_audit_log_admin_readonly(self, admin_client):
        response = admin_client.get("/admin/core/auditlog/")
        assert response.status_code == 200

    def test_audit_log_no_add_permission(self, admin_client):
        response = admin_client.get("/admin/core/auditlog/add/")
        assert response.status_code == 403

    def test_user_company_admin_list(self, admin_client):
        response = admin_client.get("/admin/core/usercompany/")
        assert response.status_code == 200
