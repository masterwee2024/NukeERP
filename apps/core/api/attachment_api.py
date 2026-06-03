"""Attachment API — upload, list, download, delete file attachments."""

from uuid import UUID

from django.http import FileResponse
from ninja import Router, Schema
from ninja.errors import HttpError

from apps.core.api.auth import JWTAuth
from apps.core.services.attachment_service import (
    download_attachment,
    get_attachments,
    soft_delete_attachment,
    upload_attachment,
)

router = Router(auth=JWTAuth())


class AttachmentOut(Schema):
    id: str
    file_name: str
    file_size: int
    mime_type: str = ""
    description: str = ""
    uploaded_by_name: str = ""
    uploaded_by_id: str = ""
    created_at: str = ""
    download_url: str = ""

    @staticmethod
    def resolve_id(obj):
        return str(obj.id)

    @staticmethod
    def resolve_uploaded_by_name(obj):
        return obj.uploaded_by.full_name if obj.uploaded_by else ""

    @staticmethod
    def resolve_uploaded_by_id(obj):
        return str(obj.uploaded_by.id) if obj.uploaded_by else ""

    @staticmethod
    def resolve_created_at(obj):
        return obj.created_at.isoformat() if obj.created_at else ""

    @staticmethod
    def resolve_download_url(obj):
        return f"/api/v1/core/attachments/download/{obj.id}/"


@router.post("/upload/", response=AttachmentOut)
def upload(request):
    """Upload a file attachment. Expects multipart/form-data with:
    - file: the file to upload
    - content_type_label: "app_label.model_name" (e.g. "core.user")
    - object_id: UUID of the target record
    - description: optional description string
    """
    if "file" not in request.FILES:
        raise HttpError(400, "No file provided")

    file = request.FILES["file"]
    content_type_label = request.POST.get("content_type_label", "")
    object_id = request.POST.get("object_id", "")
    description = request.POST.get("description", "")

    if not content_type_label:
        raise HttpError(400, "content_type_label is required")
    if not object_id:
        raise HttpError(400, "object_id is required")

    try:
        attachment = upload_attachment(
            content_type_label=content_type_label,
            object_id=object_id,
            file=file,
            user=request.auth,
            description=description,
        )
    except ValueError as e:
        raise HttpError(400, str(e)) from e

    return attachment


@router.get("/list/{content_type_label}/{object_id}/", response=list[AttachmentOut])
def list_attachments(request, content_type_label: str, object_id: str):
    """List all active attachments for a given record."""
    try:
        attachments = get_attachments(
            content_type_label=content_type_label,
            object_id=object_id,
        )
    except ValueError as e:
        raise HttpError(400, str(e)) from e
    return attachments


@router.get("/download/{id}/")
def download(request, id: UUID):
    """Download an attachment file."""
    attachment = download_attachment(str(id))
    if attachment is None:
        raise HttpError(404, "Attachment not found")

    file_handle = attachment.file.open("rb")
    response = FileResponse(
        file_handle, content_type=attachment.mime_type or "application/octet-stream"
    )
    response["Content-Disposition"] = f'attachment; filename="{attachment.file_name}"'
    response["Content-Length"] = attachment.file_size
    return response


@router.delete("/{id}/")
def delete(request, id: UUID):
    """Soft delete an attachment."""
    attachment = soft_delete_attachment(str(id))
    if attachment is None:
        raise HttpError(404, "Attachment not found")
    return {"success": True}
