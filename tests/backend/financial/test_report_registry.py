"""Tests for ReportDefinition, ReportParameter, ReportExport CRUD."""

import uuid
from datetime import timedelta

import pytest
from django.db import IntegrityError
from django.utils import timezone

from apps.financial.models import ReportDefinition, ReportExport, ReportParameter


@pytest.mark.django_db
class TestReportDefinition:
    def test_create_report_definition(self):
        report = ReportDefinition.objects.create(
            code="test_report",
            name="Test Report",
            module="financial",
            compute_type="sql",
            sql_template="SELECT 1",
        )
        assert report.code == "test_report"
        assert report.is_active is True
        assert report.page_size == 100

    def test_update_report_definition(self):
        report = ReportDefinition.objects.create(
            code="test_report",
            name="Test Report",
            module="financial",
            compute_type="sql",
        )
        report.name = "Updated Report"
        report.save()
        report.refresh_from_db()
        assert report.name == "Updated Report"

    def test_delete_report_definition(self):
        report = ReportDefinition.objects.create(
            code="to_delete",
            name="To Delete",
            module="financial",
            compute_type="sql",
        )
        pk = report.pk
        report.delete()
        assert not ReportDefinition.objects.filter(pk=pk).exists()


@pytest.mark.django_db
class TestReportParameter:
    def test_create_parameter(self):
        report = ReportDefinition.objects.create(
            code="param_test",
            name="Param Test",
            module="financial",
            compute_type="sql",
        )
        param = ReportParameter.objects.create(
            report=report,
            key="period_from",
            label="Period From",
            param_type="period",
            required=True,
            sort_order=1,
        )
        assert param.key == "period_from"
        assert param.required is True

    def test_parameter_ordering(self):
        report = ReportDefinition.objects.create(
            code="order_test",
            name="Order Test",
            module="financial",
            compute_type="sql",
        )
        p1 = ReportParameter.objects.create(
            report=report, key="second", label="Second", param_type="text", sort_order=2
        )
        p2 = ReportParameter.objects.create(
            report=report, key="first", label="First", param_type="text", sort_order=1
        )
        params = list(ReportParameter.objects.filter(report=report))
        assert params == [p2, p1]

    def test_unique_together(self):
        report = ReportDefinition.objects.create(
            code="unique_test",
            name="Unique Test",
            module="financial",
            compute_type="sql",
        )
        ReportParameter.objects.create(
            report=report, key="test_key", label="Test", param_type="text"
        )
        with pytest.raises(IntegrityError):
            ReportParameter.objects.create(
                report=report, key="test_key", label="Test", param_type="text"
            )


@pytest.mark.django_db
class TestReportExport:
    def test_create_export(self, db):
        from django.contrib.auth import get_user_model

        from apps.core.models import Company

        User = get_user_model()
        user = User.objects.create_user(
            email="export@test.com", password="test123", full_name="Export User"
        )
        company = Company.objects.create(name="Export Co", code="EC")

        report = ReportDefinition.objects.create(
            code="export_test",
            name="Export Test",
            module="financial",
            compute_type="sql",
        )
        export = ReportExport.objects.create(
            report=report,
            user=user,
            company=company,
            format="csv",
            params={"period_from": str(uuid.uuid4())},
            status="generating",
            expires_at=timezone.now() + timedelta(days=1),
        )
        assert export.status == "generating"
        assert export.format == "csv"

    def test_export_company_scoped(self, db):
        from django.contrib.auth import get_user_model

        from apps.core.models import Company

        User = get_user_model()
        user = User.objects.create_user(
            email="scope@test.com", password="test123", full_name="Scope User"
        )
        company_a = Company.objects.create(name="Company A", code="CA")
        company_b = Company.objects.create(name="Company B", code="CB")

        report = ReportDefinition.objects.create(
            code="scope_test",
            name="Scope Test",
            module="financial",
            compute_type="sql",
        )
        ReportExport.objects.create(
            report=report,
            user=user,
            company=company_a,
            format="pdf",
            params={},
            status="generating",
            expires_at=timezone.now() + timedelta(days=1),
        )
        assert ReportExport.objects.filter(company=company_a).count() == 1
        assert ReportExport.objects.filter(company=company_b).count() == 0
