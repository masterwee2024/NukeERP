"""Notification service — handles in-app notification creation, read status, and WebSocket delivery."""

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.utils import timezone

from apps.core.models import Notification, NotificationType, User


def send_notification(
    recipient: User, slug: str, title: str, message: str, link: str = "", company=None
) -> Notification:
    """Create a notification, broadcast it via WebSockets, and trigger async delivery (email/push)."""
    # Fetch or create the notification type slug
    notif_type, _ = NotificationType.objects.get_or_create(
        slug=slug, defaults={"name": slug.replace("_", " ").title(), "is_active": True}
    )

    # Create the notification object
    notification = Notification.objects.create(
        notification_type=notif_type,
        recipient=recipient,
        title=title,
        message=message,
        link=link or "",
        company=company or (getattr(recipient, "current_company", None)),
    )

    # Broadcast via Channels
    channel_layer = get_channel_layer()
    if channel_layer:
        try:
            async_to_sync(channel_layer.group_send)(
                f"notifications_{recipient.id}",
                {
                    "type": "notification_message",
                    "notification": {
                        "id": str(notification.id),
                        "title": notification.title,
                        "message": notification.message,
                        "link": notification.link,
                        "is_read": notification.is_read,
                        "created_at": notification.created_at.isoformat(),
                    },
                },
            )
        except Exception:
            pass  # Fail gracefully if Channel Layer is not running (e.g. in test env)

    # Queue async tasks (Imported inline to avoid circular dependencies)
    from apps.core.tasks import send_notification_email, send_push_notification

    if recipient.email:
        send_notification_email.delay(notification.id)

    # Push notifications if subscriptions exist
    if recipient.push_subscriptions.filter(is_active=True).exists():
        send_push_notification.delay(recipient.id, title, message, link)

    return notification


def mark_as_read(notification_id: str, user: User) -> Notification:
    """Mark a specific notification as read."""
    notification = Notification.objects.get(id=notification_id, recipient=user)
    if not notification.is_read:
        notification.is_read = True
        notification.read_at = timezone.now()
        notification.save()
        _send_unread_count_update(user)
    return notification


def mark_all_as_read(user: User):
    """Mark all unread notifications of a user as read."""
    Notification.objects.filter(recipient=user, is_read=False).update(
        is_read=True, read_at=timezone.now()
    )
    _send_unread_count_update(user)


def get_unread_count(user: User) -> int:
    """Return the unread notification count for a user."""
    return Notification.objects.filter(recipient=user, is_read=False).count()


def _send_unread_count_update(user: User):
    """Broadcast updated unread count to user WebSocket."""
    channel_layer = get_channel_layer()
    if channel_layer:
        try:
            count = get_unread_count(user)
            async_to_sync(channel_layer.group_send)(
                f"notifications_{user.id}",
                {"type": "unread_count_update", "unread_count": count},
            )
        except Exception:
            pass
