"""Tests for the Data Migration Framework (T009d)."""

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.core.models import ImportHistory, ImportJob, ImportRow, ImportTemplate, User
from apps.core.services import import_service
from apps.core.services.column_mapper import (
    apply_mapping,
    auto_detect_columns,
    manual_map,
)
from apps.core.services.validation_engine import validate_row

# ── Fixtures ─────────────────────────────────────────────────────


@pytest.fixture
def db():
    pass


@pytest.fixture
def admin_user(db):
    return User.objects.create_superuser(
        email="admin@example.com",
        password="adminpass123",
        first_name="Admin",
        last_name="User",
    )


@pytest.fixture
def items_template(db):
    return ImportTemplate.objects.create(
        name="Items",
        entity_type="items",
        description="Import items from CSV",
        column_definitions=[
            {
                "name": "code",
                "label": "Code",
                "type": "string",
                "rules": {"required": True, "max_length": 50},
            },
            {
                "name": "name",
                "label": "Name",
                "type": "string",
                "rules": {"required": True, "max_length": 200},
            },
            {
                "name": "selling_price",
                "label": "Selling Price",
                "type": "number",
                "rules": {},
            },
            {
                "name": "reorder_level",
                "label": "Reorder Level",
                "type": "integer",
                "rules": {},
            },
        ],
    )


@pytest.fixture
def unmapped_template(db):
    """Template with entity_type NOT in `_resolve_model_name` mapping (for roundtrip tests)."""
    return ImportTemplate.objects.create(
        name="Custom Import",
        entity_type="custom-import",
        description="A template with no backend model mapping",
        column_definitions=[
            {
                "name": "code",
                "label": "Code",
                "type": "string",
                "rules": {"required": True},
            },
            {
                "name": "name",
                "label": "Name",
                "type": "string",
                "rules": {"required": True},
            },
        ],
    )


@pytest.fixture
def auth_client(client, admin_user):
    from rest_framework_simplejwt.tokens import AccessToken

    token = AccessToken.for_user(admin_user)
    client.defaults["HTTP_AUTHORIZATION"] = f"Bearer {token}"
    return client


# ── Model Tests ──────────────────────────────────────────────────


@pytest.mark.django_db
class TestImportTemplateModel:
    def test_create_template(self, items_template):
        assert items_template.name == "Items"
        assert items_template.entity_type == "items"
        assert len(items_template.column_definitions) == 4
        assert str(items_template) == "Items"

    def test_template_unique_entity_type(self, db):
        ImportTemplate.objects.create(entity_type="test", name="Test")
        with pytest.raises(Exception, match="duplicate key|UNIQUE|already exists"):
            ImportTemplate.objects.create(entity_type="test", name="Duplicate")


@pytest.mark.django_db
class TestImportJobModel:
    def test_create_job(self, items_template, admin_user):
        job = ImportJob.objects.create(
            template=items_template,
            file_name="items.csv",
            uploaded_by=admin_user,
            status="uploaded",
        )
        assert job.status == "uploaded"
        assert str(job) == "Items — items.csv (uploaded)"

    def test_job_defaults(self, items_template):
        job = ImportJob.objects.create(template=items_template, file_name="test.csv")
        assert job.status == "uploaded"
        assert job.total_rows == 0
        assert job.success_count == 0


@pytest.mark.django_db
class TestImportRowModel:
    def test_create_row(self, items_template, admin_user):
        job = ImportJob.objects.create(
            template=items_template, file_name="test.csv", uploaded_by=admin_user
        )
        row = ImportRow.objects.create(
            job=job,
            row_number=1,
            raw_data={"code": "001", "name": "Widget"},
            mapped_data={"code": "001", "name": "Widget"},
            status="valid",
        )
        assert row.status == "valid"
        assert str(row) == "Row 1 — valid"

    def test_unique_row_number(self, items_template, admin_user):
        job = ImportJob.objects.create(
            template=items_template, file_name="test.csv", uploaded_by=admin_user
        )
        ImportRow.objects.create(job=job, row_number=1)
        with pytest.raises(Exception, match="duplicate key|UNIQUE|already exists"):
            ImportRow.objects.create(job=job, row_number=1)


@pytest.mark.django_db
class TestImportHistoryModel:
    def test_create_history(self, items_template, admin_user):
        job = ImportJob.objects.create(
            template=items_template, file_name="test.csv", uploaded_by=admin_user
        )
        history = ImportHistory.objects.create(
            job=job,
            entity_type="items",
            action="import",
            record_count=10,
            performed_by=admin_user,
        )
        assert history.action == "import"
        assert str(history) == "import — items (10 records)"


# ── Validation Engine Tests ──────────────────────────────────────


class TestValidationEngine:
    def test_required_valid(self):
        col_defs = [{"name": "code", "type": "string", "rules": {"required": True}}]
        errors = validate_row({"code": "001"}, col_defs)
        assert len(errors) == 0

    def test_required_missing(self):
        col_defs = [{"name": "code", "type": "string", "rules": {"required": True}}]
        errors = validate_row({"code": ""}, col_defs)
        assert len(errors) == 1
        assert errors[0]["field"] == "code"

    def test_number_type_valid(self):
        col_defs = [{"name": "price", "type": "number", "rules": {}}]
        assert len(validate_row({"price": "12.50"}, col_defs)) == 0
        assert len(validate_row({"price": "0"}, col_defs)) == 0

    def test_number_type_invalid(self):
        col_defs = [{"name": "price", "type": "number", "rules": {}}]
        errors = validate_row({"price": "abc"}, col_defs)
        assert len(errors) == 1

    def test_integer_type(self):
        col_defs = [{"name": "qty", "type": "integer", "rules": {}}]
        assert len(validate_row({"qty": "5"}, col_defs)) == 0
        errors = validate_row({"qty": "5.5"}, col_defs)
        assert len(errors) == 1

    def test_max_length_exceeded(self):
        col_defs = [{"name": "code", "type": "string", "rules": {"max_length": 5}}]
        errors = validate_row({"code": "toolong"}, col_defs)
        assert len(errors) == 1

    def test_max_length_ok(self):
        col_defs = [{"name": "code", "type": "string", "rules": {"max_length": 5}}]
        assert len(validate_row({"code": "ok"}, col_defs)) == 0

    def test_email_valid(self):
        col_defs = [{"name": "email", "type": "string", "rules": {"format": "email"}}]
        assert len(validate_row({"email": "test@example.com"}, col_defs)) == 0

    def test_email_invalid(self):
        col_defs = [{"name": "email", "type": "string", "rules": {"format": "email"}}]
        errors = validate_row({"email": "not-an-email"}, col_defs)
        assert len(errors) == 1

    def test_multiple_errors(self):
        col_defs = [
            {"name": "code", "type": "string", "rules": {"required": True}},
            {"name": "price", "type": "number", "rules": {"required": True}},
        ]
        errors = validate_row({"code": "", "price": "abc"}, col_defs)
        assert len(errors) == 2


# ── Column Mapper Tests ──────────────────────────────────────────


class TestColumnMapper:
    def test_auto_detect_exact_match(self):
        headers = ["Code", "Name", "Selling Price"]
        defs = [
            {"name": "code"},
            {"name": "name"},
            {"name": "selling_price"},
        ]
        mapping = auto_detect_columns(headers, defs)
        assert mapping.get("Code") == "code"
        assert mapping.get("Name") == "name"
        assert mapping.get("Selling Price") == "selling_price"

    def test_auto_detect_alias(self):
        headers = ["SKU", "Description", "Price"]
        defs = [
            {"name": "code"},
            {"name": "name"},
            {"name": "selling_price"},
        ]
        mapping = auto_detect_columns(headers, defs)
        assert mapping.get("SKU") == "code"
        assert mapping.get("Description") == "name"
        assert mapping.get("Price") == "selling_price"

    def test_apply_mapping(self):
        mapping = {"Code": "code", "Name": "name"}
        row = {"Code": "001", "Name": "Widget", "Extra": "ignored"}
        result = apply_mapping(row, mapping)
        assert result == {"code": "001", "name": "Widget"}

    def test_manual_map_valid(self):
        user_map = {"Code": "code", "Desc": "name"}
        defs = [{"name": "code"}, {"name": "name"}]
        result = manual_map(user_map, defs)
        assert result == {"Code": "code", "Desc": "name"}

    def test_manual_map_invalid(self):
        user_map = {"Code": "nonexistent_field"}
        defs = [{"name": "code"}]
        result = manual_map(user_map, defs)
        assert result == {}

    def test_auto_detect_fuzzy(self):
        headers = ["Item Code"]
        defs = [{"name": "code"}]
        mapping = auto_detect_columns(headers, defs)
        assert mapping.get("Item Code") == "code"


# ── Import Service Tests ─────────────────────────────────────────


@pytest.mark.django_db
class TestImportService:
    def test_seed_templates(self, db):
        import_service.seed_templates()
        templates = ImportTemplate.objects.all()
        assert len(templates) >= 7  # 7 predefined templates

    def test_list_templates(self, items_template):
        templates = import_service.list_templates()
        assert items_template in templates

    def test_get_template_found(self, items_template):
        t = import_service.get_template("items")
        assert t == items_template

    def test_get_template_not_found(self, db):
        assert import_service.get_template("nonexistent") is None

    def test_generate_csv_template(self, items_template):
        result = import_service.generate_csv_template("items")
        assert result is not None
        content, filename = result
        assert filename == "items_template.csv"
        assert "Code" in content
        assert "Name" in content

    def test_generate_csv_template_not_found(self, db):
        assert import_service.generate_csv_template("nonexistent") is None

    def test_parse_csv(self, db):
        csv_content = "Code,Name,Price\n001,Widget,10.00\n002,Gadget,20.00\n"
        headers, rows = import_service.parse_csv(csv_content)
        assert headers == ["Code", "Name", "Price"]
        assert len(rows) == 2
        assert rows[0]["Code"] == "001"

    def test_create_job(self, items_template, admin_user):
        job = import_service.create_job(
            template=items_template,
            file_name="test.csv",
            user=admin_user,
        )
        assert job.template == items_template
        assert job.file_name == "test.csv"
        assert job.uploaded_by == admin_user

    def test_csv_with_bom(self, items_template):
        """CSV with UTF-8 BOM should parse correctly."""
        csv_content = "\ufeffCode,Name\n001,Widget\n"
        headers, rows = import_service.parse_csv(csv_content)
        assert "Code" in headers or "\ufeffCode" in headers

    def test_process_upload(self, items_template, admin_user):
        job = import_service.create_job(
            template=items_template, file_name="test.csv", user=admin_user
        )
        csv_content = "Code,Name,Selling Price\n001,Widget,10.00\n002,Gadget,20.00\n"
        result = import_service.process_upload(job.id, csv_content)
        assert result["total_rows"] == 2
        assert ImportRow.objects.filter(job=job).count() == 2

    def test_validate_job_valid_rows(self, items_template, admin_user):
        job = import_service.create_job(
            template=items_template, file_name="test.csv", user=admin_user
        )
        csv_content = "Code,Name\n001,Widget\n002,Gadget\n"
        import_service.process_upload(job.id, csv_content)
        result = import_service.validate_job(job.id)
        assert result["valid_count"] == 2
        assert result["error_count"] == 0

    def test_validate_job_error_rows(self, items_template, admin_user):
        job = import_service.create_job(
            template=items_template, file_name="test.csv", user=admin_user
        )
        csv_content = "Code,Name\n,Widget\n003,\n"  # Missing required fields
        import_service.process_upload(job.id, csv_content)
        result = import_service.validate_job(job.id)
        assert result["error_count"] > 0

    def test_validate_and_import_roundtrip(self, unmapped_template, admin_user):
        """Full roundtrip: upload → validate → import → history."""
        job = import_service.create_job(
            template=unmapped_template, file_name="test.csv", user=admin_user
        )
        csv_content = "Code,Name\n001,Widget\n002,Gadget\n"
        import_service.process_upload(job.id, csv_content)
        import_service.validate_job(job.id)
        result = import_service.import_job(job.id, admin_user)
        assert result["success"] is True
        assert result["success_count"] == 2

        history = ImportHistory.objects.filter(job=job, action="import")
        assert history.count() == 1
        assert history.first().record_count == 2

    def test_rollback_import(self, unmapped_template, admin_user):
        """Full roundtrip: upload → validate → import → rollback."""
        job = import_service.create_job(
            template=unmapped_template, file_name="test.csv", user=admin_user
        )
        csv_content = "Code,Name\n001,Widget\n002,Gadget\n"
        import_service.process_upload(job.id, csv_content)
        import_service.validate_job(job.id)
        import_service.import_job(job.id, admin_user)

        result = import_service.rollback_job(job.id, admin_user)
        assert result["success"] is True

        job.refresh_from_db()
        assert job.status == "rolled_back"

        history = ImportHistory.objects.filter(job=job, action="rollback")
        assert history.count() == 1

    def test_get_import_history(self, items_template, admin_user):
        job = import_service.create_job(
            template=items_template, file_name="test.csv", user=admin_user
        )
        ImportHistory.objects.create(
            job=job,
            entity_type="items",
            action="import",
            record_count=5,
            performed_by=admin_user,
        )
        history = import_service.get_import_history()
        assert len(history) >= 1


# ── API Tests ────────────────────────────────────────────────────


CSV_DATA = "Code,Name,Selling Price\n001,Widget,10.00\n002,Gadget,20.00\n"


@pytest.mark.django_db
class TestImportAPI:
    def test_list_templates(self, auth_client):
        import_service.seed_templates()
        response = auth_client.get("/api/v1/core/import/templates/")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 7

    def test_get_template(self, auth_client, items_template):
        response = auth_client.get(
            f"/api/v1/core/import/templates/{items_template.entity_type}/"
        )
        assert response.status_code == 200
        assert response.json()["name"] == "Items"

    def test_get_template_not_found(self, auth_client):
        response = auth_client.get("/api/v1/core/import/templates/nonexistent/")
        assert response.status_code == 404

    def test_download_csv_template(self, auth_client, items_template):
        response = auth_client.get(
            f"/api/v1/core/import/templates/{items_template.entity_type}/csv/"
        )
        assert response.status_code == 200
        assert response["Content-Type"] == "text/csv"

    def _csv_file(self):
        return SimpleUploadedFile(
            "test.csv", CSV_DATA.encode("utf-8"), content_type="text/csv"
        )

    def test_upload_csv(self, auth_client, items_template):
        response = auth_client.post(
            "/api/v1/core/import/upload/",
            {"file": self._csv_file(), "entity_type": "items"},
            format="multipart",
        )
        assert response.status_code == 200, response.content
        data = response.json()
        assert "job_id" in data
        assert data["total_rows"] == 2

    def test_upload_csv_invalid_template(self, auth_client):
        response = auth_client.post(
            "/api/v1/core/import/upload/",
            {"file": self._csv_file(), "entity_type": "nonexistent"},
            format="multipart",
        )
        assert response.status_code == 404

    def test_validate_job(self, auth_client, items_template):
        upload_resp = auth_client.post(
            "/api/v1/core/import/upload/",
            {"file": self._csv_file(), "entity_type": "items"},
            format="multipart",
        )
        job_id = upload_resp.json()["job_id"]

        response = auth_client.post(f"/api/v1/core/import/jobs/{job_id}/validate/")
        assert response.status_code == 200
        data = response.json()
        assert data["total_rows"] == 2

    def test_import_execute(self, auth_client, unmapped_template):
        upload_resp = auth_client.post(
            "/api/v1/core/import/upload/",
            {"file": self._csv_file(), "entity_type": "custom-import"},
            format="multipart",
        )
        job_id = upload_resp.json()["job_id"]
        auth_client.post(f"/api/v1/core/import/jobs/{job_id}/validate/")

        response = auth_client.post(f"/api/v1/core/import/jobs/{job_id}/import/")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_get_job_status(self, auth_client, unmapped_template):
        upload_resp = auth_client.post(
            "/api/v1/core/import/upload/",
            {"file": self._csv_file(), "entity_type": "custom-import"},
            format="multipart",
        )
        job_id = upload_resp.json()["job_id"]

        response = auth_client.get(f"/api/v1/core/import/jobs/{job_id}/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "uploaded"

    def test_job_not_found(self, auth_client):
        response = auth_client.get(
            "/api/v1/core/import/jobs/00000000-0000-0000-0000-000000000000/"
        )
        assert response.status_code == 404

    def test_import_history(self, auth_client, items_template):
        response = auth_client.get("/api/v1/core/import/history/")
        assert response.status_code == 200

    def test_unauthorized_access(self, client, items_template):
        response = client.get("/api/v1/core/import/templates/")
        assert response.status_code == 401
