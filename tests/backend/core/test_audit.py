"""Tests for Audit Log — model, mixin tracking, API."""

import uuid

import pytest
from django.contrib.auth import get_user_model

from apps.core.mixins.audit_mixin import (
    clear_audit_context,
    compute_changes,
    get_field_dict,
    serialize_field_value,
    set_audit_context,
)
from apps.core.models import AuditLog, Company

User = get_user_model()


# --- Fixtures ---


@pytest.fixture
def admin_user(db):
    user = User.objects.create_superuser(email="admin@test.com", password="admin123")
    return user


@pytest.fixture
def regular_user(db):
    return User.objects.create_user(email="user@test.com", password="user123")


@pytest.fixture
def company(db):
    return Company.objects.create(name="Test Company", code="TC")


# --- AuditLog Model Tests ---


@pytest.mark.django_db
class TestAuditLogModel:
    def test_create_audit_log(self, admin_user, company):
        log = AuditLog.objects.create(
            model_name="core.Company",
            record_id=str(company.id),
            action="create",
            changes={"name": {"old": None, "new": "Test Company"}},
            user=admin_user,
            ip_address="127.0.0.1",
            company=company,
        )
        assert log.action == "create"
        assert log.model_name == "core.Company"
        assert log.user == admin_user
        assert log.ip_address == "127.0.0.1"
        assert log.company == company
        assert log.timestamp is not None
        assert str(log) == f"create core.Company #{company.id}"

    def test_audit_log_no_user(self, company):
        log = AuditLog.objects.create(
            model_name="core.Company",
            record_id=str(company.id),
            action="delete",
            changes={},
        )
        assert log.user is None
        assert log.ip_address is None
        assert log.company is None

    def test_audit_log_ordering(self, admin_user):
        AuditLog.objects.create(
            model_name="core.Test",
            record_id="1",
            action="create",
            user=admin_user,
        )
        import time

        time.sleep(0.01)
        log2 = AuditLog.objects.create(
            model_name="core.Test",
            record_id="2",
            action="update",
            user=admin_user,
        )
        logs = list(AuditLog.objects.all())
        assert logs[0] == log2  # newest first (default ordering)


# --- Diff / Serialization Tests ---


class TestAuditDiff:
    def test_compute_changes_new_fields(self):
        old = {"name": "Old", "email": "old@test.com"}
        new = {"name": "New", "email": "old@test.com"}
        result = compute_changes(old, new)
        assert result == {"name": {"old": "Old", "new": "New"}}
        assert "email" not in result  # unchanged

    def test_compute_changes_excludes_metadata(self):
        old = {
            "name": "X",
            "updated_at": "2024-01-01",
            "version": 1,
            "created_at": "2024-01-01",
        }
        new = {
            "name": "Y",
            "updated_at": "2024-01-02",
            "version": 2,
            "created_at": "2024-01-01",
        }
        result = compute_changes(old, new)
        assert "updated_at" not in result
        assert "version" not in result
        assert "created_at" not in result
        assert result == {"name": {"old": "X", "new": "Y"}}

    def test_compute_changes_all_new(self):
        result = compute_changes({}, {"name": "New"})
        assert result == {"name": {"old": None, "new": "New"}}

    def test_compute_changes_all_deleted(self):
        result = compute_changes({"name": "Old"}, {})
        assert result == {"name": {"old": "Old", "new": None}}

    def test_serialize_model_instance(self, db):
        company = Company.objects.create(name="S", code="S1")
        value = serialize_field_value(company)
        assert value == str(company.pk)

    def test_serialize_uuid(self):
        val = uuid.uuid4()
        result = serialize_field_value(val)
        assert result == str(val)

    def test_get_field_dict(self, company):
        d = get_field_dict(company)
        assert d["name"] == "Test Company"
        assert d["code"] == "TC"
        assert "id" in d
        assert "created_at" in d


# --- AuditModelMixin Integration Tests ---


@pytest.mark.django_db
class TestAuditMixinTracking:
    def test_create_tracks_audit_log(self, db):
        set_audit_context(None, "192.168.1.1")
        company = Company.objects.create(name="NewCo", code="NC")
        logs = AuditLog.objects.filter(
            model_name="core.Company", record_id=str(company.id)
        )
        assert logs.count() == 1
        log = logs.first()
        assert log.action == "create"
        assert log.changes.get("name", {}).get("new") == "NewCo"
        assert log.changes.get("code", {}).get("new") == "NC"
        assert log.ip_address == "192.168.1.1"
        clear_audit_context()

    def test_update_tracks_diff(self, db):
        company = Company.objects.create(name="Original", code="OR")
        AuditLog.objects.all().delete()  # clear create log

        set_audit_context(None)
        company.name = "Updated"
        company.save()
        logs = AuditLog.objects.filter(
            model_name="core.Company", record_id=str(company.id), action="update"
        )
        assert logs.count() == 1
        log = logs.first()
        assert log.changes == {"name": {"old": "Original", "new": "Updated"}}
        clear_audit_context()

    def test_no_audit_on_no_change(self, db):
        company = Company.objects.create(name="Stable", code="ST")
        AuditLog.objects.all().delete()

        set_audit_context(None)
        company.save()  # same values, only version increments
        logs = AuditLog.objects.filter(action="update")
        assert logs.count() == 0  # no meaningful changes
        clear_audit_context()

    def test_delete_tracks_audit(self, db):
        company = Company.objects.create(name="DeleteMe", code="DM")
        pk = str(company.id)
        AuditLog.objects.all().delete()

        set_audit_context(None, "10.0.0.1")
        company.delete()
        logs = AuditLog.objects.filter(
            model_name="core.Company", record_id=pk, action="delete"
        )
        assert logs.count() == 1
        log = logs.first()
        assert log.changes.get("name", {}).get("old") == "DeleteMe"
        assert log.changes.get("code", {}).get("old") == "DM"
        assert log.changes.get("name", {}).get("new") is None  # deleted
        assert log.ip_address == "10.0.0.1"
        clear_audit_context()

    def test_audit_with_user_context(self, db, admin_user):
        set_audit_context(admin_user)
        company = Company.objects.create(name="UserTrack", code="UT")
        logs = AuditLog.objects.filter(record_id=str(company.id))
        log = logs.first()
        assert log.user == admin_user
        clear_audit_context()

    def test_audit_with_company_context(self, db, company):
        set_audit_context(None)
        new_company = Company.objects.create(name="SubCo", code="SC")
        # AuditLog for company creation won't have company FK (it's the record's own company)
        # but the field dict captures all fields including company's own data
        logs = AuditLog.objects.filter(record_id=str(new_company.id))
        log = logs.first()
        # Company model doesn't have `company` FK (it IS a company)
        assert log.company is None
        clear_audit_context()

    def test_inherited_concurrency_model_works(self, db):
        """Ensure that ConcurrencyModel still works correctly alongside AuditModelMixin."""
        company = Company.objects.create(name="VersionTest", code="VT")
        original_version = company.version
        company.name = "VersionTest Updated"
        company.save()
        company.refresh_from_db()
        assert company.version == original_version + 1

    def test_concurrency_conflict(self, db):
        """Setting stale version should still raise ConcurrencyError."""
        from apps.core.mixins.models import ConcurrencyError

        company = Company.objects.create(name="Conflict", code="CF")
        company.version = 0  # stale
        with pytest.raises(ConcurrencyError):
            company.save()


# --- API Tests ---


@pytest.mark.django_db
class TestAuditAPI:
    def test_list_unauthenticated(self, client):
        response = client.get("/api/v1/core/admin/audit-logs/")
        assert response.status_code == 401

    def test_list_regular_user(self, client, regular_user):
        from rest_framework_simplejwt.tokens import AccessToken

        token = AccessToken.for_user(regular_user)
        response = client.get(
            "/api/v1/core/admin/audit-logs/", HTTP_AUTHORIZATION=f"Bearer {token}"
        )
        assert response.status_code == 403

    def test_list_admin(self, client, admin_user):
        from rest_framework_simplejwt.tokens import AccessToken

        AuditLog.objects.create(
            model_name="core.Test",
            record_id="1",
            action="create",
        )
        token = AccessToken.for_user(admin_user)
        response = client.get(
            "/api/v1/core/admin/audit-logs/", HTTP_AUTHORIZATION=f"Bearer {token}"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["count"] >= 1
        assert len(data["results"]) >= 1

    def test_list_filter_by_action(self, client, admin_user):
        from rest_framework_simplejwt.tokens import AccessToken

        AuditLog.objects.create(model_name="core.A", record_id="1", action="create")
        AuditLog.objects.create(model_name="core.A", record_id="2", action="delete")
        token = AccessToken.for_user(admin_user)
        response = client.get(
            "/api/v1/core/admin/audit-logs/?action=delete",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        data = response.json()
        assert data["count"] >= 1
        for result in data["results"]:
            assert result["action"] == "delete"

    def test_list_filter_by_model_name(self, client, admin_user):
        from rest_framework_simplejwt.tokens import AccessToken

        AuditLog.objects.create(
            model_name="core.Company", record_id="1", action="create"
        )
        AuditLog.objects.create(model_name="core.User", record_id="1", action="create")
        token = AccessToken.for_user(admin_user)
        response = client.get(
            "/api/v1/core/admin/audit-logs/?model_name=Company",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        data = response.json()
        for result in data["results"]:
            assert "Company" in result["model_name"]

    def test_detail_admin(self, client, admin_user):
        from rest_framework_simplejwt.tokens import AccessToken

        log = AuditLog.objects.create(
            model_name="core.Test",
            record_id="1",
            action="update",
            changes={"field": {"old": "A", "new": "B"}},
            ip_address="10.0.0.1",
        )
        token = AccessToken.for_user(admin_user)
        response = client.get(
            f"/api/v1/core/admin/audit-logs/{log.id}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        assert response.status_code == 200
        data = response.json()
        assert data["model_name"] == "core.Test"
        assert data["action"] == "update"
        assert data["ip_address"] == "10.0.0.1"

    def test_detail_not_found(self, client, admin_user):
        from rest_framework_simplejwt.tokens import AccessToken

        token = AccessToken.for_user(admin_user)
        response = client.get(
            f"/api/v1/core/admin/audit-logs/{uuid.uuid4()}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        assert response.status_code == 404

    def test_record_audit_trail(self, client, admin_user, company):
        from rest_framework_simplejwt.tokens import AccessToken

        # Create and update a company to generate audit logs
        set_audit_context(admin_user)
        c = Company.objects.create(name="TrailCo", code="TR")
        c.name = "TrailCo Updated"
        c.save()
        clear_audit_context()

        token = AccessToken.for_user(admin_user)
        response = client.get(
            f"/api/v1/core/admin/audit-logs/model/core.Company/{c.id}/",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        # Should include create log
        actions = [entry["action"] for entry in data]
        assert "create" in actions

    def test_no_create_update_delete_endpoints(self, client, admin_user):
        """Audit logs are immutable — no POST, PUT, DELETE endpoints exposed."""
        from rest_framework_simplejwt.tokens import AccessToken

        token = AccessToken.for_user(admin_user)
        # POST should 404 (not registered)
        response = client.post(
            "/api/v1/core/admin/audit-logs/",
            data={},
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        assert response.status_code in (404, 405)

        # PUT should 404
        response = client.put(
            f"/api/v1/core/admin/audit-logs/{uuid.uuid4()}/",
            data={},
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        assert response.status_code in (404, 405)
