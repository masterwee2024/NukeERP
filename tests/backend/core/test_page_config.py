"""Tests for the page config system."""

import pytest

from apps.core.models import PageConfig, PageConfigField
from apps.core.services import page_config_service


@pytest.fixture
def sample_config(db):
    """Create a sample page config."""
    return PageConfig.objects.create(
        page_key="test-page",
        page_title="Test Page",
        page_type="list",
        module="financial",
        entity_model="TestModel",
    )


@pytest.fixture
def config_with_fields(db, sample_config):
    """Create a page config with fields."""
    PageConfigField.objects.create(
        page_config=sample_config,
        field_name="name",
        label="Name",
        field_type="text",
        required=True,
        sort_order=1,
        is_column=True,
    )
    PageConfigField.objects.create(
        page_config=sample_config,
        field_name="email",
        label="Email",
        field_type="email",
        sort_order=2,
        is_column=True,
    )
    return sample_config


# --- Model Tests ---


@pytest.mark.django_db
class TestPageConfigModel:
    def test_str(self, sample_config):
        assert str(sample_config) == "test-page (list)"

    def test_page_key_unique(self, sample_config):
        from django.db import IntegrityError

        with pytest.raises(IntegrityError):
            PageConfig.objects.create(
                page_key="test-page",
                page_title="Duplicate",
                page_type="form",
                module="test",
            )


@pytest.mark.django_db
class TestPageConfigFieldModel:
    def test_str(self, sample_config):
        field = PageConfigField.objects.create(
            page_config=sample_config,
            field_name="email",
            label="Email",
            field_type="email",
        )
        assert str(field) == "test-page.email"


# --- Service Tests ---


@pytest.mark.django_db
class TestPageConfigService:
    def test_get_page_config(self, config_with_fields):
        config = page_config_service.get_page_config("test-page")
        assert config is not None
        assert config.page_key == "test-page"
        assert config.fields.count() == 2

    def test_get_nonexistent_config(self):
        config = page_config_service.get_page_config("nonexistent")
        assert config is None

    def test_list_page_configs(self, sample_config):
        configs = page_config_service.list_page_configs()
        assert len(configs) == 1
        assert configs[0].page_key == "test-page"

    def test_list_by_module(self, sample_config):
        configs = page_config_service.list_page_configs(module="financial")
        assert len(configs) == 1

        configs = page_config_service.list_page_configs(module="scm")
        assert len(configs) == 0

    def test_create_page_config(self):
        config = page_config_service.create_page_config(
            {
                "page_key": "new-page",
                "page_title": "New Page",
                "page_type": "form",
                "module": "test",
            }
        )
        assert config.page_key == "new-page"
        assert PageConfig.objects.filter(page_key="new-page").exists()

    def test_update_page_config(self, sample_config):
        config = page_config_service.update_page_config(
            "test-page", {"page_title": "Updated Title"}
        )
        assert config.page_title == "Updated Title"

    def test_delete_page_config(self, sample_config):
        page_config_service.delete_page_config("test-page")
        assert not PageConfig.objects.filter(page_key="test-page").exists()

    def test_add_field(self, sample_config):
        field = page_config_service.add_field(
            "test-page",
            {"field_name": "phone", "label": "Phone", "field_type": "text"},
        )
        assert field.field_name == "phone"
        assert sample_config.fields.count() == 1

    def test_remove_field(self, config_with_fields):
        field = config_with_fields.fields.first()
        page_config_service.remove_field("test-page", str(field.id))
        assert config_with_fields.fields.count() == 1

    def test_clone_config(self, config_with_fields):
        new_config = page_config_service.clone_config("test-page", "cloned-page")
        assert new_config.page_key == "cloned-page"
        assert new_config.page_title == "Test Page (Copy)"
        assert new_config.fields.count() == 2

        # Verify fields are independent copies
        original_field = config_with_fields.fields.first()
        cloned_field = new_config.fields.first()
        assert original_field.id != cloned_field.id
        assert original_field.field_name == cloned_field.field_name

    def test_export_config(self, config_with_fields):
        exported = page_config_service.export_config("test-page")
        assert exported["page_key"] == "test-page"
        assert len(exported["fields"]) == 2

    def test_import_config(self):
        data = {
            "page_key": "imported-page",
            "page_title": "Imported Page",
            "page_type": "form",
            "module": "test",
            "fields": [
                {"field_name": "name", "label": "Name", "field_type": "text"},
            ],
        }
        config = page_config_service.import_config(data)
        assert config.page_key == "imported-page"
        assert config.fields.count() == 1


# --- API Tests ---


@pytest.mark.django_db
class TestPageConfigAPI:
    def _jwt_auth(self, client, user):
        from rest_framework_simplejwt.tokens import AccessToken

        token = AccessToken.for_user(user)
        client.defaults["HTTP_AUTHORIZATION"] = f"Bearer {token}"

    def test_list_configs(self, client, admin_user):
        self._jwt_auth(client, admin_user)
        response = client.get("/api/v1/core/page-configs/")
        assert response.status_code == 200

    def test_get_config(self, client, admin_user, sample_config):
        self._jwt_auth(client, admin_user)
        response = client.get(f"/api/v1/core/page-configs/{sample_config.page_key}/")
        assert response.status_code == 200
        assert response.json()["page_key"] == "test-page"

    def test_create_config(self, client, admin_user):
        self._jwt_auth(client, admin_user)
        response = client.post(
            "/api/v1/core/page-configs/",
            {
                "page_key": "api-test",
                "page_title": "API Test",
                "page_type": "form",
                "module": "test",
            },
            content_type="application/json",
        )
        assert response.status_code == 200
        assert PageConfig.objects.filter(page_key="api-test").exists()

    def test_delete_config(self, client, admin_user, sample_config):
        self._jwt_auth(client, admin_user)
        response = client.delete(f"/api/v1/core/page-configs/{sample_config.page_key}/")
        assert response.status_code == 204
        assert not PageConfig.objects.filter(page_key="test-page").exists()
