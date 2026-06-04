"""Push service — handles PWA Web Push subscriptions and payload delivery."""

import json
import logging

from django.conf import settings
from pywebpush import WebPushException, webpush

from apps.core.models import PushSubscription, User

logger = logging.getLogger(__name__)


def subscribe_push(
    user: User, endpoint: str, p256dh: str, auth: str, user_agent: str = ""
) -> PushSubscription:
    """Save or update a Web Push subscription for a user."""
    subscription, created = PushSubscription.objects.update_or_create(
        user=user,
        endpoint=endpoint,
        defaults={
            "p256dh": p256dh,
            "auth": auth,
            "user_agent": user_agent or "",
            "is_active": True,
        },
    )
    return subscription


def unsubscribe_push(user: User):
    """Deactivate all active push subscriptions for a user."""
    PushSubscription.objects.filter(user=user, is_active=True).update(is_active=False)


def send_push(user: User, title: str, message: str, link: str = "") -> bool:
    """Send a push notification to all active devices of a user."""
    subscriptions = PushSubscription.objects.filter(user=user, is_active=True)
    if not subscriptions.exists():
        return False

    vapid_private = getattr(settings, "VAPID_PRIVATE_KEY", None)
    vapid_public = getattr(settings, "VAPID_PUBLIC_KEY", None)
    vapid_claims = getattr(
        settings, "VAPID_CLAIMS", {"sub": "mailto:admin@pyerp.local"}
    )

    # If VAPID keys are not configured, simulate/log sending and exit
    if not vapid_private or not vapid_public:
        logger.warning(
            f"VAPID keys not configured. Simulating Push to user {user.email}: "
            f"Title='{title}', Message='{message}', Link='{link}'"
        )
        return True

    payload = json.dumps(
        {"notification": {"title": title, "body": message, "data": {"url": link}}}
    )

    success = False
    for sub in subscriptions:
        try:
            webpush(
                subscription_info={
                    "endpoint": sub.endpoint,
                    "keys": {"p256dh": sub.p256dh, "auth": sub.auth},
                },
                data=payload,
                vapid_private_key=vapid_private,
                vapid_claims=vapid_claims,
            )
            success = True
        except WebPushException as ex:
            logger.error(f"Failed to send Web Push: {ex}")
            # If the endpoint is expired/gone (410 Gone / 404 Not Found), deactivate subscription
            if ex.response is not None and ex.response.status_code in [404, 410]:
                sub.is_active = False
                sub.save()
        except Exception as ex:
            logger.error(f"Unexpected error in push: {ex}")

    return success
