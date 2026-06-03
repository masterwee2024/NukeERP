"""Tests for Document Attachment service and API (T009a)."""

import uuid

import pytest
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework_simplejwt.tokens import AccessToken

from apps.core.models import Attachment, Company, Menu

User = get_user_model()


# --- Fixtures ---


@pytest.fixture
def test_user(db):
    return User.objects.create_user(
        email="user@example.com",
        password="testpass123",
        first_name="Test",
        last_name="User",
    )


@pytest.fixture
def auth_client(client, test_user):
    """Client authenticated via JWT Bearer token."""
    token = AccessToken.for_user(test_user)
    client.defaults["HTTP_AUTHORIZATION"] = f"Bearer {token}"
    return client


@pytest.fixture
def test_company(db):
    return Company.objects.create(name="Test Co", code="TST")


@pytest.fixture
def test_menu(db):
    return Menu.objects.create(name="Test Menu", slug="test-menu", module="test")


@pytest.fixture
def pdf_file():
    return SimpleUploadedFile(
        "test_document.pdf",
        b"%PDF-1.4 fake pdf content for testing",
        content_type="application/pdf",
    )


@pytest.fixture
def large_file():
    return SimpleUploadedFile(
        "large_file.pdf",
        b"x" * (11 * 1024 * 1024),  # 11 MB
        content_type="application/pdf",
    )


@pytest.fixture
def invalid_file():
    return SimpleUploadedFile(
        "script.exe",
        b"fake exe content",
        content_type="application/x-msdownload",
    )


@pytest.fixture
def jpg_file():
    return SimpleUploadedFile(
        "photo.jpg",
        b"\xff\xd8\xff\xe0 fake jpeg data",
        content_type="image/jpeg",
    )


# --- Model Tests ---


@pytest.mark.django_db
class TestAttachmentModel:
    def test_create_attachment(self, test_user, test_company, pdf_file):
        ct = ContentType.objects.get_for_model(Company)
        attachment = Attachment.objects.create(
            content_type=ct,
            object_id=test_company.id,
            file=pdf_file,
            file_name=pdf_file.name,
            file_size=pdf_file.size,
            mime_type="application/pdf",
            uploaded_by=test_user,
        )
        assert attachment.file_name == "test_document.pdf"
        assert attachment.file_size > 0
        assert attachment.mime_type == "application/pdf"
        assert attachment.uploaded_by == test_user
        assert attachment.is_active is True
        assert str(attachment) == "test_document.pdf"
        assert attachment.content_object == test_company

    def test_soft_delete(self, test_company, pdf_file):
        ct = ContentType.objects.get_for_model(Company)
        attachment = Attachment.objects.create(
            content_type=ct,
            object_id=test_company.id,
            file=pdf_file,
            file_name=pdf_file.name,
            file_size=pdf_file.size,
        )
        assert attachment.is_active is True

        attachment.is_active = False
        attachment.save()
        attachment.refresh_from_db()
        assert attachment.is_active is False

    def test_content_type_filter(self, test_company, test_menu, pdf_file):
        ct_company = ContentType.objects.get_for_model(Company)
        ct_menu = ContentType.objects.get_for_model(Menu)

        Attachment.objects.create(
            content_type=ct_company,
            object_id=test_company.id,
            file=pdf_file,
            file_name="company_file.pdf",
            file_size=pdf_file.size,
        )
        Attachment.objects.create(
            content_type=ct_menu,
            object_id=test_menu.id,
            file=pdf_file,
            file_name="menu_file.pdf",
            file_size=pdf_file.size,
        )

        company_attachments = Attachment.objects.filter(
            content_type=ct_company, object_id=test_company.id, is_active=True
        )
        assert company_attachments.count() == 1
        assert company_attachments.first().file_name == "company_file.pdf"

    def test_generic_fk_relation(self, test_company, pdf_file):
        ct = ContentType.objects.get_for_model(Company)
        attachment = Attachment.objects.create(
            content_type=ct,
            object_id=test_company.id,
            file=pdf_file,
            file_name="test.pdf",
            file_size=pdf_file.size,
        )
        assert attachment.content_object == test_company


# --- Service Tests ---


@pytest.mark.django_db
class TestAttachmentService:
    def test_upload_attachment(self, test_user, pdf_file):
        from apps.core.services.attachment_service import upload_attachment

        attachment = upload_attachment(
            content_type_label="core.company",
            object_id=str(uuid.uuid4()),
            file=pdf_file,
            user=test_user,
            description="Test upload",
        )
        assert attachment.file_name == "test_document.pdf"
        assert attachment.description == "Test upload"
        assert attachment.uploaded_by == test_user
        assert attachment.is_active is True

    def test_upload_invalid_file_type(self, test_user, invalid_file):
        from apps.core.services.attachment_service import upload_attachment

        with pytest.raises(ValueError, match="File type '.exe' is not allowed"):
            upload_attachment(
                content_type_label="core.company",
                object_id=str(uuid.uuid4()),
                file=invalid_file,
                user=test_user,
            )

    def test_upload_file_too_large(self, test_user, large_file):
        from apps.core.services.attachment_service import upload_attachment

        with pytest.raises(ValueError, match="File size exceeds 10 MB"):
            upload_attachment(
                content_type_label="core.company",
                object_id=str(uuid.uuid4()),
                file=large_file,
                user=test_user,
            )

    def test_upload_invalid_content_type(self, test_user, pdf_file):
        from apps.core.services.attachment_service import upload_attachment

        with pytest.raises(ValueError, match="Invalid content type"):
            upload_attachment(
                content_type_label="core.nonexistent",
                object_id=str(uuid.uuid4()),
                file=pdf_file,
                user=test_user,
            )

    def test_get_attachments(self, test_company, pdf_file, jpg_file):
        from apps.core.services.attachment_service import (
            get_attachments,
        )

        ct = ContentType.objects.get_for_model(Company)
        for f in [pdf_file, jpg_file]:
            Attachment.objects.create(
                content_type=ct,
                object_id=test_company.id,
                file=f,
                file_name=f.name,
                file_size=f.size,
                mime_type=f.content_type,
            )

        attachments = get_attachments("core.company", str(test_company.id))
        assert len(attachments) == 2

    def test_get_attachments_excludes_inactive(self, test_company, pdf_file):
        from apps.core.services.attachment_service import (
            get_attachments,
        )

        ct = ContentType.objects.get_for_model(Company)
        a1 = Attachment.objects.create(
            content_type=ct,
            object_id=test_company.id,
            file=pdf_file,
            file_name="active.pdf",
            file_size=pdf_file.size,
            is_active=True,
        )
        Attachment.objects.create(
            content_type=ct,
            object_id=test_company.id,
            file=pdf_file,
            file_name="inactive.pdf",
            file_size=pdf_file.size,
            is_active=False,
        )

        attachments = get_attachments("core.company", str(test_company.id))
        assert len(attachments) == 1
        assert attachments[0].id == a1.id

    def test_soft_delete_attachment(self, test_company, pdf_file):
        from apps.core.services.attachment_service import (
            soft_delete_attachment,
        )

        ct = ContentType.objects.get_for_model(Company)
        attachment = Attachment.objects.create(
            content_type=ct,
            object_id=test_company.id,
            file=pdf_file,
            file_name="to_delete.pdf",
            file_size=pdf_file.size,
        )

        result = soft_delete_attachment(str(attachment.id))
        assert result is not None
        assert result.is_active is False

        attachment.refresh_from_db()
        assert attachment.is_active is False

    def test_soft_delete_nonexistent(self):
        from apps.core.services.attachment_service import soft_delete_attachment

        result = soft_delete_attachment(str(uuid.uuid4()))
        assert result is None

    def test_download_attachment(self, test_company, pdf_file):
        from apps.core.services.attachment_service import download_attachment

        ct = ContentType.objects.get_for_model(Company)
        attachment = Attachment.objects.create(
            content_type=ct,
            object_id=test_company.id,
            file=pdf_file,
            file_name="download_test.pdf",
            file_size=pdf_file.size,
        )

        result = download_attachment(str(attachment.id))
        assert result is not None
        assert result.file_name == "download_test.pdf"

    def test_download_inactive_returns_none(self, test_company, pdf_file):
        from apps.core.services.attachment_service import download_attachment

        ct = ContentType.objects.get_for_model(Company)
        attachment = Attachment.objects.create(
            content_type=ct,
            object_id=test_company.id,
            file=pdf_file,
            file_name="inactive.pdf",
            file_size=pdf_file.size,
            is_active=False,
        )

        result = download_attachment(str(attachment.id))
        assert result is None


# --- API Tests ---


@pytest.mark.django_db
class TestAttachmentAPI:
    def test_upload_attachment(self, auth_client, test_company, pdf_file):
        response = auth_client.post(
            "/api/v1/core/attachments/upload/",
            {
                "file": pdf_file,
                "content_type_label": "core.company",
                "object_id": str(test_company.id),
                "description": "Test upload via API",
            },
            format="multipart",
        )
        assert response.status_code == 200, response.content
        data = response.json()
        assert data["file_name"] == "test_document.pdf"
        assert data["description"] == "Test upload via API"
        assert data["uploaded_by_name"] == "Test User"
        assert data["mime_type"] == "application/pdf"
        assert "download_url" in data

    def test_upload_without_file(self, auth_client):
        response = auth_client.post(
            "/api/v1/core/attachments/upload/",
            {
                "content_type_label": "core.company",
                "object_id": str(uuid.uuid4()),
            },
            format="multipart",
        )
        assert response.status_code == 400
        assert "No file provided" in response.json()["detail"]

    def test_upload_without_content_type(self, auth_client, pdf_file):
        response = auth_client.post(
            "/api/v1/core/attachments/upload/",
            {
                "file": pdf_file,
                "object_id": str(uuid.uuid4()),
            },
            format="multipart",
        )
        assert response.status_code == 400

    def test_upload_invalid_content_type(self, auth_client, pdf_file):
        response = auth_client.post(
            "/api/v1/core/attachments/upload/",
            {
                "file": pdf_file,
                "content_type_label": "core.nonexistent",
                "object_id": str(uuid.uuid4()),
            },
            format="multipart",
        )
        assert response.status_code == 400

    def test_list_attachments(self, auth_client, test_company, pdf_file, jpg_file):
        ct = ContentType.objects.get_for_model(Company)
        for f in [pdf_file, jpg_file]:
            Attachment.objects.create(
                content_type=ct,
                object_id=test_company.id,
                file=f,
                file_name=f.name,
                file_size=f.size,
                mime_type=f.content_type,
                uploaded_by=auth_client.defaults.get("user"),
            )

        response = auth_client.get(
            f"/api/v1/core/attachments/list/core.company/{test_company.id}/"
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        file_names = {a["file_name"] for a in data}
        assert "test_document.pdf" in file_names
        assert "photo.jpg" in file_names

    def test_list_attachments_empty(self, auth_client, test_company):
        response = auth_client.get(
            f"/api/v1/core/attachments/list/core.company/{test_company.id}/"
        )
        assert response.status_code == 200
        assert response.json() == []

    def test_download_attachment(self, auth_client, test_company, pdf_file):
        ct = ContentType.objects.get_for_model(Company)
        attachment = Attachment.objects.create(
            content_type=ct,
            object_id=test_company.id,
            file=pdf_file,
            file_name="downloadable.pdf",
            file_size=pdf_file.size,
            mime_type="application/pdf",
        )

        response = auth_client.get(
            f"/api/v1/core/attachments/download/{attachment.id}/"
        )
        assert response.status_code == 200, response.content
        assert response["Content-Type"] == "application/pdf"
        assert (
            'attachment; filename="downloadable.pdf"' in response["Content-Disposition"]
        )

    def test_download_nonexistent(self, auth_client):
        response = auth_client.get(f"/api/v1/core/attachments/download/{uuid.uuid4()}/")
        assert response.status_code == 404, response.content

    def test_delete_attachment(self, auth_client, test_company, pdf_file):
        ct = ContentType.objects.get_for_model(Company)
        attachment = Attachment.objects.create(
            content_type=ct,
            object_id=test_company.id,
            file=pdf_file,
            file_name="to_delete.pdf",
            file_size=pdf_file.size,
        )

        response = auth_client.delete(f"/api/v1/core/attachments/{attachment.id}/")
        assert response.status_code == 200
        assert response.json()["success"] is True

        attachment.refresh_from_db()
        assert attachment.is_active is False

    def test_delete_nonexistent(self, auth_client):
        response = auth_client.delete(f"/api/v1/core/attachments/{uuid.uuid4()}/")
        assert response.status_code == 404

    def test_unauthorized_access(self, client, test_company):
        """Requests without JWT token should be rejected."""
        response = client.get(
            f"/api/v1/core/attachments/list/core.company/{test_company.id}/"
        )
        assert response.status_code == 401
