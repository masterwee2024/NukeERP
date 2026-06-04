"""Celery tasks for async email dispatch, PWA push notifications, and token cleanup."""

import logging

from celery import shared_task
from django.core.mail import send_mail
from django.utils import timezone

from apps.core.models import (
    ApprovalToken,
    EmailSetting,
    Notification,
    User,
    WorkflowExecution,
)
from apps.core.services.email_approval_service import send_approval_email_notification
from apps.core.services.email_service import apply_smtp_settings
from apps.core.services.push_service import send_push

logger = logging.getLogger(__name__)


@shared_task
def send_notification_email(notification_id: str):
    """Fetch notification, render email content, and dispatch via SMTP."""
    try:
        notification = Notification.objects.select_related("recipient").get(
            id=notification_id
        )
    except Notification.DoesNotExist:
        logger.error(f"Notification {notification_id} not found for email dispatch.")
        return

    recipient = notification.recipient
    if not recipient.email or not recipient.is_active:
        return

    # Load SMTP settings and apply
    apply_smtp_settings()
    cfg = EmailSetting.load()
    from_email = cfg.from_email or "noreply@pyerp.local"
    from_name = cfg.from_name or "pyERP"

    subject = f"[{from_name}] {notification.title}"
    body = (
        f"Hello {recipient.full_name or recipient.email},\n\n"
        f"{notification.message}\n\n"
        f"View details: {notification.link}\n\n"
        f"Best regards,\n"
        f"{from_name} Team"
    )

    try:
        send_mail(
            subject,
            body,
            f"{from_name} <{from_email}>",
            [recipient.email],
            fail_silently=False,
        )
    except Exception as ex:
        logger.error(f"Failed to send email notification: {ex}")


@shared_task
def send_push_notification(user_id: str, title: str, message: str, link: str = ""):
    """Trigger Web Push notification to user's registered devices."""
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        logger.error(f"User {user_id} not found for push notification.")
        return

    send_push(user, title, message, link)


@shared_task
def send_approval_email(execution_id: str, approver_id: str):
    """Generate tokens and email for one-click approval."""
    try:
        execution = WorkflowExecution.objects.get(id=execution_id)
        approver = User.objects.get(id=approver_id)
    except (WorkflowExecution.DoesNotExist, User.DoesNotExist) as ex:
        logger.error(f"Workflow execution or approver not found: {ex}")
        return

    send_approval_email_notification(execution, approver)


@shared_task
def cleanup_expired_tokens():
    """Daily job to delete expired approval tokens."""
    deleted_count, _ = ApprovalToken.objects.filter(
        expires_at__lt=timezone.now()
    ).delete()
    logger.info(f"Cleaned up {deleted_count} expired approval tokens.")


@shared_task
def archive_audit_logs():
    """Monthly job to archive audit logs older than the retention period."""
    from apps.core.services.advanced_audit_service import archive_old_logs

    result = archive_old_logs()
    logger.info(
        "Archived %d audit logs across %d companies",
        result["deleted_count"],
        result["companies_processed"],
    )
