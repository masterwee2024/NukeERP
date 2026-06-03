"""Attachment service — business logic for file attachments."""

import mimetypes
import os

from django.contrib.contenttypes.models import ContentType
from django.db import transaction

from apps.core.models import Attachment, User

ALLOWED_EXTENSIONS = {"pdf", "jpg", "jpeg", "png", "gif", "doc", "docx", "xls", "xlsx"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


def validate_file(file) -> None:
    """Validate file type and size. Raises ValueError on failure."""
    ext = os.path.splitext(file.name)[1].lower().lstrip(".")
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(
            f"File type '.{ext}' is not allowed. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
        )
    if file.size > MAX_FILE_SIZE:
        raise ValueError(
            f"File size exceeds 10 MB limit ({file.size / 1024 / 1024:.1f} MB)"
        )


def get_content_type(app_label: str, model_name: str) -> ContentType:
    """Resolve content type from app_label and model_name."""
    try:
        return ContentType.objects.get(app_label=app_label, model=model_name)
    except ContentType.DoesNotExist as e:
        raise ValueError(f"Invalid content type: {app_label}.{model_name}") from e


@transaction.atomic
def upload_attachment(
    content_type_label: str,
    object_id: str,
    file,
    user: User | None = None,
    description: str = "",
) -> Attachment:
    """Upload a file and link it to any record.

    Args:
        content_type_label: "app_label.model_name" format (e.g. "core.user")
        object_id: UUID of the target record
        file: Uploaded file object (must have .name, .size, .read())
        user: Uploading user (optional)
        description: Optional description

    Returns:
        The created Attachment instance.
    """
    validate_file(file)

    parts = content_type_label.split(".", 1)
    if len(parts) != 2:
        raise ValueError("content_type_label must be in 'app_label.model_name' format")
    app_label, model_name = parts
    ct = get_content_type(app_label, model_name)

    mime_type, _ = mimetypes.guess_type(file.name)
    mime_type = mime_type or "application/octet-stream"

    attachment = Attachment.objects.create(
        content_type=ct,
        object_id=object_id,
        file=file,
        file_name=file.name,
        file_size=file.size,
        mime_type=mime_type,
        description=description,
        uploaded_by=user,
    )
    return attachment


def get_attachments(content_type_label: str, object_id: str) -> list[Attachment]:
    """List active attachments for a record."""
    parts = content_type_label.split(".", 1)
    if len(parts) != 2:
        raise ValueError("content_type_label must be in 'app_label.model_name' format")
    app_label, model_name = parts
    ct = get_content_type(app_label, model_name)
    return list(
        Attachment.objects.filter(
            content_type=ct, object_id=object_id, is_active=True
        ).select_related("uploaded_by")
    )


def soft_delete_attachment(attachment_id: str) -> Attachment | None:
    """Soft delete an attachment (set is_active=False)."""
    try:
        attachment = Attachment.objects.get(id=attachment_id, is_active=True)
    except Attachment.DoesNotExist:
        return None
    attachment.is_active = False
    attachment.save(update_fields=["is_active", "updated_at", "version"])
    return attachment


def download_attachment(attachment_id: str) -> Attachment | None:
    """Get attachment for download (returns None if not found or inactive)."""
    try:
        return Attachment.objects.get(id=attachment_id, is_active=True)
    except Attachment.DoesNotExist:
        return None
