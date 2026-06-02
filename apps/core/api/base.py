"""Base CRUD mixin for Django Ninja APIs with pagination, sorting, filtering."""

from typing import Any
from uuid import UUID

from django.db import models
from django.db.models import QuerySet
from ninja import Field, Router, Schema
from ninja.errors import HttpError

from apps.core.models import ConcurrencyError


class PaginationSchema(Schema):
    """Pagination parameters."""

    page: int = Field(1, ge=1)
    page_size: int = Field(25, ge=1, le=100)


class PaginatedResponse(Schema):
    """Paginated response format."""

    count: int
    results: list[Any]


class SortMixin:
    """Mixin for sorting querysets."""

    def apply_sorting(self, queryset: QuerySet, sort_by: str | None) -> QuerySet:
        if not sort_by:
            return queryset.order_by("-created_at")

        fields = [f.strip() for f in sort_by.split(",")]
        order_fields = []
        for field in fields:
            if field.startswith("-"):
                order_fields.append(f"-{field[1:]}")
            else:
                order_fields.append(field)

        return queryset.order_by(*order_fields)


class FilterMixin:
    """Mixin for filtering querysets."""

    def apply_filters(self, queryset: QuerySet, filters: dict[str, Any]) -> QuerySet:
        for key, value in filters.items():
            if value is None or value == "":
                continue

            if key.startswith("search"):
                # Global search across multiple fields
                continue

            if key.endswith("_from"):
                field = key[:-5]
                queryset = queryset.filter(**{f"{field}__gte": value})
            elif key.endswith("_to"):
                field = key[:-3]
                queryset = queryset.filter(**{f"{field}__lte": value})
            elif key == "is_active":
                queryset = queryset.filter(is_active=value)
            else:
                queryset = queryset.filter(**{key: value})

        return queryset


class BaseCRUDRouter(SortMixin, FilterMixin):
    """Base CRUD router with pagination, sorting, filtering, and concurrency control."""

    def __init__(
        self,
        model: type[models.Model],
        schema_out: type,
        schema_create: type,
        schema_update: type,
    ):
        self.model = model
        self.schema_out = schema_out
        self._schema_create = schema_create
        self._schema_update = schema_update
        self.router = Router()

        # Register routes
        self.router.get("/", response=PaginatedResponse)(self.list_view)
        self.router.post("/", response=schema_out, status_code=201)(self.create_view)
        self.router.get("/{id}/", response=schema_out)(self.detail_view)
        self.router.put("/{id}/", response=schema_out)(self.update_view)
        self.router.delete("/{id}/", status_code=204)(self.delete_view)

    def get_queryset(self, request) -> QuerySet:
        """Override to customize queryset (e.g., filter by company)."""
        return self.model.objects.all()

    def list_view(
        self,
        request,
        page: int = 1,
        page_size: int = 25,
        sort: str | None = None,
        **filters,
    ):
        """List items with pagination, sorting, and filtering."""
        queryset = self.get_queryset(request)
        queryset = self.apply_filters(queryset, filters)
        queryset = self.apply_sorting(queryset, sort)

        total = queryset.count()
        start = (page - 1) * page_size
        end = start + page_size
        items = queryset[start:end]

        return {
            "count": total,
            "results": [self.schema_out.model_validate(item) for item in items],
        }

    def create_view(self, request, data):
        """Create a new item."""
        item = self.model.objects.create(**data.model_dump())
        return item

    def detail_view(self, request, id: UUID):
        """Get item by ID."""
        try:
            return self.model.objects.get(id=id)
        except self.model.DoesNotExist:
            raise HttpError(404, "Not found") from None

    def update_view(self, request, id: UUID, data):
        """Update item with optimistic locking."""
        try:
            item = self.model.objects.get(id=id)
        except self.model.DoesNotExist:
            raise HttpError(404, "Not found") from None

        # Validate updated_at if provided (optimistic lock)
        if hasattr(data, "updated_at") and data.updated_at:
            if item.updated_at != data.updated_at:
                raise HttpError(
                    409,
                    "Record was modified by another user. Please reload and try again.",
                )

        # Apply updates
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if field != "updated_at":
                setattr(item, field, value)

        try:
            item.save()  # version auto-increments via ConcurrencyModel
        except ConcurrencyError as e:
            raise HttpError(409, str(e)) from e

        return item

    def delete_view(self, request, id: UUID):
        """Delete item."""
        try:
            item = self.model.objects.get(id=id)
            item.delete()
        except self.model.DoesNotExist:
            raise HttpError(404, "Not found") from None
