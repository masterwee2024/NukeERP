"""Tests for the Opening Balance Migration (T009e)."""

import json

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework_simplejwt.tokens import AccessToken

from apps.core.models import (
    Company,
    OpeningBalanceAP,
    OpeningBalanceAR,
    OpeningBalanceAsset,
    OpeningBalanceGL,
    OpeningBalanceInventory,
    OpeningBalanceMigration,
    User,
)
from apps.core.services import opening_balance_service


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
def company(db):
    return Company.objects.create(name="Test Corp", code="TEST", base_currency="MYR")


@pytest.fixture
def migration(db, company, admin_user):
    return OpeningBalanceMigration.objects.create(
        company=company,
        go_live_date="2026-01-01",
        status="draft",
        created_by=admin_user,
    )


@pytest.fixture
def auth_client(client, admin_user, company):
    admin_user.current_company = company
    admin_user.save(update_fields=["current_company"])
    token = AccessToken.for_user(admin_user)
    client.defaults["HTTP_AUTHORIZATION"] = f"Bearer {token}"
    return client


# ── Model Tests ──────────────────────────────────────────────────


@pytest.mark.django_db
class TestOpeningBalanceModels:
    def test_create_migration(self, migration, company):
        assert migration.status == "draft"
        assert str(migration.go_live_date) == "2026-01-01"
        assert str(migration) == f"Migration {migration.id} — TEST (2026-01-01)"

    def test_gl_line(self, migration):
        gl = OpeningBalanceGL.objects.create(
            migration=migration,
            account_code="1000",
            debit=50000,
            row_number=1,
            status="imported",
        )
        assert float(gl.debit) == 50000

    def test_ap_line(self, migration):
        ap = OpeningBalanceAP.objects.create(
            migration=migration,
            supplier_code="SUP001",
            invoice_no="INV-001",
            invoice_date="2025-12-01",
            due_date="2026-01-15",
            amount=10000,
            row_number=1,
            status="imported",
        )
        assert float(ap.amount) == 10000

    def test_ar_line(self, migration):
        ar = OpeningBalanceAR.objects.create(
            migration=migration,
            customer_code="CUST001",
            invoice_no="INV-001",
            invoice_date="2025-12-01",
            due_date="2026-01-15",
            amount=20000,
            row_number=1,
            status="imported",
        )
        assert float(ar.amount) == 20000

    def test_inventory_line(self, migration):
        inv = OpeningBalanceInventory.objects.create(
            migration=migration,
            item_code="ITEM001",
            warehouse_code="WH01",
            quantity=100,
            unit_cost=10.50,
            row_number=1,
            status="imported",
        )
        assert float(inv.quantity) == 100
        assert float(inv.unit_cost) == 10.50

    def test_asset_line(self, migration):
        asset = OpeningBalanceAsset.objects.create(
            migration=migration,
            asset_code="AST001",
            name="Machine A",
            purchase_date="2025-06-01",
            cost=100000,
            accumulated_depreciation=20000,
            useful_life=10,
            row_number=1,
            status="imported",
        )
        assert float(asset.cost) == 100000


# ── Service Tests ────────────────────────────────────────────────


@pytest.mark.django_db
class TestOpeningBalanceService:
    def test_create_migration(self, company, admin_user):
        m = opening_balance_service.create_migration(
            company.id, "2026-01-01", admin_user
        )
        assert m.status == "draft"
        assert m.company_id == company.id

    def test_get_migration(self, migration):
        m = opening_balance_service.get_migration(migration.id)
        assert m is not None
        assert m.id == migration.id

    def test_get_migration_not_found(self, db):
        import uuid

        assert opening_balance_service.get_migration(uuid.uuid4()) is None

    def test_generate_csv_template_gl(self):
        result = opening_balance_service.generate_csv_template("gl")
        assert result is not None
        content, filename = result
        assert "Account Code" in content
        assert filename == "opening_gl_template.csv"

    def test_generate_csv_template_invalid(self):
        assert opening_balance_service.generate_csv_template("invalid") is None

    def test_validate_rows_gl_valid(self):
        rows = [{"account_code": "1000", "debit": "50000", "credit": "0"}]
        result = opening_balance_service.validate_rows("gl", rows)
        assert len(result) == 1
        assert result[0]["errors"] == []

    def test_validate_rows_gl_invalid(self):
        rows = [{"account_code": "", "debit": "0", "credit": "0"}]
        result = opening_balance_service.validate_rows("gl", rows)
        assert len(result[0]["errors"]) > 0

    def test_validate_gl_balance(self):
        rows = [
            {"debit": "50000", "credit": "0"},
            {"debit": "0", "credit": "50000"},
        ]
        result = opening_balance_service.validate_gl_balance(rows)
        assert result["balanced"] is True

    def test_validate_gl_balance_unbalanced(self):
        rows = [
            {"debit": "50000", "credit": "0"},
            {"debit": "0", "credit": "40000"},
        ]
        result = opening_balance_service.validate_gl_balance(rows)
        assert result["balanced"] is False

    def test_import_gl(self, migration):
        rows = [
            {
                "account_code": "1000",
                "account_name": "Cash",
                "debit": "50000",
                "credit": "0",
            }
        ]
        validation = opening_balance_service.validate_rows("gl", rows)
        result = opening_balance_service.import_gl(migration.id, rows, validation)
        assert result["success"] == 1
        assert (
            OpeningBalanceGL.objects.filter(
                migration=migration, status="imported"
            ).count()
            == 1
        )

    def test_import_ap(self, migration):
        rows = [
            {
                "supplier_code": "SUP001",
                "invoice_no": "INV-001",
                "invoice_date": "2025-12-01",
                "due_date": "2026-01-15",
                "amount": "10000",
                "currency": "MYR",
            }
        ]
        validation = opening_balance_service.validate_rows("ap", rows)
        result = opening_balance_service.import_ap(migration.id, rows, validation)
        assert result["success"] == 1

    def test_import_ar(self, migration):
        rows = [
            {
                "customer_code": "CUST001",
                "invoice_no": "INV-001",
                "invoice_date": "2025-12-01",
                "due_date": "2026-01-15",
                "amount": "20000",
            }
        ]
        validation = opening_balance_service.validate_rows("ar", rows)
        result = opening_balance_service.import_ar(migration.id, rows, validation)
        assert result["success"] == 1

    def test_import_inventory(self, migration):
        rows = [
            {
                "item_code": "ITEM001",
                "warehouse_code": "WH01",
                "quantity": "100",
                "unit_cost": "10.50",
            }
        ]
        validation = opening_balance_service.validate_rows("inventory", rows)
        result = opening_balance_service.import_inventory(
            migration.id, rows, validation
        )
        assert result["success"] == 1

    def test_import_asset(self, migration):
        rows = [
            {
                "asset_code": "AST001",
                "name": "Machine",
                "purchase_date": "2025-06-01",
                "cost": "100000",
                "accumulated_depreciation": "20000",
                "useful_life": "10",
            }
        ]
        validation = opening_balance_service.validate_rows("asset", rows)
        result = opening_balance_service.import_asset(migration.id, rows, validation)
        assert result["success"] == 1

    def test_get_summary(self, migration):
        opening_balance_service.import_gl(
            migration.id,
            [{"account_code": "1000", "debit": "50000", "credit": "0"}],
            opening_balance_service.validate_rows(
                "gl", [{"account_code": "1000", "debit": "50000", "credit": "0"}]
            ),
        )
        summary = opening_balance_service.get_migration_summary(migration.id)
        assert summary["gl"]["success"] == 1

    def test_rollback_migration(self, migration):
        rows = [{"account_code": "1000", "debit": "50000", "credit": "0"}]
        validation = opening_balance_service.validate_rows("gl", rows)
        opening_balance_service.import_gl(migration.id, rows, validation)
        opening_balance_service.rollback_migration(migration.id)
        assert OpeningBalanceGL.objects.filter(migration=migration).count() == 0
        migration.refresh_from_db()
        assert migration.status == "rolled_back"

    def test_complete_migration(self, migration):
        opening_balance_service.complete_migration(migration.id)
        migration.refresh_from_db()
        assert migration.status == "completed"

    def test_get_company_migrations(self, company, admin_user):
        opening_balance_service.create_migration(company.id, "2026-01-01", admin_user)
        migrations = opening_balance_service.get_company_migrations(company.id)
        assert len(migrations) >= 1


# ── CSV Template Tests ────────────────────────────────────────────


@pytest.mark.django_db
class TestCSVTemplates:
    def test_all_templates_generatable(self):
        for bt in ("gl", "ap", "ar", "inventory", "asset"):
            result = opening_balance_service.generate_csv_template(bt)
            assert result is not None, f"Template for {bt} should exist"


# ── API Tests ────────────────────────────────────────────────────


@pytest.mark.django_db
class TestOpeningBalanceAPI:
    def test_create_migration(self, auth_client, company):

        response = auth_client.post(
            "/api/v1/core/opening-balance/migrations/",
            json.dumps({"company_id": str(company.id), "go_live_date": "2026-01-01"}),
            content_type="application/json",
        )
        if response.status_code != 200:
            print("CREATE RESPONSE:", response.status_code, response.content[:500])
        assert response.status_code == 200, response.content
        data = response.json()
        assert data["status"] == "draft"

    def test_get_migration(self, auth_client, migration):
        response = auth_client.get(
            f"/api/v1/core/opening-balance/migrations/{migration.id}/"
        )
        assert response.status_code == 200
        assert response.json()["status"] == "draft"

    def test_get_summary(self, auth_client, migration):
        response = auth_client.get(
            f"/api/v1/core/opening-balance/migrations/{migration.id}/summary/"
        )
        assert response.status_code == 200

    def test_list_migrations(self, auth_client, migration):
        response = auth_client.get("/api/v1/core/opening-balance/migrations/")
        if response.status_code != 200:
            print("LIST RESPONSE:", response.status_code, response.content[:500])
        assert response.status_code == 200

    def test_complete_migration(self, auth_client, migration):
        response = auth_client.post(
            f"/api/v1/core/opening-balance/migrations/{migration.id}/complete/"
        )
        assert response.status_code == 200

    def test_rollback_migration(self, auth_client, migration):
        response = auth_client.post(
            f"/api/v1/core/opening-balance/migrations/{migration.id}/rollback/"
        )
        assert response.status_code == 200

    def test_download_csv_template(self, auth_client):
        response = auth_client.get("/api/v1/core/opening-balance/templates/gl/csv/")
        assert response.status_code == 200
        assert response["Content-Type"] == "text/csv"

    def test_upload_csv(self, auth_client, migration):
        csv_data = "account_code,account_name,debit,credit\n1000,Cash,50000,0\n"
        response = auth_client.post(
            f"/api/v1/core/opening-balance/migrations/{migration.id}/upload/gl/",
            {
                "file": SimpleUploadedFile(
                    "gl.csv", csv_data.encode(), content_type="text/csv"
                )
            },
            format="multipart",
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total_rows"] == 1

    def test_upload_csv_invalid_type(self, auth_client, migration):
        response = auth_client.post(
            f"/api/v1/core/opening-balance/migrations/{migration.id}/upload/invalid/",
            {
                "file": SimpleUploadedFile(
                    "test.csv", b"a,b\n1,2", content_type="text/csv"
                )
            },
            format="multipart",
        )
        assert response.status_code == 400

    def test_import_execute(self, auth_client, migration):
        csv_data = "account_code,account_name,debit,credit\n1000,Cash,50000,0\n2000,Equity,0,50000\n"
        response = auth_client.post(
            f"/api/v1/core/opening-balance/migrations/{migration.id}/import/gl/",
            {
                "file": SimpleUploadedFile(
                    "gl.csv", csv_data.encode(), content_type="text/csv"
                )
            },
            format="multipart",
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] == 2

    def test_validate_gl_balance(self, auth_client, migration):
        # Import some GL data first
        csv_data = "account_code,account_name,debit,credit\n1000,Cash,50000,0\n2000,Equity,0,50000\n"
        auth_client.post(
            f"/api/v1/core/opening-balance/migrations/{migration.id}/import/gl/",
            {
                "file": SimpleUploadedFile(
                    "gl.csv", csv_data.encode(), content_type="text/csv"
                )
            },
            format="multipart",
        )
        response = auth_client.post(
            f"/api/v1/core/opening-balance/migrations/{migration.id}/validate-gl/"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["balanced"] is True

    def test_unauthorized(self, client):
        response = client.get("/api/v1/core/opening-balance/migrations/")
        assert response.status_code == 401
