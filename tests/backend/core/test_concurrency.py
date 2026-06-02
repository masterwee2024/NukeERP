"""Tests for concurrency control — optimistic locking, 409 Conflict."""

import pytest

from apps.core.models import ConcurrencyError, Menu


@pytest.fixture
def admin_user(db):
    from apps.core.models import User

    return User.objects.create_superuser(
        email="admin@example.com",
        password="adminpass123",
        first_name="Admin",
        last_name="User",
    )


@pytest.fixture
def auth_client(client, admin_user):
    client.force_login(admin_user)
    return client


@pytest.fixture
def menu_item(db):
    return Menu.objects.create(
        name="Test Menu",
        slug="test-menu",
        icon="Test",
        url="/test",
        sort_order=1,
        module="test",
    )


# --- Optimistic Locking Tests ---


@pytest.mark.django_db
class TestOptimisticLocking:
    def test_version_increments_on_save(self, menu_item):
        """Version should increment on each save."""
        original_version = menu_item.version
        menu_item.name = "Updated"
        menu_item.save()
        menu_item.refresh_from_db()
        assert menu_item.version == original_version + 1

    def test_version_increments_multiple_saves(self, menu_item):
        """Version should increment correctly across multiple saves."""
        for i in range(5):
            menu_item.name = f"Update {i}"
            menu_item.save()
        menu_item.refresh_from_db()
        assert menu_item.version == 6  # Started at 1, incremented 5 times

    def test_concurrency_error_on_stale_version(self, menu_item):
        """Saving with stale version should raise ConcurrencyError."""
        # Simulate two users loading the same record
        user1 = Menu.objects.get(id=menu_item.id)
        user2 = Menu.objects.get(id=menu_item.id)

        # User 1 saves first — succeeds
        user1.name = "User 1 Update"
        user1.save()

        # User 2 saves with stale version — should fail
        user2.name = "User 2 Update"
        with pytest.raises(ConcurrencyError):
            user2.save()

    def test_concurrency_error_message(self, menu_item):
        """ConcurrencyError should have descriptive message."""
        user1 = Menu.objects.get(id=menu_item.id)
        user2 = Menu.objects.get(id=menu_item.id)

        user1.save()

        with pytest.raises(ConcurrencyError, match="modified by another user"):
            user2.save()


# --- API Concurrency Tests ---


@pytest.mark.django_db
class TestAPIConcurrency:
    def test_update_with_correct_version(self, auth_client, menu_item):
        """Update with correct version should succeed."""
        response = auth_client.put(
            f"/api/v1/core/menus/{menu_item.id}/",
            {
                "name": "Updated Menu",
                "updated_at": menu_item.updated_at.isoformat(),
            },
            content_type="application/json",
        )
        assert response.status_code == 200
        assert response.json()["name"] == "Updated Menu"

    def test_update_with_stale_version_returns_409(self, auth_client, menu_item):
        """Update with stale version should return 409 Conflict."""
        # First update — succeeds
        auth_client.put(
            f"/api/v1/core/menus/{menu_item.id}/",
            {
                "name": "First Update",
                "updated_at": menu_item.updated_at.isoformat(),
            },
            content_type="application/json",
        )

        # Second update with original (stale) version — should fail
        response = auth_client.put(
            f"/api/v1/core/menus/{menu_item.id}/",
            {
                "name": "Second Update",
                "updated_at": menu_item.updated_at.isoformat(),  # Stale!
            },
            content_type="application/json",
        )
        assert response.status_code == 409

    def test_409_response_contains_conflict_flag(self, auth_client, menu_item):
        """409 response should contain conflict flag."""
        response = auth_client.put(
            f"/api/v1/core/menus/{menu_item.id}/",
            {
                "name": "Update",
                "updated_at": menu_item.updated_at.isoformat(),
            },
            content_type="application/json",
        )
        # First update succeeds, then second with stale version
        auth_client.put(
            f"/api/v1/core/menus/{menu_item.id}/",
            {"name": "Update 2"},
            content_type="application/json",
        )

        response = auth_client.put(
            f"/api/v1/core/menus/{menu_item.id}/",
            {
                "name": "Stale Update",
                "updated_at": menu_item.updated_at.isoformat(),
            },
            content_type="application/json",
        )
        assert response.status_code == 409
