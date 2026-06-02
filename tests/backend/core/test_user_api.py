"""Tests for User Management API (T015)."""

import pytest
from django.contrib.auth.hashers import check_password
from django.test import Client

from apps.core.models import LoginHistory, Role, User, UserRole


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
def test_role(db):
    return Role.objects.create(name="Test Role")


@pytest.fixture
def auth_client(admin_user):
    from rest_framework_simplejwt.tokens import AccessToken

    client = Client()
    token = AccessToken.for_user(admin_user)
    client.defaults["HTTP_AUTHORIZATION"] = f"Bearer {token}"
    return client


@pytest.fixture
def user_client(regular_user):
    from rest_framework_simplejwt.tokens import AccessToken

    client = Client()
    token = AccessToken.for_user(regular_user)
    client.defaults["HTTP_AUTHORIZATION"] = f"Bearer {token}"
    return client


# --- Model Tests ---


@pytest.mark.django_db
class TestLoginHistoryModel:
    def test_create_login_history(self, regular_user):
        lh = LoginHistory.objects.create(
            user=regular_user,
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
            device_type="desktop",
        )
        assert lh.ip_address == "192.168.1.1"
        assert str(lh).startswith(regular_user.email)

    def test_login_history_ordering(self, regular_user):
        LoginHistory.objects.create(user=regular_user)
        LoginHistory.objects.create(user=regular_user)
        history = LoginHistory.objects.all()
        assert history.count() == 2
        assert history[0].login_time >= history[1].login_time


# --- API Tests ---


@pytest.mark.django_db
class TestUserAPI:
    def test_list_users(self, auth_client, regular_user):
        response = auth_client.get("/api/v1/core/admin/users/")
        assert response.status_code == 200
        data = response.json()
        emails = [u["email"] for u in data]
        assert regular_user.email in emails
        assert "admin@example.com" in emails

    def test_list_users_forbidden(self, user_client):
        response = user_client.get("/api/v1/core/admin/users/")
        assert response.status_code == 403

    def test_search_users(self, auth_client, regular_user):
        response = auth_client.get("/api/v1/core/admin/users/?search=Regular")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["email"] == "user@example.com"

    def test_filter_by_active(self, auth_client, regular_user):
        regular_user.is_active = False
        regular_user.save()
        response = auth_client.get("/api/v1/core/admin/users/?is_active=true")
        assert response.status_code == 200
        data = response.json()
        assert all(u["is_active"] for u in data)

    def test_filter_by_role(self, auth_client, regular_user, test_role):
        UserRole.objects.create(user=regular_user, role=test_role)
        response = auth_client.get(f"/api/v1/core/admin/users/?role_id={test_role.id}")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["email"] == "user@example.com"

    def test_create_user(self, auth_client, test_role):
        response = auth_client.post(
            "/api/v1/core/admin/users/",
            {
                "email": "new@example.com",
                "password": "newpass123",
                "first_name": "New",
                "last_name": "User",
                "role_ids": [str(test_role.id)],
            },
            content_type="application/json",
        )
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "new@example.com"
        assert len(data["roles"]) == 1
        assert data["roles"][0]["name"] == "Test Role"

    def test_create_user_duplicate_email(self, auth_client, regular_user):
        response = auth_client.post(
            "/api/v1/core/admin/users/",
            {"email": "user@example.com", "password": "pass123"},
            content_type="application/json",
        )
        assert response.status_code == 400

    def test_create_user_forbidden(self, user_client):
        response = user_client.post(
            "/api/v1/core/admin/users/",
            {"email": "new@example.com", "password": "pass123"},
            content_type="application/json",
        )
        assert response.status_code == 403

    def test_update_user(self, auth_client, regular_user, test_role):
        response = auth_client.put(
            f"/api/v1/core/admin/users/{regular_user.id}/",
            {
                "first_name": "Updated",
                "role_ids": [str(test_role.id)],
            },
            content_type="application/json",
        )
        assert response.status_code == 200
        data = response.json()
        assert data["first_name"] == "Updated"
        assert len(data["roles"]) == 1

    def test_deactivate_user(self, auth_client, regular_user):
        response = auth_client.post(
            f"/api/v1/core/admin/users/{regular_user.id}/deactivate/"
        )
        assert response.status_code == 200
        regular_user.refresh_from_db()
        assert regular_user.is_active is False

    def test_deactivate_self(self, auth_client, admin_user):
        response = auth_client.post(
            f"/api/v1/core/admin/users/{admin_user.id}/deactivate/"
        )
        assert response.status_code == 400

    def test_reactivate_user(self, auth_client, regular_user):
        regular_user.is_active = False
        regular_user.save()
        response = auth_client.post(
            f"/api/v1/core/admin/users/{regular_user.id}/reactivate/"
        )
        assert response.status_code == 200
        regular_user.refresh_from_db()
        assert regular_user.is_active is True

    def test_reset_password(self, auth_client, regular_user):
        response = auth_client.post(
            f"/api/v1/core/admin/users/{regular_user.id}/reset-password/",
            {"new_password": "newsecurepass123"},
            content_type="application/json",
        )
        assert response.status_code == 200
        regular_user.refresh_from_db()
        assert check_password("newsecurepass123", regular_user.password) is True

    def test_login_history(self, auth_client, regular_user):
        LoginHistory.objects.create(
            user=regular_user,
            ip_address="10.0.0.1",
            user_agent="test-agent",
        )
        response = auth_client.get(
            f"/api/v1/core/admin/users/{regular_user.id}/login-history/"
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["ip_address"] == "10.0.0.1"
