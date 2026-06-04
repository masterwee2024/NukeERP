"""Tests for T009f — Transaction Migration."""

from datetime import date
from uuid import uuid4

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework_simplejwt.tokens import AccessToken

from apps.core.models import (
    Company,
    TransactionMigration,
    TransactionMigrationLine,
    User,
)
from apps.core.services.transaction_migration_service import (
    LINE_TYPE_CONFIG,
    complete_migration,
    create_migration,
    generate_csv_template,
    get_company_migrations,
    get_migration,
    get_migration_summary,
    import_lines,
    parse_csv,
    rollback_migration,
    validate_rows,
)

SAMPLE_PO_CSV = (
    "po_number,supplier_code,item_code,quantity,unit_price,currency\n"
    "PO-001,SUP001,ITEM-001,10,100.00,MYR\n"
    "PO-002,SUP001,ITEM-002,5,250.00,MYR\n"
)

SAMPLE_JOURNAL_CSV = (
    "entry_number,date,account_code,description,debit,credit\n"
    "JE-001,2025-12-01,1000,Test entry,1000.00,0.00\n"
    "JE-001,2025-12-01,4000,Test entry,0.00,1000.00\n"
)


@pytest.fixture
def db():
    pass


@pytest.fixture
def company(db):
    return Company.objects.create(name="Test Corp", code="TEST", base_currency="MYR")


@pytest.fixture
def admin_user(db):
    return User.objects.create_superuser(
        email="admin@example.com",
        password="adminpass123",
    )


@pytest.fixture
def auth_client(client, admin_user, company):
    admin_user.current_company = company
    admin_user.save(update_fields=["current_company"])
    token = AccessToken.for_user(admin_user)
    client.defaults["HTTP_AUTHORIZATION"] = f"Bearer {token}"
    client.defaults["HTTP_X_COMPANY_ID"] = str(company.id)
    return client


# ---------------------------------------------------------------------------
# Model Tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestTransactionMigrationModel:
    def test_create_migration(self, company):
        m = TransactionMigration.objects.create(
            company=company,
            go_live_date="2026-01-01",
            migration_option="fresh",
        )
        assert m.status == "draft"
        assert m.migration_option == "fresh"
        assert str(m.go_live_date) == "2026-01-01"

    def test_create_line(self, company):
        m = TransactionMigration.objects.create(
            company=company,
            go_live_date="2026-01-01",
        )
        line = TransactionMigrationLine.objects.create(
            migration=m,
            line_type="pending_po",
            row_number=0,
            raw_data={"po_number": "PO-001"},
            data={"po_number": "PO-001", "item_code": "ITEM-001"},
            status="valid",
        )
        assert line.line_type == "pending_po"
        assert str(line) == "pending_po Row 0 — valid"


# ---------------------------------------------------------------------------
# Service Tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestTransactionMigrationService:
    def test_create_migration_service(self, company):
        m = create_migration(
            company_id=company.id,
            go_live_date=date(2026, 1, 1),
            migration_option="full",
        )
        assert m.migration_option == "full"
        assert m.status == "draft"

    def test_create_migration_invalid_option(self, company):
        with pytest.raises(ValueError, match="migration_option"):
            create_migration(
                company_id=company.id,
                go_live_date=date(2026, 1, 1),
                migration_option="bad",
            )

    def test_get_migration(self, company):
        m = create_migration(company_id=company.id, go_live_date=date(2026, 1, 1))
        found = get_migration(m.id, company.id)
        assert found is not None
        assert found.id == m.id

    def test_get_migration_wrong_company(self, company):
        m = create_migration(company_id=company.id, go_live_date=date(2026, 1, 1))
        other_id = uuid4()
        assert get_migration(m.id, other_id) is None

    def test_get_company_migrations(self, company):
        create_migration(company_id=company.id, go_live_date=date(2026, 1, 1))
        create_migration(company_id=company.id, go_live_date=date(2026, 2, 1))
        assert len(get_company_migrations(company.id)) == 2

    def test_parse_csv(self):
        headers, rows = parse_csv(SAMPLE_PO_CSV)
        assert len(headers) == 6
        assert len(rows) == 2
        assert rows[0]["po_number"] == "PO-001"

    def test_parse_csv_empty(self):
        _, rows = parse_csv("header1,header2\n")
        assert rows == []

    def test_validate_valid_rows(self):
        rows = [
            {
                "po_number": "PO-001",
                "supplier_code": "S1",
                "item_code": "I1",
                "quantity": "10",
                "unit_price": "100",
            },
        ]
        results = validate_rows("pending_po", rows)
        assert len(results) == 1
        assert results[0]["status"] == "valid"

    def test_validate_missing_fields(self):
        rows = [{"po_number": "PO-001", "quantity": "10"}]
        results = validate_rows("pending_po", rows)
        assert results[0]["status"] == "error"
        assert any("supplier_code" in e for e in results[0]["errors"])

    def test_import_lines(self, company):
        m = create_migration(company_id=company.id, go_live_date=date(2026, 1, 1))
        rows = [
            {
                "po_number": "PO-001",
                "supplier_code": "S1",
                "item_code": "I1",
                "quantity": "10",
                "unit_price": "100",
            },
        ]
        validation = validate_rows("pending_po", rows)
        result = import_lines(m.id, "pending_po", rows, validation)
        assert result["total_rows"] == 1
        assert result["valid_count"] == 1
        assert TransactionMigrationLine.objects.filter(migration=m).count() == 1

    def test_get_migration_summary(self, company):
        m = create_migration(company_id=company.id, go_live_date=date(2026, 1, 1))
        rows = [
            {
                "po_number": "PO-001",
                "supplier_code": "S1",
                "item_code": "I1",
                "quantity": "10",
                "unit_price": "100",
            }
        ]
        validation = validate_rows("pending_po", rows)
        import_lines(m.id, "pending_po", rows, validation)
        summary = get_migration_summary(m.id)
        assert summary["line_types"]["pending_po"]["valid"] == 1

    def test_complete_migration(self, company):
        m = create_migration(company_id=company.id, go_live_date=date(2026, 1, 1))
        result = complete_migration(m.id)
        assert result["status"] == "completed"

    def test_complete_already_completed_raises(self, company):
        m = create_migration(company_id=company.id, go_live_date=date(2026, 1, 1))
        complete_migration(m.id)
        with pytest.raises(ValueError, match="already completed"):
            complete_migration(m.id)

    def test_rollback_migration(self, company):
        m = create_migration(company_id=company.id, go_live_date=date(2026, 1, 1))
        result = rollback_migration(m.id)
        assert result["status"] == "rolled_back"
        m.refresh_from_db()
        assert m.status == "rolled_back"

    def test_rollback_twice_raises(self, company):
        m = create_migration(company_id=company.id, go_live_date=date(2026, 1, 1))
        rollback_migration(m.id)
        with pytest.raises(ValueError, match="already rolled back"):
            rollback_migration(m.id)

    def test_generate_csv_template(self):
        csv_content = generate_csv_template("pending_po")
        assert "po_number" in csv_content
        assert "supplier_code" in csv_content
        assert "item_code" in csv_content

    def test_generate_csv_template_unknown(self):
        with pytest.raises(ValueError):
            generate_csv_template("unknown")

    def test_validate_journal_debit_credit(self):
        rows = [
            {
                "entry_number": "JE-001",
                "date": "2025-01-01",
                "account_code": "1000",
                "description": "test",
                "debit": "abc",
                "credit": "0",
            }
        ]
        results = validate_rows("historical_journal", rows)
        assert results[0]["status"] == "error"

    def test_line_type_config_has_all_types(self):
        expected = {
            "pending_po",
            "pending_so",
            "pending_grn",
            "historical_journal",
            "historical_ap_invoice",
            "historical_ar_invoice",
        }
        assert set(LINE_TYPE_CONFIG.keys()) == expected


# ---------------------------------------------------------------------------
# API Tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestTransactionMigrationAPI:
    def test_list_migrations_empty(self, auth_client):
        response = auth_client.get("/api/v1/core/transaction-migration/migrations/")
        assert response.status_code == 200
        assert response.json() == []

    def test_create_migration(self, auth_client, company):
        response = auth_client.post(
            "/api/v1/core/transaction-migration/migrations/",
            data={"go_live_date": "2026-01-01", "migration_option": "fresh"},
            content_type="application/json",
        )
        assert response.status_code == 200
        data = response.json()
        assert data["migration_option"] == "fresh"
        assert data["status"] == "draft"

    def test_create_and_get_migration(self, auth_client):
        resp = auth_client.post(
            "/api/v1/core/transaction-migration/migrations/",
            data={"go_live_date": "2026-01-01", "migration_option": "full"},
            content_type="application/json",
        )
        mid = resp.json()["id"]
        resp2 = auth_client.get(f"/api/v1/core/transaction-migration/migrations/{mid}/")
        assert resp2.status_code == 200
        assert resp2.json()["migration_option"] == "full"

    def test_create_list_migrations(self, auth_client):
        auth_client.post(
            "/api/v1/core/transaction-migration/migrations/",
            data={"go_live_date": "2026-01-01", "migration_option": "fresh"},
            content_type="application/json",
        )
        resp = auth_client.get("/api/v1/core/transaction-migration/migrations/")
        assert len(resp.json()) == 1

    def test_get_summary(self, auth_client, company):
        m = create_migration(company_id=company.id, go_live_date=date(2026, 1, 1))
        resp = auth_client.get(
            f"/api/v1/core/transaction-migration/migrations/{m.id}/summary/"
        )
        assert resp.status_code == 200
        assert resp.json()["migration_option"] == "fresh"

    def test_complete(self, auth_client, company):
        m = create_migration(company_id=company.id, go_live_date=date(2026, 1, 1))
        resp = auth_client.post(
            f"/api/v1/core/transaction-migration/migrations/{m.id}/complete/"
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "completed"

    def test_rollback(self, auth_client, company):
        m = create_migration(company_id=company.id, go_live_date=date(2026, 1, 1))
        resp = auth_client.post(
            f"/api/v1/core/transaction-migration/migrations/{m.id}/rollback/"
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "rolled_back"

    def test_get_template(self, auth_client):
        resp = auth_client.get(
            "/api/v1/core/transaction-migration/templates/pending_po/"
        )
        assert resp.status_code == 200
        assert "po_number" in resp.json()["csv_content"]

    def test_get_template_unknown(self, auth_client):
        resp = auth_client.get("/api/v1/core/transaction-migration/templates/unknown/")
        assert resp.status_code == 404

    def test_upload_csv(self, client, admin_user, company):
        admin_user.current_company = company
        admin_user.save(update_fields=["current_company"])
        token = AccessToken.for_user(admin_user)
        client.defaults["HTTP_AUTHORIZATION"] = f"Bearer {token}"
        client.defaults["HTTP_X_COMPANY_ID"] = str(company.id)
        m = create_migration(company_id=company.id, go_live_date=date(2026, 1, 1))
        uploaded = SimpleUploadedFile(
            "test.csv", SAMPLE_PO_CSV.encode("utf-8-sig"), content_type="text/csv"
        )
        resp = client.post(
            f"/api/v1/core/transaction-migration/migrations/{m.id}/upload/pending_po/",
            {"file": uploaded},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_rows"] == 2
        assert data["valid_count"] == 2
