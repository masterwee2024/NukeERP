"""Notification and email approval API endpoints."""

from datetime import datetime
from uuid import UUID

from ninja import Router, Schema
from ninja.errors import HttpError

from apps.core.models import Notification
from apps.core.services.email_approval_service import process_email_approval

router = Router()
approvals_router = Router()


class NotificationTypeOut(Schema):
    name: str
    slug: str


class NotificationOut(Schema):
    id: str
    notification_type: NotificationTypeOut
    title: str
    message: str
    link: str = ""
    is_read: bool
    read_at: datetime | None = None
    created_at: datetime

    @staticmethod
    def resolve_id(obj):
        return str(obj.id)


class NotificationListOut(Schema):
    count: int
    results: list[NotificationOut]


class PushSubscriptionSchema(Schema):
    endpoint: str
    p256dh: str
    auth: str
    user_agent: str = ""


def _get_company_id(request) -> UUID | None:
    company_id = request.headers.get("X-Company-Id")
    if company_id:
        try:
            return UUID(company_id)
        except ValueError:
            return None
    return None


@router.get("/", response=NotificationListOut)
def list_notifications(
    request,
    page: int = 1,
    page_size: int = 20,
    unread_only: bool = False,
):
    """List paginated notifications for the authenticated user."""
    qs = Notification.objects.filter(recipient=request.auth).select_related(
        "notification_type"
    )

    company_id = _get_company_id(request)
    if company_id:
        qs = qs.filter(company_id=company_id)

    if unread_only:
        qs = qs.filter(is_read=False)

    total = qs.count()
    start = (page - 1) * page_size
    end = start + page_size
    items = qs.order_by("-created_at")[start:end]

    return {
        "count": total,
        "results": [NotificationOut.from_orm(item) for item in items],
    }


@router.get("/unread-count/")
def unread_count(request):
    """Get the unread notification count for the logged-in user."""
    from apps.core.services.notification_service import get_unread_count

    count = get_unread_count(request.auth)
    return {"count": count}


@router.put("/{id}/read/")
def mark_notification_read(request, id: UUID):
    """Mark a specific notification as read."""
    from apps.core.services.notification_service import mark_as_read

    try:
        mark_as_read(str(id), request.auth)
        return {"detail": "Notification marked as read"}
    except Notification.DoesNotExist:
        raise HttpError(404, "Notification not found") from None


@router.put("/read-all/")
def mark_all_notifications_read(request):
    """Mark all notifications of the user as read."""
    from apps.core.services.notification_service import mark_all_as_read

    mark_all_as_read(request.auth)
    return {"detail": "All notifications marked as read"}


@router.post("/push/subscribe/")
def subscribe_push_notification(request, payload: PushSubscriptionSchema):
    """Register/update user's push subscription."""
    from apps.core.services.push_service import subscribe_push

    subscribe_push(
        user=request.auth,
        endpoint=payload.endpoint,
        p256dh=payload.p256dh,
        auth=payload.auth,
        user_agent=payload.user_agent,
    )
    return {"detail": "Push subscription registered"}


@router.delete("/push/unsubscribe/")
def unsubscribe_push_notification(request):
    """Deactivate all push subscriptions for the user."""
    from apps.core.services.push_service import unsubscribe_push

    unsubscribe_push(request.auth)
    return {"detail": "Push subscription removed"}


@router.get("/push/status/")
def push_status(request):
    """Check if the user has an active push subscription."""
    has_sub = request.auth.push_subscriptions.filter(is_active=True).exists()
    return {"subscribed": has_sub}


@router.get("/push/vapid-key/", auth=None)
def get_vapid_public_key(request):
    """Get the public VAPID key configured on the server."""
    from django.conf import settings

    return {"public_key": getattr(settings, "VAPID_PUBLIC_KEY", "")}


@approvals_router.get("/execute", auth=None)
def execute_email_approval(request, token: str, action: str, comment: str = ""):
    """Validate token and process approval/rejection from email without login."""
    # Get client IP address
    ip_address = request.META.get("HTTP_X_FORWARDED_FOR")
    if ip_address:
        ip_address = ip_address.split(",")[0].strip()
    else:
        ip_address = request.META.get("REMOTE_ADDR")

    result = process_email_approval(token, comment, ip_address)
    if result["status"] == "error":
        raise HttpError(400, result["message"])

    return {"detail": result["message"]}
