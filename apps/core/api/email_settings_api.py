"""Email settings API — SMTP configuration endpoints."""

from ninja import Router, Schema
from ninja.errors import HttpError

from apps.core.services import email_service

router = Router()


class EmailConfigOut(Schema):
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_use_tls: bool = True
    smtp_use_ssl: bool = False
    from_email: str = ""
    from_name: str = ""


class EmailConfigUpdate(Schema):
    smtp_host: str | None = None
    smtp_port: int | None = None
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_use_tls: bool | None = None
    smtp_use_ssl: bool | None = None
    from_email: str | None = None
    from_name: str | None = None


class TestEmailSchema(Schema):
    recipient: str


@router.get("/settings/email/", response=EmailConfigOut)
def get_email_settings(request):
    """Get current SMTP configuration."""
    if not request.auth.is_superuser:
        raise HttpError(403, "Access denied")
    return email_service.get_email_config()


@router.put("/settings/email/", response=EmailConfigOut)
def update_email_settings(request, data: EmailConfigUpdate):
    """Update SMTP configuration."""
    if not request.auth.is_superuser:
        raise HttpError(403, "Access denied")
    return email_service.update_email_config(data.model_dump(exclude_unset=True))


@router.post("/settings/email/test/")
def test_email_settings(request, data: TestEmailSchema):
    """Send a test email to verify SMTP configuration."""
    if not request.auth.is_superuser:
        raise HttpError(403, "Access denied")
    try:
        msg = email_service.send_test_email(data.recipient)
        return {"detail": msg}
    except RuntimeError as e:
        raise HttpError(400, str(e)) from e
