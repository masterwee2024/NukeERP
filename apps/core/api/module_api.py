"""Module plugin interface API endpoints."""

from ninja import Router
from ninja.errors import HttpError

from apps.core.platform.module_registry import registry
from apps.core.platform.schemas import ModuleDetailSchema

router = Router()


@router.get("/", response=list[ModuleDetailSchema])
def list_modules(request):
    return registry.get_all_modules()


@router.get("/{code}/", response=ModuleDetailSchema)
def get_module(request, code: str):
    mod = registry.get_module(code)
    if mod is None:
        raise HttpError(404, f"Module '{code}' not found")
    return mod


@router.get("/{code}/dependencies/", response=list[ModuleDetailSchema])
def get_dependencies(request, code: str):
    mod = registry.get_module(code)
    if mod is None:
        raise HttpError(404, f"Module '{code}' not found")
    return registry.get_module_dependencies(code)


@router.post("/{code}/activate/", response=ModuleDetailSchema)
def activate_module(request, code: str):
    if not request.auth.is_superuser:
        raise HttpError(403, "Only superusers can activate modules")
    result = registry.activate(code)
    if result is None:
        raise HttpError(404, f"Module '{code}' not found")
    return result


@router.post("/{code}/deactivate/", response=ModuleDetailSchema)
def deactivate_module(request, code: str):
    if not request.auth.is_superuser:
        raise HttpError(403, "Only superusers can deactivate modules")
    result = registry.deactivate(code)
    if result is None:
        raise HttpError(404, f"Module '{code}' not found")
    return result
