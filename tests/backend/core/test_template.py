"""Tests for T009c — Industry Template Engine."""

import pytest
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import AccessToken

from apps.core.models import (
    Company,
    IndustryTemplate,
    IndustryTemplateInstallation,
    Menu,
    PageConfig,
)
from apps.core.services.template_service import (
    export_template,
    get_all_templates,
    get_installed_templates,
    get_template,
    import_template,
    install_template,
    preview_installation,
    uninstall_template,
)

User = get_user_model()

SAMPLE_TEMPLATE = {
    "name": "Property Management",
    "code": "property",
    "version": "1.0.0",
    "description": "Lease management, tenant management, utility billing",
    "module_dependencies": [],
    "menu_items": [
        {
            "name": "Properties",
            "slug": "properties",
            "icon": "building",
            "sort_order": 1,
            "children": [
                {
                    "name": "Property Register",
                    "slug": "property-register",
                    "url": "/property/register",
                    "icon": "list",
                    "sort_order": 1,
                },
                {
                    "name": "Units",
                    "slug": "property-units",
                    "url": "/property/units",
                    "icon": "grid",
                    "sort_order": 2,
                },
            ],
        },
    ],
    "page_configs": [
        {
            "page_key": "property_register",
            "page_title": "Property Register",
            "page_type": "list",
            "module": "property",
        },
    ],
    "workflow_config": [],
    "gl_account_config": [],
    "report_config": [],
    "seed_data": {"lease_types": ["tenancy", "license"]},
}


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
        first_name="Admin",
        last_name="User",
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
class TestIndustryTemplateModel:
    def test_create_template(self):
        tmpl = IndustryTemplate.objects.create(
            name="Retail", code="retail", description="Retail setup"
        )
        assert tmpl.code == "retail"
        assert tmpl.template_version == "1.0.0"
        assert tmpl.is_active is True
        assert str(tmpl) == "Retail v1.0.0"

    def test_template_with_config(self):
        tmpl = IndustryTemplate.objects.create(
            name="Property",
            code="property",
            menu_config=[{"name": "Properties", "slug": "properties"}],
            seed_data={"lease_types": ["tenancy"]},
        )
        assert len(tmpl.menu_config) == 1
        assert tmpl.seed_data["lease_types"] == ["tenancy"]


@pytest.mark.django_db
class TestInstallationModel:
    def test_create_installation(self, company):
        tmpl = IndustryTemplate.objects.create(name="Test", code="test")
        inst = IndustryTemplateInstallation.objects.create(
            template=tmpl,
            company=company,
            installed_by=None,
        )
        assert inst.status == "active"
        assert inst.template.code == "test"


# ---------------------------------------------------------------------------
# Service Tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestTemplateService:
    def test_get_all_templates_empty(self):
        assert get_all_templates() == []

    def test_get_all_templates(self):
        IndustryTemplate.objects.create(name="A", code="a")
        IndustryTemplate.objects.create(name="B", code="b")
        assert len(get_all_templates()) == 2

    def test_get_template(self):
        IndustryTemplate.objects.create(name="A", code="a")
        tmpl = get_template("a")
        assert tmpl is not None
        assert tmpl.code == "a"

    def test_get_template_not_found(self):
        assert get_template("nope") is None

    def test_import_template(self):
        tmpl = import_template(SAMPLE_TEMPLATE)
        assert tmpl.code == "property"
        assert tmpl.name == "Property Management"
        assert len(tmpl.menu_config) == 1

    def test_import_template_update_existing(self):
        import_template(SAMPLE_TEMPLATE)
        updated = dict(SAMPLE_TEMPLATE)
        updated["version"] = "2.0.0"
        tmpl = import_template(updated)
        # template_version maps from "version" in JSON
        assert tmpl.template_version == "2.0.0"

    def test_export_template(self):
        import_template(SAMPLE_TEMPLATE)
        data = export_template("property")
        assert data is not None
        assert data["name"] == "Property Management"
        assert len(data["menu_items"]) == 1

    def test_export_template_not_found(self):
        assert export_template("nope") is None

    def test_preview(self):
        import_template(SAMPLE_TEMPLATE)
        preview = preview_installation("property")
        assert preview["code"] == "property"
        assert preview["menu_count"] == 1
        assert preview["page_config_count"] == 1
        assert preview["has_seed_data"] is True

    def test_preview_not_found(self):
        result = preview_installation("nope")
        assert "error" in result

    def test_install_creates_menus(self, company):
        import_template(SAMPLE_TEMPLATE)
        tmpl = IndustryTemplate.objects.get(code="property")

        result = install_template(tmpl.id, company.id)

        assert result["status"] == "active"
        assert result["menu_created"] == 1
        assert Menu.objects.filter(slug="property-register").exists() is True
        assert Menu.objects.filter(slug="property-units").exists() is True

    def test_install_creates_page_configs(self, company):
        import_template(SAMPLE_TEMPLATE)
        tmpl = IndustryTemplate.objects.get(code="property")

        install_template(tmpl.id, company.id)

        assert PageConfig.objects.filter(page_key="property_register").exists() is True

    def test_install_creates_installation_record(self, company):
        import_template(SAMPLE_TEMPLATE)
        tmpl = IndustryTemplate.objects.get(code="property")

        install_template(tmpl.id, company.id)

        assert (
            IndustryTemplateInstallation.objects.filter(
                template=tmpl, company=company, status="active"
            ).exists()
            is True
        )

    def test_uninstall_deactivates_menus(self, company):
        import_template(SAMPLE_TEMPLATE)
        tmpl = IndustryTemplate.objects.get(code="property")
        install_template(tmpl.id, company.id)

        uninstall_template(tmpl.id, company.id)

        assert Menu.objects.get(slug="property-register").is_active is False
        inst = IndustryTemplateInstallation.objects.get(template=tmpl, company=company)
        assert inst.status == "uninstalled"

    def test_uninstall_not_installed_raises(self, company):
        tmpl = IndustryTemplate.objects.create(name="X", code="x")
        with pytest.raises(ValueError, match="not installed"):
            uninstall_template(tmpl.id, company.id)

    def test_install_with_missing_module_dependency(self, company):
        IndustryTemplate.objects.create(
            name="Needy",
            code="needy",
            module_dependencies=["not_a_real_module"],
        )
        tmpl = IndustryTemplate.objects.get(code="needy")
        with pytest.raises(ValueError, match="not registered"):
            install_template(tmpl.id, company.id)

    def test_get_installed_templates(self, company):
        import_template(SAMPLE_TEMPLATE)
        tmpl = IndustryTemplate.objects.get(code="property")
        install_template(tmpl.id, company.id)

        installed = get_installed_templates(company.id)
        assert len(installed) == 1
        assert installed[0].template.code == "property"

    def test_import_template_then_install_with_valid_module_dep(self, company):
        """Verify a template with a KNOWN module dependency can install."""
        from apps.core.platform.module_registry import registry as mod_registry

        mod_registry.register_module({"name": "Finance", "code": "finance"})

        IndustryTemplate.objects.create(
            name="Finance Template",
            code="fin_tmpl",
            module_dependencies=["finance"],
            menu_config=[{"name": "Finance Menu", "slug": "finance-menu"}],
        )
        tmpl = IndustryTemplate.objects.get(code="fin_tmpl")
        result = install_template(tmpl.id, company.id)
        assert result["status"] == "active"


# ---------------------------------------------------------------------------
# API Tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
class TestTemplateAPI:
    def test_list_templates_empty(self, auth_client):
        response = auth_client.get("/api/v1/core/platform/templates/")
        assert response.status_code == 200
        assert response.json() == []

    def test_list_templates(self, auth_client):
        import_template(SAMPLE_TEMPLATE)
        response = auth_client.get("/api/v1/core/platform/templates/")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["code"] == "property"

    def test_get_template_detail(self, auth_client):
        import_template(SAMPLE_TEMPLATE)
        response = auth_client.get("/api/v1/core/platform/templates/property/")
        assert response.status_code == 200
        assert response.json()["name"] == "Property Management"

    def test_get_template_not_found(self, auth_client):
        response = auth_client.get("/api/v1/core/platform/templates/nope/")
        assert response.status_code == 404

    def test_preview(self, auth_client):
        import_template(SAMPLE_TEMPLATE)
        response = auth_client.get("/api/v1/core/platform/templates/property/preview/")
        assert response.status_code == 200
        assert response.json()["code"] == "property"

    def test_export(self, auth_client):
        import_template(SAMPLE_TEMPLATE)
        response = auth_client.get("/api/v1/core/platform/templates/property/export/")
        assert response.status_code == 200
        assert response.json()["name"] == "Property Management"

    def test_install(self, auth_client, company):
        import_template(SAMPLE_TEMPLATE)
        response = auth_client.post(
            "/api/v1/core/platform/templates/property/install/",
            content_type="application/json",
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "active"
        assert data["template_code"] == "property"

    def test_install_then_uninstall(self, auth_client, company):
        import_template(SAMPLE_TEMPLATE)
        auth_client.post(
            "/api/v1/core/platform/templates/property/install/",
            content_type="application/json",
        )
        response = auth_client.post(
            "/api/v1/core/platform/templates/property/uninstall/",
            content_type="application/json",
        )
        assert response.status_code == 200
        assert response.json()["status"] == "uninstalled"

    def test_uninstall_not_installed(self, auth_client):
        import_template(SAMPLE_TEMPLATE)
        response = auth_client.post(
            "/api/v1/core/platform/templates/property/uninstall/",
            content_type="application/json",
        )
        assert response.status_code == 400

    def test_install_requires_superuser(self, client, company):
        user = User.objects.create_user(email="regular@test.com", password="pass123")
        token = AccessToken.for_user(user)
        client.defaults["HTTP_AUTHORIZATION"] = f"Bearer {token}"
        client.defaults["HTTP_X_COMPANY_ID"] = str(company.id)

        import_template(SAMPLE_TEMPLATE)
        response = client.post(
            "/api/v1/core/platform/templates/property/install/",
            content_type="application/json",
        )
        assert response.status_code == 403

    def test_import_requires_superuser(self, client, company):
        user = User.objects.create_user(email="regular2@test.com", password="pass123")
        token = AccessToken.for_user(user)
        client.defaults["HTTP_AUTHORIZATION"] = f"Bearer {token}"
        client.defaults["HTTP_X_COMPANY_ID"] = str(company.id)

        response = client.post(
            "/api/v1/core/platform/templates/import/",
            data={
                "name": "X",
                "code": "x",
                "version": "1.0.0",
                "description": "",
                "module_dependencies": [],
                "menu_items": [],
                "page_configs": [],
                "workflow_config": [],
                "gl_account_config": [],
                "report_config": [],
                "seed_data": {},
            },
            content_type="application/json",
        )
        assert response.status_code == 403

    def test_import_template_via_api(self, auth_client):
        payload = {
            "name": "Retail",
            "code": "retail",
            "version": "1.0.0",
            "description": "Retail template",
            "module_dependencies": [],
            "menu_items": [],
            "page_configs": [],
            "workflow_config": [],
            "gl_account_config": [],
            "report_config": [],
            "seed_data": {},
        }
        response = auth_client.post(
            "/api/v1/core/platform/templates/import/",
            data=payload,
            content_type="application/json",
        )
        assert response.status_code == 200
        assert response.json()["code"] == "retail"

    def test_list_installed(self, auth_client, company):
        import_template(SAMPLE_TEMPLATE)
        auth_client.post(
            "/api/v1/core/platform/templates/property/install/",
            content_type="application/json",
        )
        response = auth_client.get("/api/v1/core/platform/templates/installed/")
        assert response.status_code == 200
        assert len(response.json()) == 1
        assert response.json()[0]["template_code"] == "property"
