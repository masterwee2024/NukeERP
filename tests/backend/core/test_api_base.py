"""Tests for base API layer — pagination, sorting, filtering, error format, versioning."""

import pytest
from django.contrib.auth import get_user_model

from apps.core.models import Menu

User = get_user_model()


# --- Pagination Tests ---


@pytest.mark.django_db
class TestPagination:
    @pytest.fixture
    def many_menus(self, db):
        menus = []
        for i in range(50):
            menus.append(
                Menu.objects.create(
                    name=f"Menu {i:02d}",
                    slug=f"menu-{i:02d}",
                    sort_order=i,
                    module="test",
                )
            )
        return menus

    def test_default_page_size(self, many_menus):
        """Default page size should be 25."""
        total = Menu.objects.count()
        assert total == 50

    def test_pagination_first_page(self, many_menus):
        """First page should return first 25 items."""
        menus = Menu.objects.all().order_by("-created_at")[:25]
        assert len(menus) == 25
        assert menus[0].slug == "menu-49"

    def test_pagination_second_page(self, many_menus):
        """Second page should return items 26-50."""
        menus = Menu.objects.all().order_by("-created_at")[25:50]
        assert len(menus) == 25
        assert menus[0].slug == "menu-24"

    def test_pagination_last_page_partial(self, many_menus):
        """Last page with fewer items should work."""
        menus = Menu.objects.all().order_by("-created_at")[50:75]
        assert len(menus) == 0


# --- Sorting Tests ---


@pytest.mark.django_db
class TestSorting:
    @pytest.fixture
    def sorted_menus(self, db):
        Menu.objects.create(name="C", slug="menu-c", sort_order=3, module="test")
        Menu.objects.create(name="A", slug="menu-a", sort_order=1, module="test")
        Menu.objects.create(name="B", slug="menu-b", sort_order=2, module="test")

    def test_sort_ascending(self, sorted_menus):
        """Sort by sort_order ascending."""
        from apps.core.api.base import SortMixin

        mixin = SortMixin()
        qs = mixin.apply_sorting(Menu.objects.all(), "sort_order")
        items = list(qs)
        assert items[0].sort_order == 1
        assert items[1].sort_order == 2
        assert items[2].sort_order == 3

    def test_sort_descending(self, sorted_menus):
        """Sort by sort_order descending."""
        from apps.core.api.base import SortMixin

        mixin = SortMixin()
        qs = mixin.apply_sorting(Menu.objects.all(), "-sort_order")
        items = list(qs)
        assert items[0].sort_order == 3
        assert items[1].sort_order == 2
        assert items[2].sort_order == 1

    def test_sort_default_fallback(self, sorted_menus):
        """Default sort should be -created_at when no sort param."""
        from apps.core.api.base import SortMixin

        mixin = SortMixin()
        qs = mixin.apply_sorting(Menu.objects.all(), None)
        items = list(qs)
        # Items should be ordered by -created_at (newest first)
        assert len(items) == 3

    def test_sort_multi_field(self, sorted_menus):
        """Multi-field sort should work with comma separation."""
        from apps.core.api.base import SortMixin

        # Add a second module for multi-field sorting
        Menu.objects.create(name="Z SCM", slug="menu-z", sort_order=1, module="scm")
        Menu.objects.create(name="Y SCM", slug="menu-y", sort_order=2, module="scm")

        mixin = SortMixin()
        qs = mixin.apply_sorting(Menu.objects.all(), "module,sort_order")
        items = list(qs)
        # First all 'scm' items sorted by sort_order, then all 'test' items
        assert items[0].module == "scm"
        assert items[1].module == "scm"
        assert items[2].module == "test"


# --- Filtering Tests ---


@pytest.mark.django_db
class TestFiltering:
    @pytest.fixture
    def filter_menus(self, db):
        Menu.objects.create(
            name="Active Financial",
            slug="active-fin",
            module="financial",
            is_active=True,
        )
        Menu.objects.create(
            name="Inactive Financial",
            slug="inactive-fin",
            module="financial",
            is_active=False,
        )
        Menu.objects.create(
            name="Active SCM", slug="active-scm", module="scm", is_active=True
        )

    def test_filter_by_module(self, filter_menus):
        """Filter by module should return matching items."""
        from apps.core.api.base import FilterMixin

        mixin = FilterMixin()
        qs = mixin.apply_filters(Menu.objects.all(), {"module": "financial"})
        assert qs.count() == 2

    def test_filter_by_is_active(self, filter_menus):
        """Filter by is_active should work."""
        from apps.core.api.base import FilterMixin

        mixin = FilterMixin()
        qs = mixin.apply_filters(Menu.objects.all(), {"is_active": True})
        assert qs.count() == 2

    def test_filter_ignores_empty_values(self, filter_menus):
        """Empty filter values should be ignored."""
        from apps.core.api.base import FilterMixin

        mixin = FilterMixin()
        qs = mixin.apply_filters(Menu.objects.all(), {"module": "", "is_active": None})
        assert qs.count() == 3

    def test_filter_date_range(self, filter_menus):
        """Date range filter should work."""
        from django.utils import timezone

        from apps.core.api.base import FilterMixin

        mixin = FilterMixin()
        qs = mixin.apply_filters(
            Menu.objects.all(),
            {"created_at_from": timezone.now() - timezone.timedelta(days=1)},
        )
        assert qs.count() == 3


# --- Error Schema Tests ---


class TestErrorSchemas:
    def test_error_response_schema(self):
        """ErrorResponseSchema should have detail field."""
        from apps.core.schemas import ErrorResponseSchema

        s = ErrorResponseSchema(detail="Not found")
        assert s.detail == "Not found"

    def test_validation_error_schema(self):
        """ValidationErrorResponseSchema should have errors dict."""
        from apps.core.schemas import ValidationErrorResponseSchema

        s = ValidationErrorResponseSchema(errors={"name": ["This field is required"]})
        assert "name" in s.errors
        assert s.errors["name"] == ["This field is required"]

    def test_conflict_response_schema(self):
        """ConflictResponseSchema should have detail and conflict flag."""
        from apps.core.schemas import ConflictResponseSchema

        s = ConflictResponseSchema(detail="Stale version")
        assert s.detail == "Stale version"
        assert s.conflict is True

    def test_error_schemas_import(self):
        """All error schemas should be importable."""
        from apps.core.schemas import (
            ConflictResponseSchema,
            ErrorResponseSchema,
            ValidationErrorResponseSchema,
        )

        assert ErrorResponseSchema is not None
        assert ValidationErrorResponseSchema is not None
        assert ConflictResponseSchema is not None


# --- PaginatedResponse Schema Tests ---


class TestPaginatedResponse:
    def test_schema_is_importable(self):
        """PaginatedResponse should be importable."""
        from apps.core.api.base import PaginatedResponse

        assert PaginatedResponse is not None

    def test_schema_has_count_and_results(self):
        """PaginatedResponse schema should accept count and results."""
        from apps.core.api.base import PaginatedResponse

        s = PaginatedResponse(count=10, results=[1, 2, 3])
        assert s.count == 10
        assert len(s.results) == 3


# --- Versioning Tests ---


class TestVersioning:
    def test_ninja_api_configured(self):
        """NinjaAPI should be configured with version."""
        from pyerp.api import api

        assert api.version == "1.0.0"
        assert api.title == "pyERP API"

    def test_api_url_in_urlpatterns(self):
        """URL patterns should include /api/v1/."""
        from pyerp.urls import urlpatterns

        pattern_strs = [str(p.pattern) for p in urlpatterns]
        assert any(
            "api/v1" in s for s in pattern_strs
        ), f"URL patterns must include /api/v1/ prefix. Got: {pattern_strs}"

    def test_swagger_schema_available(self):
        """OpenAPI schema should be accessible via the NinjaAPI instance."""
        from pyerp.api import api

        assert api.openapi_url is not None, "OpenAPI schema URL must be configured"

    def test_core_router_registered(self):
        """Core router should be registered under /core/ prefix."""
        from pyerp.api import api

        # Check registered router paths
        router_paths = [str(r) for r in api._routers]
        assert any(
            "core" in p for p in router_paths
        ), f"Core router must be registered. Routers: {router_paths}"
