"""Page config service — business logic for page configuration management."""

from typing import Any

from django.db import transaction
from django.db.models import Prefetch

from apps.core.models import PageConfig, PageConfigField


def get_page_config(page_key: str) -> PageConfig | None:
    """Return config with all fields sorted by sort_order."""
    try:
        return PageConfig.objects.prefetch_related(
            Prefetch(
                "fields",
                queryset=PageConfigField.objects.order_by("sort_order", "field_name"),
            )
        ).get(page_key=page_key)
    except PageConfig.DoesNotExist:
        return None


def list_page_configs(module: str | None = None) -> list[PageConfig]:
    """List all page configs, optionally filtered by module."""
    qs = PageConfig.objects.filter(is_active=True)
    if module:
        qs = qs.filter(module=module)
    return list(qs.order_by("module", "page_key"))


def create_page_config(data: dict[str, Any]) -> PageConfig:
    """Create a new page config."""
    return PageConfig.objects.create(**data)


def update_page_config(page_key: str, data: dict[str, Any]) -> PageConfig:
    """Update an existing page config."""
    config = PageConfig.objects.get(page_key=page_key)
    for key, value in data.items():
        config.set_field(key, value)
    config.save()
    return config


def delete_page_config(page_key: str) -> None:
    """Delete a page config and all its fields."""
    PageConfig.objects.get(page_key=page_key).delete()


def add_field(page_key: str, field_data: dict[str, Any]) -> PageConfigField:
    """Add a field to a page config."""
    config = PageConfig.objects.get(page_key=page_key)
    return PageConfigField.objects.create(page_config=config, **field_data)


def update_field(
    page_key: str, field_id: str, field_data: dict[str, Any]
) -> PageConfigField:
    """Update a field on a page config."""
    field = PageConfigField.objects.get(id=field_id, page_config__page_key=page_key)
    for key, value in field_data.items():
        setattr(field, key, value)
    field.save()
    return field


def remove_field(page_key: str, field_id: str) -> None:
    """Remove a field from a page config."""
    PageConfigField.objects.get(id=field_id, page_config__page_key=page_key).delete()


def clone_config(page_key: str, new_page_key: str) -> PageConfig:
    """Deep clone a page config with all fields."""
    original = PageConfig.objects.get(page_key=page_key)

    with transaction.atomic():
        new_config = PageConfig.objects.create(
            page_key=new_page_key,
            page_title=f"{original.page_title} (Copy)",
            page_type=original.page_type,
            module=original.module,
            entity_model=original.entity_model,
            api_endpoint=original.api_endpoint,
            layout=original.layout,
            desktop_layout=original.desktop_layout,
            mobile_layout=original.mobile_layout,
            list_mobile_view=original.list_mobile_view,
            mobile_group_by=original.mobile_group_by,
            actions=original.actions,
            breadcrumbs=original.breadcrumbs,
            page_size=original.page_size,
            sort_default=original.sort_default,
            sort_direction=original.sort_direction,
        )

        # Clone all fields
        fields = PageConfigField.objects.filter(page_config=original)
        for field in fields:
            PageConfigField.objects.create(
                page_config=new_config,
                field_name=field.field_name,
                label=field.label,
                placeholder=field.placeholder,
                help_text=field.help_text,
                field_type=field.field_type,
                data_type=field.data_type,
                required=field.required,
                readonly=field.readonly,
                hidden=field.hidden,
                disabled=field.disabled,
                default_value=field.default_value,
                sort_order=field.sort_order,
                group_name=field.group_name,
                col_span=field.col_span,
                width=field.width,
                show_on_desktop=field.show_on_desktop,
                show_on_mobile=field.show_on_mobile,
                desktop_col_span=field.desktop_col_span,
                mobile_col_span=field.mobile_col_span,
                mobile_render_as=field.mobile_render_as,
                min_length=field.min_length,
                max_length=field.max_length,
                min_value=field.min_value,
                max_value=field.max_value,
                pattern=field.pattern,
                custom_validator=field.custom_validator,
                options_source=field.options_source,
                options=field.options,
                options_api=field.options_api,
                options_label_field=field.options_label_field,
                options_value_field=field.options_value_field,
                option_group_by=field.option_group_by,
                related_entity=field.related_entity,
                related_display=field.related_display,
                related_search=field.related_search,
                related_fields=field.related_fields,
                show_when=field.show_when,
                depends_on=field.depends_on,
                is_column=field.is_column,
                column_order=field.column_order,
                column_width=field.column_width,
                column_align=field.column_align,
                sortable=field.sortable,
                filterable=field.filterable,
                searchable=field.searchable,
                aggregate=field.aggregate,
                render_as=field.render_as,
                line_entity=field.line_entity,
                line_fields=field.line_fields,
                permission_read=field.permission_read,
                permission_write=field.permission_write,
                icon=field.icon,
                prefix=field.prefix,
                suffix=field.suffix,
                format=field.format,
                badge_color=field.badge_color,
                css_class=field.css_class,
            )

    return new_config


def export_config(page_key: str) -> dict[str, Any]:
    """Export a page config as JSON."""
    config = PageConfig.objects.get(page_key=page_key)
    fields = PageConfigField.objects.filter(page_config=config).order_by("sort_order")

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
                "field_name": f.field_name,
                "label": f.label,
                "placeholder": f.placeholder,
                "help_text": f.help_text,
                "field_type": f.field_type,
                "data_type": f.data_type,
                "required": f.required,
                "readonly": f.readonly,
                "hidden": f.hidden,
                "disabled": f.disabled,
                "default_value": f.default_value,
                "sort_order": f.sort_order,
                "group_name": f.group_name,
                "col_span": f.col_span,
                "width": f.width,
                "show_on_desktop": f.show_on_desktop,
                "show_on_mobile": f.show_on_mobile,
                "desktop_col_span": f.desktop_col_span,
                "mobile_col_span": f.mobile_col_span,
                "mobile_render_as": f.mobile_render_as,
                "options_source": f.options_source,
                "options": f.options,
                "is_column": f.is_column,
                "column_order": f.column_order,
                "sortable": f.sortable,
                "filterable": f.filterable,
                "searchable": f.searchable,
            }
            for f in fields
        ],
    }


def import_config(data: dict[str, Any]) -> PageConfig:
    """Import a page config from JSON."""
    fields_data = data.pop("fields", [])

    with transaction.atomic():
        config = PageConfig.objects.create(**data)
        for field_data in fields_data:
            PageConfigField.objects.create(page_config=config, **field_data)

    return config
