"""Tests for the authentication system."""

import pytest
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.fixture
def test_user(db):
    """Create a test user."""
    return User.objects.create_user(
        email="test@example.com",
        password="testpass123",
        first_name="Test",
        last_name="User",
    )


@pytest.fixture
def admin_user(db):
    """Create a superuser."""
    return User.objects.create_superuser(
        email="admin@example.com",
        password="adminpass123",
        first_name="Admin",
        last_name="User",
    )


@pytest.fixture
def auth_client(client, test_user):
    """Client authenticated as test_user via JWT."""
    from rest_framework_simplejwt.tokens import AccessToken

    token = AccessToken.for_user(test_user)
    client.defaults["HTTP_AUTHORIZATION"] = f"Bearer {token}"
    return client


# --- Login Tests ---


@pytest.mark.django_db
class TestLogin:
    def test_login_success(self, client, test_user):
        response = client.post(
            "/api/v1/core/auth/login/",
            {"email": "test@example.com", "password": "testpass123"},
            content_type="application/json",
        )
        assert response.status_code == 200
        data = response.json()
        assert "access" in data
        assert "refresh" in data
        assert data["user"]["email"] == "test@example.com"

    def test_login_invalid_credentials(self, client, test_user):
        response = client.post(
            "/api/v1/core/auth/login/",
            {"email": "test@example.com", "password": "wrongpassword"},
            content_type="application/json",
        )
        assert response.status_code == 401

    def test_login_nonexistent_user(self, client):
        response = client.post(
            "/api/v1/core/auth/login/",
            {"email": "nonexistent@example.com", "password": "password"},
            content_type="application/json",
        )
        assert response.status_code == 401


# --- Register Tests ---


@pytest.mark.django_db
class TestRegister:
    def test_register_success(self, client):
        response = client.post(
            "/api/v1/core/auth/register/",
            {
                "email": "new@example.com",
                "password": "newpass123",
                "first_name": "New",
                "last_name": "User",
            },
            content_type="application/json",
        )
        assert response.status_code == 200
        data = response.json()
        assert "access" in data
        assert data["user"]["email"] == "new@example.com"
        assert User.objects.filter(email="new@example.com").exists()

    def test_register_duplicate_email(self, client, test_user):
        response = client.post(
            "/api/v1/core/auth/register/",
            {"email": "test@example.com", "password": "password123"},
            content_type="application/json",
        )
        assert response.status_code == 400


# --- Me Tests ---


@pytest.mark.django_db
class TestMe:
    def test_get_me_authenticated(self, auth_client, test_user):
        response = auth_client.get("/api/v1/core/auth/me/")
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "test@example.com"
        assert data["first_name"] == "Test"

    def test_get_me_unauthenticated(self, client):
        response = client.get("/api/v1/core/auth/me/")
        assert response.status_code == 401


# --- Logout Tests ---


@pytest.mark.django_db
class TestLogout:
    def test_logout(self, auth_client):
        response = auth_client.post(
            "/api/v1/core/auth/logout/",
            content_type="application/json",
        )
        assert response.status_code == 200
        assert response.json()["detail"] == "Logged out successfully"


# --- Forgot/Reset Password Tests ---


@pytest.mark.django_db
class TestPasswordReset:
    def test_forgot_password(self, client, test_user):
        response = client.post(
            "/api/v1/core/auth/forgot-password/",
            {"email": "test@example.com"},
            content_type="application/json",
        )
        assert response.status_code == 200
        data = response.json()
        assert "reset_token" in data
        assert "uid" in data

    def test_forgot_password_nonexistent_email(self, client):
        response = client.post(
            "/api/v1/core/auth/forgot-password/",
            {"email": "nonexistent@example.com"},
            content_type="application/json",
        )
        # Don't reveal if user exists
        assert response.status_code == 200

    def test_reset_password_invalid_token(self, client, test_user):
        from django.utils.encoding import force_bytes
        from django.utils.http import urlsafe_base64_encode

        uid = urlsafe_base64_encode(force_bytes(test_user.pk))
        response = client.post(
            "/api/v1/core/auth/reset-password/",
            {"uid": uid, "token": "invalid-token", "new_password": "newpass123"},
            content_type="application/json",
        )
        assert response.status_code == 400

    def test_reset_password_invalid_uid(self, client):
        response = client.post(
            "/api/v1/core/auth/reset-password/",
            {"uid": "invalid-uid", "token": "token", "new_password": "newpass123"},
            content_type="application/json",
        )
        assert response.status_code == 400
