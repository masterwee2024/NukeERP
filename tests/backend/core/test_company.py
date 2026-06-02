"""Tests for the multi-company architecture (T013)."""

import pytest
from django.test import Client

from apps.core.models import Company, User, UserCompany
from apps.core.services import company_service

# --- Fixtures ---


@pytest.fixture
def db():
    """Ensure database is available."""
    pass


@pytest.fixture
def admin_user(db):
    return User.objects.create_superuser(
        email="admin@example.com",
        password="adminpass123",
        first_name="Admin",
        last_name="User",
    )


@pytest.fixture
def regular_user(db):
    return User.objects.create_user(
        email="user@example.com",
        password="userpass123",
        first_name="Regular",
        last_name="User",
    )


@pytest.fixture
def parent_company(db):
    return Company.objects.create(
        name="Parent Corp",
        code="PARENT",
        registration_number="111111-A",
        is_group=True,
        base_currency="MYR",
    )


@pytest.fixture
def child_company(db, parent_company):
    return Company.objects.create(
        name="Child Sdn Bhd",
        code="CHILD",
        registration_number="222222-A",
        parent=parent_company,
        base_currency="MYR",
    )


@pytest.fixture
def another_company(db):
    return Company.objects.create(
        name="Another Sdn Bhd",
        code="ANOTHER",
        registration_number="333333-A",
        base_currency="MYR",
    )


@pytest.fixture
def auth_client(admin_user):
    client = Client()
    client.force_login(admin_user)
    return client


@pytest.fixture
def user_client(regular_user):
    client = Client()
    client.force_login(regular_user)
    return client


# --- Model Tests ---


@pytest.mark.django_db
class TestCompanyModel:
    def test_create_company(self):
        company = Company.objects.create(name="Test Co", code="TEST")
        assert company.name == "Test Co"
        assert company.code == "TEST"
        assert company.is_active is True
        assert company.is_group is False
        assert company.base_currency == "MYR"
        assert company.date_format == "Y-m-d"
        assert company.timezone == "Asia/Kuala_Lumpur"
        assert company.country == "MY"

    def test_str(self, parent_company):
        assert str(parent_company) == "Parent Corp"

    def test_group_hierarchy(self, child_company, parent_company):
        assert child_company.parent == parent_company
        assert child_company in parent_company.children.all()

    def test_company_fields_defaults(self):
        company = Company.objects.create(name="Default Test", code="DFT1")
        assert company.address == ""
        assert company.city == ""
        assert company.state == ""
        assert company.postcode == ""
        assert company.country == "MY"
        assert company.phone == ""
        assert company.email == ""
        assert company.base_currency == "MYR"
        assert company.date_format == "Y-m-d"
        assert company.timezone == "Asia/Kuala_Lumpur"
        assert company.is_group is False
        assert company.parent is None


@pytest.mark.django_db
class TestUserCompanyModel:
    def test_user_company_creation(self, regular_user, parent_company):
        uc = UserCompany.objects.create(
            user=regular_user,
            company=parent_company,
            is_default=True,
        )
        assert uc.user == regular_user
        assert uc.company == parent_company
        assert uc.is_default is True

    def test_unique_constraint(self, regular_user, parent_company):
        UserCompany.objects.create(user=regular_user, company=parent_company)
        with pytest.raises(Exception, match="unique|duplicate|already exists"):
            UserCompany.objects.create(user=regular_user, company=parent_company)

    def test_str(self, regular_user, parent_company):
        uc = UserCompany.objects.create(user=regular_user, company=parent_company)
        assert str(uc) == f"{regular_user.email} → {parent_company.name}"


# --- Service Tests ---


@pytest.mark.django_db
class TestCompanyService:
    def test_get_user_companies(self, regular_user, parent_company, child_company):
        UserCompany.objects.create(user=regular_user, company=parent_company)
        companies = company_service.get_user_companies(regular_user)
        assert parent_company in companies
        assert child_company not in companies

    def test_get_user_default_company_from_usercompany(
        self, regular_user, parent_company, another_company
    ):
        UserCompany.objects.create(user=regular_user, company=another_company)
        UserCompany.objects.create(
            user=regular_user, company=parent_company, is_default=True
        )
        default = company_service.get_user_default_company(regular_user)
        assert default == parent_company

    def test_get_user_default_company_from_user_field(
        self, regular_user, parent_company
    ):
        regular_user.current_company = parent_company
        regular_user.save()
        default = company_service.get_user_default_company(regular_user)
        assert default == parent_company

    def test_set_user_default_company(
        self, regular_user, parent_company, child_company
    ):
        UserCompany.objects.create(user=regular_user, company=parent_company)
        UserCompany.objects.create(user=regular_user, company=child_company)
        company_service.set_user_default_company(regular_user, child_company)
        assert regular_user.current_company == child_company

    def test_get_company_children(self, parent_company, child_company):
        children = company_service.get_company_children(parent_company)
        assert child_company in children

    def test_get_company_descendants(self, parent_company, child_company):
        grandchild = Company.objects.create(
            name="Grandchild", code="GRND", parent=child_company
        )
        descendants = company_service.get_company_descendants(parent_company)
        assert child_company in descendants
        assert grandchild in descendants

    def test_get_company_ancestors(self, parent_company, child_company):
        ancestors = company_service.get_company_ancestors(child_company)
        assert parent_company in ancestors

    def test_get_company_group(self, parent_company, child_company):
        group = company_service.get_company_group(child_company)
        assert group == parent_company

    def test_get_company_group_self(self, parent_company):
        group = company_service.get_company_group(parent_company)
        assert group == parent_company

    def test_assign_and_unassign_user(
        self, regular_user, parent_company, another_company
    ):
        company_service.assign_user_to_companies(
            regular_user, [str(parent_company.id), str(another_company.id)]
        )
        assert UserCompany.objects.filter(user=regular_user).count() == 2

        company_service.unassign_user_from_company(regular_user, parent_company)
        assert UserCompany.objects.filter(user=regular_user).count() == 1

    def test_get_company_tree(self, parent_company, child_company):
        tree = company_service.get_company_tree()
        assert len(tree) >= 1
        parent_in_tree = any(n["code"] == "PARENT" for n in tree)
        assert parent_in_tree


# --- API Tests ---


@pytest.mark.django_db
class TestCompanyAPI:
    def test_list_companies_superuser(self, auth_client, parent_company):
        response = auth_client.get("/api/v1/core/companies/")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        codes = [c["code"] for c in data]
        assert "PARENT" in codes

    def test_list_companies_user_no_access(self, user_client):
        response = user_client.get("/api/v1/core/companies/")
        assert response.status_code == 200
        data = response.json()
        assert data == []

    def test_create_company_superuser(self, auth_client):
        response = auth_client.post(
            "/api/v1/core/companies/",
            {"name": "New Co", "code": "NEWCO"},
            content_type="application/json",
        )
        assert response.status_code == 200
        assert response.json()["code"] == "NEWCO"

    def test_create_company_regular_user_forbidden(self, user_client):
        response = user_client.post(
            "/api/v1/core/companies/",
            {"name": "New Co", "code": "NEWCO"},
            content_type="application/json",
        )
        assert response.status_code == 403

    def test_get_company(self, auth_client, parent_company):
        response = auth_client.get(f"/api/v1/core/companies/{parent_company.id}/")
        assert response.status_code == 200
        assert response.json()["code"] == "PARENT"

    def test_update_company(self, auth_client, parent_company):
        response = auth_client.put(
            f"/api/v1/core/companies/{parent_company.id}/",
            {"name": "Updated Parent"},
            content_type="application/json",
        )
        assert response.status_code == 200
        assert response.json()["name"] == "Updated Parent"

    def test_update_company_regular_user_forbidden(self, user_client, parent_company):
        response = user_client.put(
            f"/api/v1/core/companies/{parent_company.id}/",
            {"name": "Hacked"},
            content_type="application/json",
        )
        assert response.status_code == 403

    def test_deactivate_company(self, auth_client, parent_company):
        response = auth_client.delete(f"/api/v1/core/companies/{parent_company.id}/")
        assert response.status_code == 200
        parent_company.refresh_from_db()
        assert parent_company.is_active is False

    def test_get_company_children(self, auth_client, parent_company, child_company):
        response = auth_client.get(
            f"/api/v1/core/companies/{parent_company.id}/children/"
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["code"] == "CHILD"

    def test_add_child_company(self, auth_client, parent_company):
        response = auth_client.post(
            f"/api/v1/core/companies/{parent_company.id}/children/",
            {"name": "New Child", "code": "NCHILD"},
            content_type="application/json",
        )
        assert response.status_code == 200
        assert response.json()["code"] == "NCHILD"

    def test_get_company_tree(self, auth_client, parent_company, child_company):
        response = auth_client.get("/api/v1/core/companies/tree/")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_get_current_company_no_assignment(self, user_client, regular_user):
        response = user_client.get("/api/v1/core/companies/current/")
        print("RESPONSE:", response.status_code, response.content)
        assert response.status_code == 404

    def test_get_current_company_with_assignment(
        self, user_client, regular_user, parent_company
    ):
        User.objects.filter(pk=regular_user.pk).update(current_company=parent_company)
        response = user_client.get("/api/v1/core/companies/current/")
        assert response.status_code == 200
        assert response.json()["code"] == "PARENT"

    def test_switch_company(self, auth_client, admin_user, parent_company):
        UserCompany.objects.create(user=admin_user, company=parent_company)
        response = auth_client.post(
            "/api/v1/core/companies/switch/",
            {"id": str(parent_company.id), "name": "", "code": ""},
            content_type="application/json",
        )
        assert response.status_code == 200
        admin_user.refresh_from_db()
        assert admin_user.current_company == parent_company

    def test_set_default_company(
        self, auth_client, admin_user, parent_company, child_company
    ):
        UserCompany.objects.create(user=admin_user, company=parent_company)
        UserCompany.objects.create(user=admin_user, company=child_company)
        response = auth_client.put(
            "/api/v1/core/companies/default/",
            {"id": str(child_company.id), "name": "", "code": ""},
            content_type="application/json",
        )
        assert response.status_code == 200
        assert response.json()["code"] == "CHILD"

    def test_admin_user_companies(self, auth_client, regular_user, parent_company):
        UserCompany.objects.create(user=regular_user, company=parent_company)
        response = auth_client.get(
            f"/api/v1/core/companies/admin/user-companies/{regular_user.id}/"
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["company_name"] == parent_company.name

    def test_regular_user_cannot_access_admin(self, user_client, regular_user):
        response = user_client.get(
            f"/api/v1/core/companies/admin/user-companies/{regular_user.id}/"
        )
        assert response.status_code == 403


# --- Middleware Tests ---


@pytest.mark.django_db
class TestCompanyMiddleware:
    def test_middleware_sets_company_from_header(
        self, auth_client, admin_user, parent_company
    ):
        """X-Company-Id header sets request.company via middleware."""
        UserCompany.objects.create(
            user=admin_user, company=parent_company, is_default=True
        )
        User.objects.filter(pk=admin_user.pk).update(current_company=parent_company)
        response = auth_client.get(
            "/api/v1/core/companies/current/",
            HTTP_X_COMPANY_ID=str(parent_company.id),
        )
        assert response.status_code == 200
        assert response.json()["id"] == str(parent_company.id)

    def test_middleware_falls_back_to_user_company(
        self, user_client, regular_user, parent_company
    ):
        UserCompany.objects.create(
            user=regular_user, company=parent_company, is_default=True
        )
        User.objects.filter(pk=regular_user.pk).update(current_company=parent_company)
        response = user_client.get("/api/v1/core/companies/current/")
        assert response.status_code == 200
        assert response.json()["code"] == "PARENT"
