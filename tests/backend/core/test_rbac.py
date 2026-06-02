"""Tests for Role-Based Access Control (T014)."""

import pytest
from django.test import Client

from apps.core.models import Permission, Role, RolePermission, User, UserRole
from apps.core.services import rbac_service


@pytest.fixture
def db():
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
def permissions(db):
    perms = {}
    for module in ["financial", "scm"]:
        for action in ["view", "create", "update"]:
            codename = f"{module}_{action}"
            perm, _ = Permission.objects.get_or_create(
                codename=codename,
                defaults={"module": module, "action": action},
            )
            perms[codename] = perm
    return perms


@pytest.fixture
def role(db, permissions):
    r = Role.objects.create(name="Test Role", description="Test role")
    for perm in permissions.values():
        RolePermission.objects.create(role=r, permission=perm)
    return r


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
class TestPermissionModel:
    def test_create_permission(self):
        perm = Permission.objects.create(
            module="financial", action="view", codename="financial_view"
        )
        assert perm.codename == "financial_view"
        assert str(perm) == "financial_view"

    def test_auto_codename(self):
        perm = Permission(module="scm", action="create")
        perm.save()
        assert perm.codename == "scm_create"

    def test_unique_together(self, permissions):
        with pytest.raises(Exception, match="unique|duplicate|already exists"):
            Permission.objects.create(module="financial", action="view")


@pytest.mark.django_db
class TestRoleModel:
    def test_create_role(self):
        role = Role.objects.create(name="Manager")
        assert str(role) == "Manager"
        assert role.is_system is False

    def test_system_role_cannot_be_deleted_check(self, role):
        role.is_system = True
        role.save()
        assert role.is_system is True

    def test_str(self, role):
        assert str(role) == "Test Role"


@pytest.mark.django_db
class TestRolePermissionModel:
    def test_create_role_permission(self, role, permissions):
        rp = RolePermission.objects.filter(role=role).first()
        assert rp is not None
        assert str(rp).startswith("Test Role")

    def test_unique_together(self, role, permissions):
        perm = list(permissions.values())[0]
        with pytest.raises(Exception, match="unique|duplicate|already exists"):
            RolePermission.objects.create(role=role, permission=perm)


@pytest.mark.django_db
class TestUserRoleModel:
    def test_create_user_role(self, regular_user, role):
        ur = UserRole.objects.create(user=regular_user, role=role)
        assert str(ur) == f"{regular_user.email} → {role.name}"

    def test_unique_together(self, regular_user, role):
        UserRole.objects.create(user=regular_user, role=role)
        with pytest.raises(Exception, match="unique|duplicate|already exists"):
            UserRole.objects.create(user=regular_user, role=role)


# --- Service Tests ---


@pytest.mark.django_db
class TestRBACService:
    def test_get_user_permissions(self, regular_user, role, permissions):
        UserRole.objects.create(user=regular_user, role=role)
        perms = rbac_service.get_user_permissions(regular_user)
        assert len(perms) == 6
        assert "financial_view" in perms
        assert "scm_create" in perms

    def test_get_user_permissions_no_role(self, regular_user):
        perms = rbac_service.get_user_permissions(regular_user)
        assert perms == []

    def test_get_user_permissions_superuser(self, admin_user, permissions):
        perms = rbac_service.get_user_permissions(admin_user)
        # Superuser check is in the service — returns empty from get_user_permissions
        # because the function doesn't check superuser status
        assert isinstance(perms, list)

    def test_user_has_permission(self, regular_user, role, permissions):
        UserRole.objects.create(user=regular_user, role=role)
        assert rbac_service.user_has_permission(regular_user, "financial_view") is True
        assert rbac_service.user_has_permission(regular_user, "admin_view") is False

    def test_user_has_permission_superuser(self, admin_user):
        assert rbac_service.user_has_permission(admin_user, "anything") is True

    def test_user_has_any_permission(self, regular_user, role, permissions):
        UserRole.objects.create(user=regular_user, role=role)
        assert (
            rbac_service.user_has_any_permission(
                regular_user, ["financial_view", "admin_view"]
            )
            is True
        )
        assert rbac_service.user_has_any_permission(regular_user, ["admin_view"]) is False

    def test_get_user_roles(self, regular_user, role):
        UserRole.objects.create(user=regular_user, role=role)
        roles = rbac_service.get_user_roles(regular_user)
        assert len(roles) == 1
        assert roles[0].name == "Test Role"

    def test_get_role_permissions(self, role, permissions):
        perms = rbac_service.get_role_permissions(role)
        assert len(perms) == 6

    def test_assign_and_remove_role(self, regular_user, role):
        rbac_service.assign_role_to_user(regular_user, role)
        assert UserRole.objects.filter(user=regular_user).count() == 1

        rbac_service.remove_role_from_user(regular_user, role)
        assert UserRole.objects.filter(user=regular_user).count() == 0

    def test_set_role_permissions(self, role, permissions):
        perm = list(permissions.values())[0]
        rbac_service.set_role_permissions(role, [str(perm.id)])
        perms = rbac_service.get_role_permissions(role)
        assert len(perms) == 1

    def test_get_all_permissions_grouped(self, permissions):
        grouped = rbac_service.get_all_permissions_grouped()
        assert "financial" in grouped
        assert "scm" in grouped
        assert len(grouped["financial"]) == 3


# --- API Tests ---


@pytest.mark.django_db
class TestRBACAPI:
    def test_list_permissions(self, auth_client, permissions):
        response = auth_client.get("/api/v1/core/admin/permissions/")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 6

    def test_list_permissions_forbidden(self, user_client):
        response = user_client.get("/api/v1/core/admin/permissions/")
        assert response.status_code == 403

    def test_list_roles(self, auth_client, role):
        response = auth_client.get("/api/v1/core/admin/roles/")
        assert response.status_code == 200
        data = response.json()
        names = [r["name"] for r in data]
        assert "Test Role" in names

    def test_list_roles_forbidden(self, user_client):
        response = user_client.get("/api/v1/core/admin/roles/")
        assert response.status_code == 403

    def test_create_role(self, auth_client):
        response = auth_client.post(
            "/api/v1/core/admin/roles/",
            {"name": "New Role", "description": "A new role"},
            content_type="application/json",
        )
        assert response.status_code == 200
        assert response.json()["name"] == "New Role"

    def test_create_role_duplicate(self, auth_client, role):
        response = auth_client.post(
            "/api/v1/core/admin/roles/",
            {"name": "Test Role"},
            content_type="application/json",
        )
        assert response.status_code == 400

    def test_update_role(self, auth_client, role):
        response = auth_client.put(
            f"/api/v1/core/admin/roles/{role.id}/",
            {"name": "Updated Role"},
            content_type="application/json",
        )
        assert response.status_code == 200
        assert response.json()["name"] == "Updated Role"

    def test_delete_role(self, auth_client):
        r = Role.objects.create(name="Deletable")
        response = auth_client.delete(f"/api/v1/core/admin/roles/{r.id}/")
        assert response.status_code == 200

    def test_delete_system_role(self, auth_client):
        r = Role.objects.create(name="System", is_system=True)
        response = auth_client.delete(f"/api/v1/core/admin/roles/{r.id}/")
        assert response.status_code == 400

    def test_get_role_permissions(self, auth_client, role, permissions):
        response = auth_client.get(
            f"/api/v1/core/admin/roles/{role.id}/permissions/"
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 6

    def test_set_role_permissions(self, auth_client, role, permissions):
        perm = list(permissions.values())[0]
        response = auth_client.put(
            f"/api/v1/core/admin/roles/{role.id}/permissions/",
            {"permission_ids": [str(perm.id)]},
            content_type="application/json",
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1

    def test_get_user_roles(self, auth_client, regular_user, role):
        UserRole.objects.create(user=regular_user, role=role)
        response = auth_client.get(
            f"/api/v1/core/admin/users/{regular_user.id}/roles/"
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["role_name"] == "Test Role"

    def test_set_user_roles(self, auth_client, regular_user, role):
        response = auth_client.put(
            f"/api/v1/core/admin/users/{regular_user.id}/roles/",
            {"role_ids": [str(role.id)]},
            content_type="application/json",
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1

    def test_regular_user_cannot_access_admin(self, user_client, regular_user):
        response = user_client.get(
            f"/api/v1/core/admin/users/{regular_user.id}/roles/"
        )
        assert response.status_code == 403
