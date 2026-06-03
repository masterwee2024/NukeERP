"""Email service — SMTP configuration and email sending."""

from smtplib import SMTPException

from django.core.mail import send_mail as django_send_mail

from apps.core.models import EmailSetting


def apply_smtp_settings():
    """Apply stored SMTP settings to Django's email config at runtime."""
    cfg = EmailSetting.load()
    if not cfg.smtp_host:
        return

    from django.conf import settings

    settings.EMAIL_HOST = cfg.smtp_host
    settings.EMAIL_PORT = cfg.smtp_port
    settings.EMAIL_HOST_USER = cfg.smtp_username
    settings.EMAIL_HOST_PASSWORD = cfg.get_decrypted_password()
    settings.EMAIL_USE_TLS = cfg.smtp_use_tls
    settings.EMAIL_USE_SSL = cfg.smtp_use_ssl
    if cfg.from_email:
        settings.DEFAULT_FROM_EMAIL = cfg.from_email


def get_email_config() -> dict:
    """Return current SMTP config for display (password masked)."""
    cfg = EmailSetting.load()
    return {
        "smtp_host": cfg.smtp_host,
        "smtp_port": cfg.smtp_port,
        "smtp_username": cfg.smtp_username,
        "smtp_password": "••••••" if cfg.smtp_password else "",
        "smtp_use_tls": cfg.smtp_use_tls,
        "smtp_use_ssl": cfg.smtp_use_ssl,
        "from_email": cfg.from_email,
        "from_name": cfg.from_name,
    }


def update_email_config(data: dict) -> dict:
    """Update SMTP config with provided data."""
    cfg = EmailSetting.load()
    allowed = [
        "smtp_host",
        "smtp_port",
        "smtp_username",
        "smtp_use_tls",
        "smtp_use_ssl",
        "from_email",
        "from_name",
    ]
    for key in allowed:
        if key in data:
            setattr(cfg, key, data[key])
    if (
        "smtp_password" in data
        and data["smtp_password"]
        and data["smtp_password"] != "••••••"
    ):
        cfg.smtp_password = data["smtp_password"]
    cfg.save()
    apply_smtp_settings()
    return get_email_config()


def send_test_email(recipient: str) -> str:
    """Send a test email to verify SMTP configuration."""
    apply_smtp_settings()
    cfg = EmailSetting.load()
    from_name = cfg.from_name or "pyERP"
    from_email = cfg.from_email or "noreply@pyerp.local"
    subject = f"[{from_name}] Test Email"
    message = (
        f"This is a test email from {from_name}.\n\n"
        f"If you received this, your SMTP settings are configured correctly.\n\n"
        f"SMTP Host: {cfg.smtp_host}:{cfg.smtp_port}\n"
        f"From: {from_email}"
    )
    try:
        django_send_mail(subject, message, from_email, [recipient], fail_silently=False)
        return "Test email sent successfully"
    except SMTPException as e:
        raise RuntimeError(f"Failed to send test email: {e}") from e
