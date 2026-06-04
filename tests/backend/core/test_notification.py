"""Tests for Notifications and Email Approval system."""

import uuid
from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework_simplejwt.tokens import AccessToken

from apps.core.models import (
    ApprovalToken,
    Company,
    WorkflowDefinition,
    WorkflowExecution,
)
from apps.core.services.email_approval_service import (
    generate_approval_token,
    process_email_approval,
)
from apps.core.services.notification_service import (
    get_unread_count,
    mark_all_as_read,
    mark_as_read,
    send_notification,
)
from apps.core.services.push_service import subscribe_push, unsubscribe_push

User = get_user_model()


# --- Fixtures ---


@pytest.fixture
def company(db):
    return Company.objects.create(name="Test Company", code="TC")


@pytest.fixture
def user(db):
    return User.objects.create_user(
        email="test@pyerp.local", password="testpassword123"
    )


@pytest.fixture
def approver(db):
    return User.objects.create_user(
        email="approver@pyerp.local", password="testpassword123"
    )


@pytest.fixture
def workflow(db, company):
    return WorkflowDefinition.objects.create(
        name="Test Workflow",
        module="financial",
        document_type="Invoice",
        company=company,
        is_active=True,
    )


@pytest.fixture
def execution(db, workflow, user, company):
    return WorkflowExecution.objects.create(
        workflow=workflow,
        document_type="Invoice",
        document_id=uuid.uuid4(),
        status="pending",
        requester=user,
        created_by=user,
        company=company,
    )


# --- Notification Services & Models ---


@pytest.mark.django_db
def test_send_and_read_notifications(user, company):
    # Test send_notification creates records and handles defaults
    notif = send_notification(
        recipient=user,
        slug="new_alert",
        title="Alert Title",
        message="Alert Message",
        link="/app/alert",
        company=company,
    )

    assert notif.recipient == user
    assert notif.title == "Alert Title"
    assert notif.message == "Alert Message"
    assert notif.link == "/app/alert"
    assert notif.company == company
    assert notif.is_read is False

    # Get unread count
    assert get_unread_count(user) == 1

    # Mark as read
    mark_as_read(notif.id, user)
    notif.refresh_from_db()
    assert notif.is_read is True
    assert notif.read_at is not None
    assert get_unread_count(user) == 0


@pytest.mark.django_db
def test_mark_all_as_read(user):
    send_notification(user, "alert_1", "Title 1", "Message 1")
    send_notification(user, "alert_2", "Title 2", "Message 2")
    assert get_unread_count(user) == 2

    mark_all_as_read(user)
    assert get_unread_count(user) == 0


# --- Push Subscription Services ---


@pytest.mark.django_db
def test_push_subscriptions(user):
    # Subscribe
    sub = subscribe_push(
        user=user,
        endpoint="https://fcm.googleapis.com/fcm/send/123",
        p256dh="p256dhkey",
        auth="authkey",
        user_agent="Mozilla/5.0",
    )
    assert sub.user == user
    assert sub.endpoint == "https://fcm.googleapis.com/fcm/send/123"
    assert sub.is_active is True

    # Unsubscribe
    unsubscribe_push(user)
    sub.refresh_from_db()
    assert sub.is_active is False


# --- Email Approvals ---


@pytest.mark.django_db
def test_generate_and_process_approval_token(execution, approver, company):
    # Mock user company access check
    from apps.core.services.workflow_service import UserCompany

    UserCompany.objects.create(user=approver, company=company)

    # Generate token
    token = generate_approval_token(execution, approver, "approve")
    assert token is not None

    token_obj = ApprovalToken.objects.get(token=token)
    assert token_obj.execution == execution
    assert token_obj.user == approver
    assert token_obj.action == "approve"
    assert token_obj.is_used is False

    # Process token approval
    res = process_email_approval(token, comment="Approved from link")
    assert res["status"] == "success"

    token_obj.refresh_from_db()
    assert token_obj.is_used is True
    assert token_obj.used_at is not None


@pytest.mark.django_db
def test_expired_approval_token(execution, approver):
    token = generate_approval_token(execution, approver, "approve")
    token_obj = ApprovalToken.objects.get(token=token)
    token_obj.expires_at = timezone.now() - timedelta(minutes=1)
    token_obj.save()

    res = process_email_approval(token)
    assert res["status"] == "error"
    assert "expired" in res["message"].lower()


@pytest.mark.django_db
def test_reused_approval_token(execution, approver, company):
    from apps.core.services.workflow_service import UserCompany

    UserCompany.objects.create(user=approver, company=company)

    token = generate_approval_token(execution, approver, "approve")

    res1 = process_email_approval(token)
    assert res1["status"] == "success"

    res2 = process_email_approval(token)
    assert res2["status"] == "error"
    assert "already" in res2["message"].lower()


# --- API Endpoints ---


@pytest.mark.django_db
class TestNotificationAPI:
    def test_list_notifications_api(self, client, user):
        send_notification(user, "alert_1", "Title 1", "Msg 1")
        token = AccessToken.for_user(user)

        response = client.get(
            "/api/v1/core/notifications/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 1
        assert data["results"][0]["title"] == "Title 1"

    def test_unread_count_api(self, client, user):
        send_notification(user, "alert_1", "Title 1", "Msg 1")
        token = AccessToken.for_user(user)

        response = client.get(
            "/api/v1/core/notifications/unread-count/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        assert response.status_code == 200
        assert response.json()["count"] == 1

    def test_mark_read_api(self, client, user):
        notif = send_notification(user, "alert_1", "Title 1", "Msg 1")
        token = AccessToken.for_user(user)

        response = client.put(
            f"/api/v1/core/notifications/{notif.id}/read/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        assert response.status_code == 200
        notif.refresh_from_db()
        assert notif.is_read is True

    def test_mark_all_read_api(self, client, user):
        send_notification(user, "alert_1", "Title 1", "Msg 1")
        token = AccessToken.for_user(user)

        response = client.put(
            "/api/v1/core/notifications/read-all/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        assert response.status_code == 200
        assert get_unread_count(user) == 0

    def test_push_subscribe_api(self, client, user):
        token = AccessToken.for_user(user)
        payload = {
            "endpoint": "https://fcm.googleapis.com/fcm/send/abc",
            "p256dh": "p256dhkey",
            "auth": "authkey",
            "user_agent": "Mozilla",
        }

        response = client.post(
            "/api/v1/core/notifications/push/subscribe/",
            data=payload,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        assert response.status_code == 200
        assert user.push_subscriptions.filter(is_active=True).exists()

    def test_push_unsubscribe_api(self, client, user):
        subscribe_push(user, "https://example.com/endpoint", "p256dh", "auth")
        token = AccessToken.for_user(user)

        response = client.delete(
            "/api/v1/core/notifications/push/unsubscribe/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        assert response.status_code == 200
        assert not user.push_subscriptions.filter(is_active=True).exists()
