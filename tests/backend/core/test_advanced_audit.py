"""Tests for Advanced Audit Trail (T018a)."""

import json
from datetime import timedelta
from uuid import UUID

import pytest
from django.db import IntegrityError
from django.utils import timezone
from rest_framework_simplejwt.tokens import AccessToken

from apps.core.models import (
    AuditExport,
    AuditLog,
    AuditLogBulk,
    AuditRetention,
    Company,
    User,
)
from apps.core.services.advanced_audit_service import (
    archive_old_logs,
    export_audit_logs,
    get_audit_dashboard,
    get_retention_policy,
    log_approval_action,
    log_bulk_operation,
    log_config_change,
    log_export,
    log_file_action,
    log_login_action,
    update_retention_policy,
)

# ── Fixtures ─────────────────────────────────────────────────────


@pytest.fixture
def admin_user(db):
    return User.objects.create_superuser(
        email="admin@test.com",
        password="admin123",
        first_name="Admin",
        last_name="User",
    )


@pytest.fixture
def regular_user(db):
    return User.objects.create_user(
        email="user@test.com",
        password="user123",
        first_name="Regular",
        last_name="User",
    )


@pytest.fixture
def company(db):
    return Company.objects.create(name="Test Company", code="TC")


@pytest.fixture
def other_company(db):
    return Company.objects.create(name="Other Company", code="OC")


@pytest.fixture
def audit_logs(admin_user, company):
    """Create sample audit logs across different categories."""
    logs = []
    for cat in ["crud", "login", "export", "config", "file", "approval", "bulk"]:
        for action in ["create", "update", "delete"]:
            log = AuditLog.objects.create(
                model_name="core.TestModel",
                record_id="123",
                action=action,
                category=cat,
                changes={"field": {"old": None, "new": "value"}},
                metadata={"category": cat, "extra": "info"},
                user=admin_user,
                ip_address="127.0.0.1",
                company=company,
            )
            logs.append(log)
    return logs


# ── Model Tests ──────────────────────────────────────────────────


@pytest.mark.django_db
class TestAuditLogExtendedModel:
    def test_category_defaults_to_crud(self, admin_user):
        log = AuditLog.objects.create(
            model_name="core.Test",
            record_id="1",
            action="create",
            user=admin_user,
        )
        assert log.category == "crud"

    def test_metadata_defaults_to_empty(self, admin_user):
        log = AuditLog.objects.create(
            model_name="core.Test",
            record_id="1",
            action="create",
            user=admin_user,
        )
        assert log.metadata == {}

    def test_category_choices(self, admin_user):
        for cat, _ in AuditLog.CATEGORY_CHOICES:
            log = AuditLog.objects.create(
                model_name="core.Test",
                record_id="1",
                action="create",
                category=cat,
                user=admin_user,
            )
            assert log.category == cat

    def test_bulk_operation_link(self, admin_user, company):
        bulk = AuditLogBulk.objects.create(
            operation_type="bulk_update",
            description="Test bulk",
            record_count=5,
            user=admin_user,
            company=company,
        )
        log = AuditLog.objects.create(
            model_name="core.Test",
            record_id="1",
            action="update",
            category="bulk",
            user=admin_user,
            bulk_operation=bulk,
            company=company,
        )
        assert log.bulk_operation == bulk
        assert bulk.audit_logs.count() == 1

    def test_category_db_index(self):
        for field in AuditLog._meta.fields:
            if field.name == "category":
                assert field.db_index


@pytest.mark.django_db
class TestAuditLogBulkModel:
    def test_create_bulk(self, admin_user, company):
        bulk = AuditLogBulk.objects.create(
            operation_type="bulk_import",
            description="Imported 10 items",
            record_count=10,
            affected_models=["core.Item", "core.Price"],
            user=admin_user,
            ip_address="127.0.0.1",
            company=company,
        )
        assert bulk.operation_type == "bulk_import"
        assert bulk.record_count == 10
        assert "core.Item" in bulk.affected_models
        assert str(bulk) == "bulk_import — 10 records"

    def test_bulk_operation_types(self, admin_user):
        for op_type, _ in AuditLogBulk.OPERATION_TYPES:
            bulk = AuditLogBulk.objects.create(operation_type=op_type, record_count=0)
            assert bulk.operation_type == op_type


@pytest.mark.django_db
class TestAuditRetentionModel:
    def test_create_retention(self, company):
        policy = AuditRetention.objects.create(company=company)
        assert policy.retention_years == 7
        assert policy.auto_archive is True
        assert policy.is_active is True
        assert str(policy) == "Test Company — 7 years"

    def test_retention_custom_years(self, company):
        policy = AuditRetention.objects.create(
            company=company, retention_years=3, auto_archive=False
        )
        assert policy.retention_years == 3
        assert policy.auto_archive is False

    def test_company_unique(self, company):
        AuditRetention.objects.create(company=company)
        with pytest.raises((IntegrityError,)):
            AuditRetention.objects.create(company=company)


@pytest.mark.django_db
class TestAuditExportModel:
    def test_create_export(self, admin_user, company):
        export = AuditExport.objects.create(
            export_type="csv",
            filters={"date_from": "2026-01-01", "category": "crud"},
            record_count=100,
            user=admin_user,
            company=company,
            file_path="/tmp/audit.csv",
        )
        assert export.export_type == "csv"
        assert export.record_count == 100
        assert str(export) == "csv export — 100 records"

    def test_export_defaults(self):
        export = AuditExport.objects.create(export_type="excel", record_count=0)
        assert export.filters == {}
        assert export.file_path == ""


# ── Service Tests ────────────────────────────────────────────────


@pytest.mark.django_db
class TestBulkOperationService:
    def test_log_bulk_operation(self, admin_user, company):
        records = [
            {"model_name": "core.Item", "id": "1"},
            {"model_name": "core.Item", "id": "2"},
            {"model_name": "core.Price", "id": "3"},
        ]
        bulk = log_bulk_operation(
            operation_type="bulk_delete",
            description="Deleted 3 records",
            records=records,
            user=admin_user,
            ip_address="127.0.0.1",
            company=company,
        )
        assert bulk.record_count == 3
        assert sorted(bulk.affected_models) == sorted(["core.Item", "core.Price"])
        assert bulk.user == admin_user

    def test_log_bulk_operation_no_records(self, admin_user):
        bulk = log_bulk_operation(
            operation_type="bulk_update",
            description="No changes",
            records=[],
            user=admin_user,
        )
        assert bulk.record_count == 0
        assert bulk.affected_models == []


@pytest.mark.django_db
class TestLoginAuditService:
    def test_log_login_action(self, admin_user):
        log = log_login_action(
            user=admin_user,
            action="create",
            ip_address="192.168.1.1",
            metadata={"device": "web", "browser": "Chrome"},
        )
        assert log.category == "login"
        assert log.model_name == "auth.User"
        assert log.record_id == str(admin_user.id)
        assert log.metadata.get("device") == "web"

    def test_log_login_action_defaults(self, admin_user):
        log = log_login_action(user=admin_user, action="create")
        assert log.category == "login"
        assert log.metadata == {}


@pytest.mark.django_db
class TestExportAuditService:
    def test_log_export(self, admin_user, company):
        export = log_export(
            export_type="csv",
            filters={"date_from": "2026-01-01"},
            record_count=50,
            user=admin_user,
            company=company,
        )
        assert export.export_type == "csv"
        assert export.record_count == 50
        # Should also create an audit log entry
        audit_log = AuditLog.objects.filter(category="export").first()
        assert audit_log is not None
        assert "export_type" in audit_log.changes

    def test_log_export_no_user(self, company):
        export = log_export(
            export_type="excel",
            filters={},
            record_count=0,
            company=company,
        )
        assert export.export_type == "excel"


@pytest.mark.django_db
class TestConfigAuditService:
    def test_log_config_change(self, admin_user, company):
        log = log_config_change(
            model_name="core.WorkflowDefinition",
            record_id="wf-001",
            changes={"name": {"old": "Old", "new": "New"}},
            user=admin_user,
            ip_address="127.0.0.1",
            company=company,
        )
        assert log.category == "config"
        assert log.model_name == "core.WorkflowDefinition"
        assert log.changes["name"]["old"] == "Old"


@pytest.mark.django_db
class TestFileAuditService:
    def test_log_file_action(self, admin_user, company):
        log = log_file_action(
            action="create",
            file_name="invoice.pdf",
            user=admin_user,
            ip_address="127.0.0.1",
            company=company,
            metadata={"file_size": 1024},
        )
        assert log.category == "file"
        assert log.model_name == "Attachment"
        assert log.metadata["file_name"] == "invoice.pdf"
        assert log.metadata["file_size"] == 1024

    def test_log_file_action_defaults(self):
        log = log_file_action(action="delete", file_name="old.doc")
        assert log.category == "file"
        assert log.metadata["file_name"] == "old.doc"


@pytest.mark.django_db
class TestApprovalAuditService:
    def test_log_approval_action(self, admin_user, company):
        execution_id = UUID("00000000-0000-0000-0000-000000000001")
        log = log_approval_action(
            execution_id=execution_id,
            action="approve",
            user=admin_user,
            ip_address="127.0.0.1",
            company=company,
            metadata={"document_type": "invoice"},
        )
        assert log.category == "approval"
        assert log.model_name == "WorkflowExecution"
        assert log.record_id == str(execution_id)
        assert log.metadata["document_type"] == "invoice"

    def test_log_approval_action_types(self, admin_user):
        for action in ["approve", "reject", "delegate"]:
            log = log_approval_action(
                execution_id=UUID("00000000-0000-0000-0000-000000000001"),
                action=action,
                user=admin_user,
            )
            assert log.action == action


@pytest.mark.django_db
class TestRetentionService:
    def test_get_retention_policy_creates_default(self, company):
        policy = get_retention_policy(company.id)
        assert policy is not None
        assert policy.retention_years == 7
        assert policy.company == company

    def test_get_retention_policy_returns_existing(self, company):
        AuditRetention.objects.create(company=company, retention_years=3)
        policy = get_retention_policy(company.id)
        assert policy.retention_years == 3

    def test_update_retention_policy(self, company):
        policy = update_retention_policy(
            company_id=company.id, retention_years=5, auto_archive=False
        )
        assert policy.retention_years == 5
        assert policy.auto_archive is False

    def test_update_retention_policy_updates_existing(self, company):
        AuditRetention.objects.create(company=company, retention_years=7)
        policy = update_retention_policy(company_id=company.id, retention_years=10)
        assert policy.retention_years == 10

    def test_get_retention_policy_nonexistent_company(self):
        policy = get_retention_policy(UUID("00000000-0000-0000-0000-000000000000"))
        assert policy is None


@pytest.mark.django_db
class TestArchiveService:
    def _create_old_log(self, model_name, record_id, user, company, days_old):
        """Create an audit log with a backdated timestamp (auto_now_add prevents override)."""
        log = AuditLog.objects.create(
            model_name=model_name,
            record_id=record_id,
            action="create",
            category="crud",
            user=user,
            company=company,
        )
        AuditLog.objects.filter(id=log.id).update(
            timestamp=timezone.now() - timedelta(days=days_old)
        )
        return AuditLog.objects.get(id=log.id)

    def test_archive_old_logs(self, admin_user, company):
        self._create_old_log("core.Test", "1", admin_user, company, 365 * 10)
        current_log = AuditLog.objects.create(
            model_name="core.Test",
            record_id="2",
            action="create",
            category="crud",
            user=admin_user,
            company=company,
        )

        result = archive_old_logs(company.id)
        assert result["companies_processed"] == 1

        remaining_logs = AuditLog.objects.filter(company=company)
        assert remaining_logs.count() == 1
        assert remaining_logs.first() == current_log

    def test_archive_logs_no_retention_policy(self, admin_user, company):
        self._create_old_log("core.Test", "1", admin_user, company, 365 * 10)
        result = archive_old_logs(company.id)
        # Default retention policy is 7 years
        assert result["deleted_count"] == 1

    def test_archive_logs_inactive_policy(self, admin_user, company):
        AuditRetention.objects.create(
            company=company, retention_years=7, is_active=False
        )
        old_log = AuditLog.objects.create(
            model_name="core.Test",
            record_id="1",
            action="create",
            user=admin_user,
            company=company,
            timestamp=timezone.now() - timedelta(days=365 * 10),
        )
        result = archive_old_logs(company.id)
        assert result["deleted_count"] == 0  # Policy is inactive
        assert AuditLog.objects.filter(id=old_log.id).exists()


@pytest.mark.django_db
class TestExportService:
    def test_export_audit_logs_csv(self, admin_user, company):
        AuditLog.objects.create(
            model_name="core.Test",
            record_id="1",
            action="create",
            category="crud",
            user=admin_user,
            company=company,
            changes={"name": {"old": None, "new": "Test"}},
        )

        content, content_type = export_audit_logs(
            fmt="csv",
            company_id=company.id,
            category="crud",
        )
        assert "Timestamp" in content
        assert "core.Test" in content
        assert content_type == "text/csv"

    def test_export_audit_logs_empty(self, company):
        content, content_type = export_audit_logs(
            fmt="csv",
            company_id=company.id,
        )
        lines = content.strip().split("\n")
        assert len(lines) == 1  # Header only


@pytest.mark.django_db
class TestDashboardService:
    def test_get_audit_dashboard(self, audit_logs, company):
        dashboard = get_audit_dashboard(company.id, period_days=365)
        assert dashboard["total_changes"] == 21  # 7 categories × 3 actions
        assert dashboard["period_days"] == 365
        assert len(dashboard["by_category"]) == 7
        assert len(dashboard["daily_trend"]) > 0

    def test_dashboard_by_category_counts(self, audit_logs, company):
        dashboard = get_audit_dashboard(company.id, period_days=365)
        for cat_entry in dashboard["by_category"]:
            assert cat_entry["category"] in dict(AuditLog.CATEGORY_CHOICES)
            assert cat_entry["count"] == 3  # 3 actions per category

    def test_dashboard_no_data(self, company):
        dashboard = get_audit_dashboard(company.id, period_days=30)
        assert dashboard["total_changes"] == 0
        assert dashboard["by_category"] == []
        assert dashboard["by_user"] == []
        assert dashboard["daily_trend"] == []


# ── API Tests ────────────────────────────────────────────────────


@pytest.mark.django_db
class TestAdvancedAuditAPI:
    def _auth_header(self, user):
        token = AccessToken.for_user(user)
        return {"HTTP_AUTHORIZATION": f"Bearer {token}"}

    def _company_header(self, company):
        return {"HTTP_X_COMPANY_ID": str(company.id)}

    def _headers(self, user, company):
        h = self._auth_header(user)
        h.update(self._company_header(company))
        return h

    def test_dashboard_requires_superuser(self, client, regular_user, company):
        response = client.get(
            "/api/v1/core/admin/audit-logs/dashboard/",
            **self._headers(regular_user, company),
        )
        assert response.status_code == 403

    def test_dashboard_returns_data(self, client, admin_user, company, audit_logs):
        response = client.get(
            "/api/v1/core/admin/audit-logs/dashboard/?period_days=365",
            **self._headers(admin_user, company),
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total_changes"] == 21
        assert len(data["by_category"]) == 7

    def test_dashboard_no_data(self, client, admin_user, other_company):
        response = client.get(
            "/api/v1/core/admin/audit-logs/dashboard/",
            **self._headers(admin_user, other_company),
        )
        assert response.status_code == 200
        assert response.json()["total_changes"] == 0

    def test_dashboard_requires_company(self, client, admin_user):
        response = client.get(
            "/api/v1/core/admin/audit-logs/dashboard/",
            **self._auth_header(admin_user),
        )
        assert response.status_code == 400

    def test_export_requires_superuser(self, client, regular_user, company):
        response = client.get(
            "/api/v1/core/admin/audit-logs/export/?fmt=csv",
            **self._headers(regular_user, company),
        )
        assert response.status_code == 403

    def test_export_returns_csv(self, client, admin_user, company):
        AuditLog.objects.create(
            model_name="core.Test",
            record_id="1",
            action="create",
            category="crud",
            user=admin_user,
            company=company,
        )
        response = client.get(
            "/api/v1/core/admin/audit-logs/export/?fmt=csv",
            **self._headers(admin_user, company),
        )
        assert response.status_code == 200
        assert response["Content-Type"] == "text/csv"
        assert "core.Test" in response.content.decode()

    def test_export_requires_company(self, client, admin_user):
        response = client.get(
            "/api/v1/core/admin/audit-logs/export/?fmt=csv",
            **self._auth_header(admin_user),
        )
        assert response.status_code == 400

    def test_get_retention_requires_superuser(self, client, regular_user, company):
        response = client.get(
            "/api/v1/core/admin/audit-retention/",
            **self._headers(regular_user, company),
        )
        assert response.status_code == 403

    def test_get_retention_creates_default(self, client, admin_user, company):
        response = client.get(
            "/api/v1/core/admin/audit-retention/",
            **self._headers(admin_user, company),
        )
        assert response.status_code == 200
        data = response.json()
        assert data["retention_years"] == 7
        assert data["auto_archive"] is True

    def test_update_retention(self, client, admin_user, company):
        response = client.put(
            "/api/v1/core/admin/audit-retention/",
            data=json.dumps({"retention_years": 5, "auto_archive": False}),
            content_type="application/json",
            **self._headers(admin_user, company),
        )
        assert response.status_code == 200
        data = response.json()
        assert data["retention_years"] == 5
        assert data["auto_archive"] is False

    def test_update_retention_invalid_years(self, client, admin_user, company):
        response = client.put(
            "/api/v1/core/admin/audit-retention/",
            data=json.dumps({"retention_years": 0}),
            content_type="application/json",
            **self._headers(admin_user, company),
        )
        assert response.status_code == 400

    def test_update_retention_too_many_years(self, client, admin_user, company):
        response = client.put(
            "/api/v1/core/admin/audit-retention/",
            data=json.dumps({"retention_years": 25}),
            content_type="application/json",
            **self._headers(admin_user, company),
        )
        assert response.status_code == 400

    def test_archive_requires_superuser(self, client, regular_user, company):
        response = client.post(
            "/api/v1/core/admin/audit-logs/archive-logs/",
            **self._headers(regular_user, company),
        )
        assert response.status_code == 403

    def test_archive_returns_result(self, client, admin_user, company):
        log = AuditLog.objects.create(
            model_name="core.Test",
            record_id="1",
            action="create",
            category="crud",
            user=admin_user,
            company=company,
        )
        AuditLog.objects.filter(id=log.id).update(
            timestamp=timezone.now() - timedelta(days=365 * 10)
        )
        response = client.post(
            "/api/v1/core/admin/audit-logs/archive-logs/",
            **self._headers(admin_user, company),
        )
        assert response.status_code == 200
        data = response.json()
        assert data["deleted_count"] == 1
        assert data["companies_processed"] == 1

    def test_archive_requires_company(self, client, admin_user):
        response = client.post(
            "/api/v1/core/admin/audit-logs/archive-logs/",
            **self._auth_header(admin_user),
        )
        assert response.status_code == 400

    def test_list_exports_requires_superuser(self, client, regular_user, company):
        response = client.get(
            "/api/v1/core/admin/audit-exports/",
            **self._headers(regular_user, company),
        )
        assert response.status_code == 403

    def test_list_exports(self, client, admin_user, company):
        AuditExport.objects.create(
            export_type="csv",
            record_count=10,
            user=admin_user,
            company=company,
        )
        response = client.get(
            "/api/v1/core/admin/audit-exports/",
            **self._headers(admin_user, company),
        )
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 1
        assert len(data["results"]) == 1
        assert data["results"][0]["export_type"] == "csv"
