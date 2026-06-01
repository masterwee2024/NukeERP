"""Tests for the Menu system — models, tree building, permissions, API."""

import pytest
from django.contrib.auth.models import Group, User
from django.db import IntegrityError

from apps.core.models import Menu, MenuRole


@pytest.fixture
def admin_user(db):
    """Create a superuser."""
    return User.objects.create_superuser(
        username="admin",
        email="admin@example.com",
        password="adminpass123",
    )


@pytest.fixture
def regular_user(db):
    """Create a regular user with no groups."""
    return User.objects.create_user(
        username="regular",
        email="regular@example.com",
        password="regularpass123",
    )


@pytest.fixture
def test_group(db):
    """Create a test group."""
    return Group.objects.create(name="Test Group")


@pytest.fixture
def user_with_role(db, regular_user, test_group):
    """Create a user assigned to a group."""
    regular_user.groups.add(test_group)
    return regular_user


@pytest.fixture
def menu_items(db):
    """Create a menu hierarchy for testing."""
    root = Menu.objects.create(
        name="Financial",
        slug="financial",
        icon="DollarSign",
        url="",
        sort_order=10,
        module="financial",
        level=0,
    )
    child = Menu.objects.create(
        name="General Ledger",
        slug="financial-gl",
        icon="FileText",
        url="/app/financial/gl",
        parent=root,
        sort_order=1,
        module="financial",
        level=1,
    )
    grandchild = Menu.objects.create(
        name="Journal Entries",
        slug="financial-gl-journal",
        icon="ScrollText",
        url="/app/financial/gl/journal",
        parent=child,
        sort_order=1,
        module="financial",
        level=2,
    )
    inactive = Menu.objects.create(
        name="Inactive Menu",
        slug="inactive-menu",
        is_active=False,
        sort_order=99,
    )
    return {
        "root": root,
        "child": child,
        "grandchild": grandchild,
        "inactive": inactive,
    }


# --- Model Tests ---


@pytest.mark.django_db
class TestMenuModel:
    def test_menu_str(self, menu_items):
        assert str(menu_items["root"]) == "Financial"

    def test_menu_parent_child(self, menu_items):
        assert menu_items["child"].parent == menu_items["root"]
        assert menu_items["grandchild"].parent == menu_items["child"]

    def test_menu_level(self, menu_items):
        assert menu_items["root"].level == 0
        assert menu_items["child"].level == 1
        assert menu_items["grandchild"].level == 2

    def test_get_ancestors(self, menu_items):
        ancestors = menu_items["grandchild"].get_ancestors()
        assert len(ancestors) == 2
        assert ancestors[0] == menu_items["root"]
        assert ancestors[1] == menu_items["child"]

    def test_get_descendants(self, menu_items):
        descendants = menu_items["root"].get_descendants()
        assert len(descendants) == 2
        assert menu_items["child"] in descendants
        assert menu_items["grandchild"] in descendants

    def test_get_descendants_include_self(self, menu_items):
        descendants = menu_items["root"].get_descendants(include_self=True)
        assert len(descendants) == 3
        assert menu_items["root"] in descendants

    def test_inactive_menu_excluded_from_descendants(self, menu_items):
        descendants = menu_items["root"].get_descendants()
        assert menu_items["inactive"] not in descendants


@pytest.mark.django_db
class TestMenuRoleModel:
    def test_menu_role_str(self, menu_items, test_group):
        mr = MenuRole.objects.create(menu=menu_items["root"], role=test_group)
        assert "Financial" in str(mr)
        assert "Test Group" in str(mr)

    def test_unique_together(self, menu_items, test_group):
        MenuRole.objects.create(menu=menu_items["root"], role=test_group)
        with pytest.raises(IntegrityError):
            MenuRole.objects.create(menu=menu_items["root"], role=test_group)


# --- Tree Building Tests ---


@pytest.mark.django_db
class TestMenuTree:
    def test_build_tree(self, menu_items):
        from apps.core.api.menu_api import _build_tree

        menus = Menu.objects.filter(is_active=True).order_by("sort_order")
        tree = _build_tree(menus, parent_id=None)

        assert len(tree) == 1
        assert tree[0]["name"] == "Financial"
        assert len(tree[0]["children"]) == 1
        assert tree[0]["children"][0]["name"] == "General Ledger"
        assert len(tree[0]["children"][0]["children"]) == 1

    def test_inactive_excluded_from_tree(self, menu_items):
        from apps.core.api.menu_api import _build_tree

        menus = Menu.objects.filter(is_active=True).order_by("sort_order")
        tree = _build_tree(menus, parent_id=None)

        all_slugs = [node["slug"] for node in tree]
        assert "inactive-menu" not in all_slugs


# --- Permission Filtering Tests ---


@pytest.mark.django_db
class TestMenuPermissions:
    def test_superuser_sees_all(self, admin_user, menu_items):
        from apps.core.api.menu_api import _get_user_menu_ids

        ids = _get_user_menu_ids(admin_user)
        assert menu_items["root"].id in ids
        assert menu_items["child"].id in ids
        assert menu_items["inactive"].id not in ids

    def test_user_with_role_sees_assigned(self, user_with_role, menu_items, test_group):
        from apps.core.api.menu_api import _get_user_menu_ids

        MenuRole.objects.create(menu=menu_items["root"], role=test_group)
        ids = _get_user_menu_ids(user_with_role)
        assert menu_items["root"].id in ids
        assert menu_items["child"].id not in ids  # Not assigned

    def test_user_without_role_sees_nothing(self, regular_user, menu_items):
        from apps.core.api.menu_api import _get_user_menu_ids

        ids = _get_user_menu_ids(regular_user)
        assert len(ids) == 0


# --- API Tests ---


@pytest.mark.django_db
class TestMenuAPI:
    def test_get_menu_tree_authenticated(self, client, admin_user, menu_items):
        client.force_login(admin_user)
        response = client.get("/api/v1/core/menus/")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "Financial"

    def test_get_menu_tree_unauthenticated(self, client, menu_items):
        response = client.get("/api/v1/core/menus/")
        assert response.status_code == 401

    def test_create_menu_admin(self, client, admin_user, menu_items):
        client.force_login(admin_user)
        response = client.post(
            "/api/v1/core/menus/",
            {
                "name": "New Menu",
                "slug": "new-menu",
                "icon": "Plus",
                "url": "/app/new",
                "sort_order": 50,
                "module": "test",
            },
            content_type="application/json",
        )
        assert response.status_code == 200
        assert response.json()["name"] == "New Menu"

    def test_create_menu_non_admin(self, client, regular_user, menu_items):
        client.force_login(regular_user)
        response = client.post(
            "/api/v1/core/menus/",
            {
                "name": "New Menu",
                "slug": "new-menu",
            },
            content_type="application/json",
        )
        assert response.status_code == 403

    def test_update_menu_admin(self, client, admin_user, menu_items):
        client.force_login(admin_user)
        menu_id = menu_items["root"].id
        response = client.put(
            f"/api/v1/core/menus/{menu_id}/",
            {"name": "Updated Financial"},
            content_type="application/json",
        )
        assert response.status_code == 200
        assert response.json()["name"] == "Updated Financial"

    def test_delete_menu_admin(self, client, admin_user, menu_items):
        client.force_login(admin_user)
        menu_id = menu_items["inactive"].id
        response = client.delete(f"/api/v1/core/menus/{menu_id}/")
        assert response.status_code == 200
        menu_items["inactive"].refresh_from_db()
        assert menu_items["inactive"].is_active is False
