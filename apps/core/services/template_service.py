"""Industry template service — install, uninstall, preview, import/export."""

from __future__ import annotations

import logging
from uuid import UUID

from django.db import transaction

from apps.core.models import (
    IndustryTemplate,
    IndustryTemplateInstallation,
    Menu,
    PageConfig,
    WorkflowDefinition,
)
from apps.core.platform.module_registry import registry

logger = logging.getLogger(__name__)

TEMPLATE_SEED_DIR = "apps/core/fixtures/templates"


def get_all_templates() -> list[IndustryTemplate]:
    return list(IndustryTemplate.objects.filter(is_active=True))


def get_template(code: str) -> IndustryTemplate | None:
    try:
        return IndustryTemplate.objects.get(code=code, is_active=True)
    except IndustryTemplate.DoesNotExist:
        return None


def get_installed_templates(company_id: UUID) -> list[IndustryTemplateInstallation]:
    return list(
        IndustryTemplateInstallation.objects.filter(
            company_id=company_id, status="active"
        ).select_related("template")
    )


def preview_installation(code: str) -> dict:
    """Return a summary of what will be configured when installing a template."""
    tmpl = get_template(code)
    if tmpl is None:
        return {"error": "Template not found"}

    return {
        "code": tmpl.code,
        "name": tmpl.name,
        "version": tmpl.template_version,
        "description": tmpl.description,
        "menu_count": len(tmpl.menu_config),
        "page_config_count": len(tmpl.page_config),
        "workflow_count": len(tmpl.workflow_config),
        "gl_account_count": len(tmpl.gl_account_config),
        "report_count": len(tmpl.report_config),
        "has_seed_data": bool(tmpl.seed_data),
        "module_dependencies": tmpl.module_dependencies,
    }


@transaction.atomic
def install_template(
    template_id: UUID, company_id: UUID, user_id: UUID | None = None
) -> dict:
    """Install a template for a company — creates menu, page configs, etc."""
    tmpl = IndustryTemplate.objects.select_for_update().get(
        id=template_id, is_active=True
    )

    for dep in tmpl.module_dependencies:
        if registry.get_module(dep) is None:
            raise ValueError(f"Module dependency '{dep}' is not registered")

    _install_menus(tmpl.menu_config)
    _install_page_configs(tmpl.page_config)
    _install_workflows(tmpl.workflow_config, company_id, user_id)
    _install_seed_data(tmpl.seed_data)

    installation, _ = IndustryTemplateInstallation.objects.update_or_create(
        template=tmpl,
        company_id=company_id,
        status="active",
        defaults={
            "installed_by_id": user_id,
            "configuration_overrides": {},
        },
    )

    logger.info(
        "Template '%s' installed for company %s by %s",
        tmpl.code,
        company_id,
        user_id,
    )
    return {
        "template_code": tmpl.code,
        "template_name": tmpl.name,
        "company_id": str(company_id),
        "status": "active",
        "installation_id": str(installation.id),
        "menu_created": len(tmpl.menu_config),
        "page_configs_created": len(tmpl.page_config),
        "workflows_created": len(tmpl.workflow_config),
    }


@transaction.atomic
def uninstall_template(template_id: UUID, company_id: UUID) -> dict:
    """Uninstall a template — deactivate associated configuration."""
    tmpl = IndustryTemplate.objects.get(id=template_id)

    installation = (
        IndustryTemplateInstallation.objects.select_for_update()
        .filter(template=tmpl, company_id=company_id, status="active")
        .first()
    )
    if installation is None:
        raise ValueError("Template is not installed for this company")

    _uninstall_menus(tmpl.menu_config)
    _uninstall_workflows(tmpl.workflow_config, company_id)

    installation.status = "uninstalled"
    installation.save()

    logger.info("Template '%s' uninstalled for company %s", tmpl.code, company_id)
    return {
        "template_code": tmpl.code,
        "company_id": str(company_id),
        "status": "uninstalled",
    }


def export_template(code: str) -> dict | None:
    tmpl = get_template(code)
    if tmpl is None:
        return None
    return {
        "name": tmpl.name,
        "code": tmpl.code,
        "version": tmpl.template_version,
        "description": tmpl.description,
        "module_dependencies": tmpl.module_dependencies,
        "menu_items": tmpl.menu_config,
        "page_configs": tmpl.page_config,
        "workflow_config": tmpl.workflow_config,
        "gl_account_config": tmpl.gl_account_config,
        "report_config": tmpl.report_config,
        "seed_data": tmpl.seed_data,
    }


@transaction.atomic
def import_template(json_data: dict, user_id: UUID | None = None) -> IndustryTemplate:
    """Import a template from JSON data, creating or updating the DB record."""
    code = json_data.get("code", "")
    defaults = {
        "name": json_data.get("name", code),
        "description": json_data.get("description", ""),
        "template_version": json_data.get(
            "version", json_data.get("template_version", "1.0.0")
        ),
        "module_dependencies": json_data.get("module_dependencies", []),
        "menu_config": json_data.get("menu_items", []),
        "page_config": json_data.get("page_configs", []),
        "workflow_config": json_data.get("workflow_config", []),
        "gl_account_config": json_data.get("gl_account_config", []),
        "report_config": json_data.get("report_config", []),
        "seed_data": json_data.get("seed_data", {}),
    }
    tmpl, created = IndustryTemplate.objects.update_or_create(
        code=code,
        defaults=defaults,
    )
    logger.info("Template '%s' %s", code, "created" if created else "updated")
    return tmpl


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _install_menus(menu_config: list[dict]) -> None:
    for item in menu_config:
        parent = None
        if item.get("parent_slug"):
            try:
                parent = Menu.objects.get(slug=item["parent_slug"])
            except Menu.DoesNotExist:
                logger.warning(
                    "Parent menu '%s' not found, creating at root",
                    item.get("parent_slug"),
                )

        children = item.pop("children", [])
        slug = item.get("slug") or item["name"].lower().replace(" ", "-")
        menu, _ = Menu.objects.update_or_create(
            slug=slug,
            defaults={
                "name": item["name"],
                "icon": item.get("icon", ""),
                "url": item.get("url", ""),
                "parent": parent,
                "sort_order": item.get("sort_order", 0),
                "module": item.get("module", ""),
                "level": (parent.level + 1) if parent else 0,
                "is_active": True,
            },
        )
        for child in children:
            child_slug = child.get("slug") or child["name"].lower().replace(" ", "-")
            Menu.objects.update_or_create(
                slug=child_slug,
                defaults={
                    "name": child["name"],
                    "icon": child.get("icon", ""),
                    "url": child.get("url", ""),
                    "parent": menu,
                    "sort_order": child.get("sort_order", 0),
                    "module": child.get("module", item.get("module", "")),
                    "level": menu.level + 1,
                    "is_active": True,
                },
            )


def _uninstall_menus(menu_config: list[dict]) -> None:
    slugs = []
    for item in menu_config:
        slugs.append(item.get("slug") or item["name"].lower().replace(" ", "-"))
        for child in item.get("children", []):
            slugs.append(child.get("slug") or child["name"].lower().replace(" ", "-"))
    Menu.objects.filter(slug__in=slugs).update(is_active=False)


def _install_page_configs(page_config: list[dict]) -> None:
    for cfg in page_config:
        page_key = cfg.get("page_key", "")
        if not page_key:
            continue
        PageConfig.objects.update_or_create(
            page_key=page_key,
            defaults={
                "page_title": cfg.get("page_title", page_key),
                "page_type": cfg.get("page_type", "list"),
                "module": cfg.get("module", ""),
                "entity_model": cfg.get("entity_model", ""),
                "api_endpoint": cfg.get("api_endpoint", ""),
                "layout": cfg.get("layout", "single"),
                "is_active": True,
            },
        )


def _install_workflows(
    workflow_config: list[dict], company_id: UUID, user_id: UUID | None
) -> None:
    for wf in workflow_config:
        WorkflowDefinition.objects.update_or_create(
            name=wf.get("name", ""),
            company_id=company_id,
            defaults={
                "module": wf.get("module", ""),
                "document_type": wf.get("document_type", ""),
                "flow_data": wf.get("flow_data", {}),
                "is_active": True,
                "created_by_id": user_id,
            },
        )


def _uninstall_workflows(workflow_config: list[dict], company_id: UUID) -> None:
    names = [wf.get("name", "") for wf in workflow_config if wf.get("name")]
    WorkflowDefinition.objects.filter(name__in=names, company_id=company_id).update(
        is_active=False
    )


def _install_seed_data(seed_data: dict) -> None:
    if not seed_data:
        return
    logger.info(
        "Seed data keys: %s (install not yet implemented)", list(seed_data.keys())
    )
