"""Industry template engine API endpoints."""

from ninja import Router, Schema
from ninja.errors import HttpError

from apps.core.mixins.models import ConcurrencyError
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

router = Router()


class InstallOut(Schema):
    template_code: str
    template_name: str
    company_id: str
    status: str
    installation_id: str
    menu_created: int = 0
    page_configs_created: int = 0
    workflows_created: int = 0


class UninstallOut(Schema):
    template_code: str
    company_id: str
    status: str


class TemplatePreviewOut(Schema):
    code: str
    name: str
    version: str
    menu_count: int
    page_config_count: int
    workflow_count: int
    gl_account_count: int
    report_count: int
    has_seed_data: bool
    module_dependencies: list[str]


class TemplateOut(Schema):
    id: str | None = None
    name: str
    code: str
    version: str
    description: str = ""
    module_dependencies: list[str] = []
    menu_items: list[dict] = []
    page_configs: list[dict] = []
    workflow_config: list[dict] = []
    gl_account_config: list[dict] = []
    report_config: list[dict] = []
    seed_data: dict = {}


class InstalledTemplateOut(Schema):
    id: str
    template_code: str
    template_name: str
    installed_at: str
    status: str


def _require_company_id(request):
    cid = getattr(request.auth, "current_company_id", None)
    if not cid:
        raise HttpError(400, "No company selected")
    return cid


@router.get("/import/", response=TemplateOut)
def import_template_docs(request):
    """GET is not supported — use POST for import."""
    raise HttpError(405, "Use POST to import a template")


@router.get("/installed/", response=list[InstalledTemplateOut])
def list_installed_templates(request):
    company_id = _require_company_id(request)
    installations = get_installed_templates(company_id)
    results = []
    for inst in installations:
        results.append(
            InstalledTemplateOut(
                id=str(inst.id),
                template_code=inst.template.code,
                template_name=inst.template.name,
                installed_at=inst.installed_at.isoformat(),
                status=inst.status,
            )
        )
    return results


@router.get("/", response=list[TemplateOut])
def list_templates(request):
    templates = get_all_templates()
    results = []
    for t in templates:
        results.append(
            TemplateOut(
                id=str(t.id),
                name=t.name,
                code=t.code,
                version=t.template_version,
                description=t.description,
                module_dependencies=t.module_dependencies,
                menu_items=t.menu_config,
                page_configs=t.page_config,
                workflow_config=t.workflow_config,
                gl_account_config=t.gl_account_config,
                report_config=t.report_config,
                seed_data=t.seed_data,
            )
        )
    return results


@router.get("/{code}/", response=TemplateOut)
def get_template_detail(request, code: str):
    tmpl = get_template(code)
    if tmpl is None:
        raise HttpError(404, f"Template '{code}' not found")
    return TemplateOut(
        id=str(tmpl.id),
        name=tmpl.name,
        code=tmpl.code,
        version=tmpl.template_version,
        description=tmpl.description,
        module_dependencies=tmpl.module_dependencies,
        menu_items=tmpl.menu_config,
        page_configs=tmpl.page_config,
        workflow_config=tmpl.workflow_config,
        gl_account_config=tmpl.gl_account_config,
        report_config=tmpl.report_config,
        seed_data=tmpl.seed_data,
    )


@router.get("/{code}/preview/", response=TemplatePreviewOut)
def preview_template(request, code: str):
    result = preview_installation(code)
    if "error" in result:
        raise HttpError(404, result["error"])
    return TemplatePreviewOut(**result)


@router.get("/{code}/export/", response=TemplateOut)
def export_template_endpoint(request, code: str):
    data = export_template(code)
    if data is None:
        raise HttpError(404, f"Template '{code}' not found")
    return TemplateOut(
        id=None,
        name=data["name"],
        code=data["code"],
        version=data["version"],
        description=data["description"],
        module_dependencies=data["module_dependencies"],
        menu_items=data["menu_items"],
        page_configs=data["page_configs"],
        workflow_config=data["workflow_config"],
        gl_account_config=data["gl_account_config"],
        report_config=data["report_config"],
        seed_data=data["seed_data"],
    )


@router.post("/import/", response=TemplateOut)
def import_template_endpoint(request, payload: TemplateOut):
    if not request.auth.is_superuser:
        raise HttpError(403, "Only superusers can import templates")
    json_data = payload.model_dump(exclude={"id"})
    json_data["menu_items"] = json_data.pop("menu_items", [])
    json_data["page_configs"] = json_data.pop("page_configs", [])
    try:
        tmpl = import_template(json_data, request.auth.id)
    except ConcurrencyError as e:
        raise HttpError(409, str(e)) from e
    return TemplateOut(
        id=str(tmpl.id),
        name=tmpl.name,
        code=tmpl.code,
        version=tmpl.template_version,
        description=tmpl.description,
        module_dependencies=tmpl.module_dependencies,
        menu_items=tmpl.menu_config,
        page_configs=tmpl.page_config,
        workflow_config=tmpl.workflow_config,
        gl_account_config=tmpl.gl_account_config,
        report_config=tmpl.report_config,
        seed_data=tmpl.seed_data,
    )


@router.post("/{code}/install/", response=InstallOut)
def install_template_endpoint(request, code: str):
    if not request.auth.is_superuser:
        raise HttpError(403, "Only superusers can install templates")
    company_id = _require_company_id(request)
    tmpl = get_template(code)
    if tmpl is None:
        raise HttpError(404, f"Template '{code}' not found")
    try:
        result = install_template(tmpl.id, company_id, request.auth.id)
    except ValueError as e:
        raise HttpError(400, str(e)) from e
    except ConcurrencyError as e:
        raise HttpError(409, str(e)) from e
    return InstallOut(**result)


@router.post("/{code}/uninstall/", response=UninstallOut)
def uninstall_template_endpoint(request, code: str):
    if not request.auth.is_superuser:
        raise HttpError(403, "Only superusers can uninstall templates")
    company_id = _require_company_id(request)
    tmpl = get_template(code)
    if tmpl is None:
        raise HttpError(404, f"Template '{code}' not found")
    try:
        result = uninstall_template(tmpl.id, company_id)
    except ValueError as e:
        raise HttpError(400, str(e)) from e
    except ConcurrencyError as e:
        raise HttpError(409, str(e)) from e
    return UninstallOut(**result)
