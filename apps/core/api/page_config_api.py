"""Page config API endpoints."""

from typing import Any

from django.http import HttpResponse
from ninja import Router, Schema
from ninja.errors import HttpError

from apps.core.services import page_config_service

router = Router()


# --- Schemas ---


class PageConfigCreateSchema(Schema):
    page_key: str
    page_title: str
    page_type: str
    module: str
    entity_model: str = ""
    api_endpoint: str = ""
    layout: str = "single"
    desktop_layout: str = "single"
    mobile_layout: str = "single"
    list_mobile_view: str = "card"
    mobile_group_by: str = ""
    actions: list = []
    breadcrumbs: list = []
    page_size: int = 25
    sort_default: str = ""
    sort_direction: str = "asc"


class PageConfigUpdateSchema(Schema):
    page_title: str | None = None
    page_type: str | None = None
    module: str | None = None
    entity_model: str | None = None
    api_endpoint: str | None = None
    layout: str | None = None
    desktop_layout: str | None = None
    mobile_layout: str | None = None
    list_mobile_view: str | None = None
    mobile_group_by: str | None = None
    actions: list | None = None
    breadcrumbs: list | None = None
    page_size: int | None = None
    sort_default: str | None = None
    sort_direction: str | None = None
    is_active: bool | None = None


class PageConfigFieldCreateSchema(Schema):
    field_name: str
    label: str
    placeholder: str = ""
    help_text: str = ""
    field_type: str
    data_type: str = ""
    required: bool = False
    readonly: bool = False
    hidden: bool = False
    disabled: bool = False
    default_value: str = ""
    sort_order: int = 0
    group_name: str = ""
    col_span: int = 1
    width: str = "full"
    show_on_desktop: bool = True
    show_on_mobile: bool = True
    desktop_col_span: int = 1
    mobile_col_span: int = 12
    mobile_render_as: str = "text"
    options_source: str = ""
    options: list = []
    is_column: bool = False
    column_order: int = 0
    sortable: bool = False
    filterable: bool = False
    searchable: bool = False
    render_as: str = ""
    icon: str = ""
    prefix: str = ""
    suffix: str = ""
    format: str = ""
    css_class: str = ""


class PageConfigFieldUpdateSchema(Schema):
    label: str | None = None
    placeholder: str | None = None
    help_text: str | None = None
    field_type: str | None = None
    required: bool | None = None
    readonly: bool | None = None
    hidden: bool | None = None
    disabled: bool | None = None
    default_value: str | None = None
    sort_order: int | None = None
    col_span: int | None = None
    show_on_desktop: bool | None = None
    show_on_mobile: bool | None = None
    desktop_col_span: int | None = None
    mobile_col_span: int | None = None
    is_column: bool | None = None
    sortable: bool | None = None
    filterable: bool | None = None
    searchable: bool | None = None


class ImportConfigSchema(Schema):
    config: dict[str, Any]


# --- Endpoints ---


@router.get("/")
def list_configs(request, module: str | None = None):
    """List all page configs."""
    configs = page_config_service.list_page_configs(module)
    return [
        {
            "page_key": c.page_key,
            "page_title": c.page_title,
            "page_type": c.page_type,
            "module": c.module,
            "is_active": c.is_active,
        }
        for c in configs
    ]


@router.post("/")
def create_config(request, data: PageConfigCreateSchema):
    """Create a page config."""
    config = page_config_service.create_page_config(data.model_dump())
    return {"page_key": config.page_key, "page_title": config.page_title}


@router.get("/{page_key}/")
def get_config(request, page_key: str):
    """Get a page config with all fields."""
    config = page_config_service.get_page_config(page_key)
    if not config:
        raise HttpError(404, "Page config not found")

    return {
        "page_key": config.page_key,
        "page_title": config.page_title,
        "page_type": config.page_type,
        "module": config.module,
        "entity_model": config.entity_model,
        "api_endpoint": config.api_endpoint,
        "layout": config.layout,
        "desktop_layout": config.desktop_layout,
        "mobile_layout": config.mobile_layout,
        "list_mobile_view": config.list_mobile_view,
        "mobile_group_by": config.mobile_group_by,
        "actions": config.actions,
        "breadcrumbs": config.breadcrumbs,
        "page_size": config.page_size,
        "sort_default": config.sort_default,
        "sort_direction": config.sort_direction,
        "fields": [
            {
                "id": str(f.id),
                "field_name": f.field_name,
                "label": f.label,
                "field_type": f.field_type,
                "required": f.required,
                "readonly": f.readonly,
                "show_on_desktop": f.show_on_desktop,
                "show_on_mobile": f.show_on_mobile,
                "sort_order": f.sort_order,
            }
            for f in config.fields.all()
        ],
    }


@router.put("/{page_key}/")
def update_config(request, page_key: str, data: PageConfigUpdateSchema):
    """Update a page config."""
    update_data = data.model_dump(exclude_unset=True)
    if not update_data:
        raise HttpError(400, "No fields to update")
    return page_config_service.update_page_config(page_key, update_data)


@router.delete("/{page_key}/")
def delete_config(request, page_key: str):
    """Delete a page config."""
    page_config_service.delete_page_config(page_key)
    return HttpResponse(status=204)


# --- Field endpoints ---


@router.post(
    "/{page_key}/fields/",
)
def add_field(request, page_key: str, data: PageConfigFieldCreateSchema):
    """Add a field to a page config."""
    return page_config_service.add_field(page_key, data.model_dump())


@router.put("/{page_key}/fields/{field_id}/")
def update_field(
    request, page_key: str, field_id: str, data: PageConfigFieldUpdateSchema
):
    """Update a field."""
    update_data = data.model_dump(exclude_unset=True)
    if not update_data:
        raise HttpError(400, "No fields to update")
    return page_config_service.update_field(page_key, field_id, update_data)


@router.delete("/{page_key}/fields/{field_id}/")
def delete_field(request, page_key: str, field_id: str):
    """Delete a field."""
    page_config_service.remove_field(page_key, field_id)
    return HttpResponse(status=204)


# --- Clone / Export / Import ---


@router.post(
    "/{page_key}/clone/",
)
def clone_config(request, page_key: str):
    """Clone a page config."""
    new_key = f"{page_key}-copy"
    return page_config_service.clone_config(page_key, new_key)


@router.get("/{page_key}/export/")
def export_config(request, page_key: str):
    """Export a page config as JSON."""
    return page_config_service.export_config(page_key)


@router.post(
    "/import/",
)
def import_config(request, data: ImportConfigSchema):
    """Import a page config from JSON."""
    return page_config_service.import_config(data.config)
