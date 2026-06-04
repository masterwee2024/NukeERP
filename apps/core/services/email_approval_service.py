"""Email approval service — handles secure token generation, email alerts, and action processing."""

import secrets
from datetime import timedelta

from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

from apps.core.models import ApprovalToken, EmailSetting, User, WorkflowExecution
from apps.core.services.email_service import apply_smtp_settings
from apps.core.services.workflow_service import process_action


def generate_approval_token(
    execution: WorkflowExecution, user: User, action: str
) -> str:
    """Generate a secure, single-use approval token valid for 7 days."""
    token_str = secrets.token_urlsafe(32)
    ApprovalToken.objects.create(
        execution=execution,
        user=user,
        token=token_str,
        action=action,
        expires_at=timezone.now() + timedelta(days=7),
        company=execution.company,
    )
    return token_str


def send_approval_email_notification(execution: WorkflowExecution, approver: User):
    """Generate approve/reject tokens, build links, and dispatch the alert email."""
    # Apply SMTP settings from configuration
    apply_smtp_settings()
    cfg = EmailSetting.load()

    from_email = cfg.from_email or "noreply@pyerp.local"
    from_name = cfg.from_name or "pyERP"

    approve_token = generate_approval_token(execution, approver, "approve")
    reject_token = generate_approval_token(execution, approver, "reject")

    frontend_url = getattr(settings, "FRONTEND_URL", "http://localhost:5173")
    approve_url = (
        f"{frontend_url}/app/approvals/execute?token={approve_token}&action=approve"
    )
    reject_url = (
        f"{frontend_url}/app/approvals/execute?token={reject_token}&action=reject"
    )

    subject = f"[{from_name}] Approval Required: {execution.document_type} #{execution.document_id}"
    message = (
        f"Hello {approver.full_name or approver.email},\n\n"
        f"An approval request has been submitted for {execution.document_type} "
        f"#{execution.document_id} by {execution.requester.full_name or execution.requester.email}.\n\n"
        f"You can approve or reject this document using the quick links below:\n\n"
        f"Approve: {approve_url}\n"
        f"Reject: {reject_url}\n\n"
        f"Note: These links are secure, single-use, and valid for 7 days. They do not require logging in.\n\n"
        f"Best regards,\n"
        f"{from_name} Team"
    )

    send_mail(
        subject,
        message,
        f"{from_name} <{from_email}>",
        [approver.email],
        fail_silently=False,
    )


def process_email_approval(
    token_str: str, comment: str = "", ip_address: str = None
) -> dict:
    """Validate secure token, process workflow action, and mark token as used."""
    try:
        token = ApprovalToken.objects.get(token=token_str)
    except ApprovalToken.DoesNotExist:
        return {"status": "error", "message": "Invalid token"}

    if token.is_used:
        return {"status": "error", "message": "Token has already been used"}

    if token.expires_at < timezone.now():
        return {"status": "error", "message": "Token has expired"}

    # Process the workflow action
    try:
        result = process_action(
            execution_id=token.execution.id,
            approver=token.user,
            action=token.action,
            comment=comment or f"Processed via email link ({token.action})",
            ip_address=ip_address,
        )
    except PermissionError as ex:
        return {"status": "error", "message": str(ex)}
    except Exception as ex:
        return {"status": "error", "message": f"Action failed: {ex}"}

    # Mark token as used
    token.is_used = True
    token.used_at = timezone.now()
    token.save()

    return {
        "status": "success",
        "message": result.get("message", "Action processed successfully"),
    }
