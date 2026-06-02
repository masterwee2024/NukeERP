"""Core API — all /api/v1/core/ endpoints."""

from ninja import Router

from apps.core.api.auth_api import router as auth_router
from apps.core.api.company_api import router as company_router
from apps.core.api.menu_api import router as menu_router
from apps.core.api.page_config_api import router as page_config_router
from apps.core.api.rbac_api import router as rbac_router

router = Router()
router.add_router("/auth/", auth_router, tags=["auth"])
router.add_router("/companies/", company_router, tags=["companies"])
router.add_router("/menus/", menu_router, tags=["menus"])
router.add_router("/page-configs/", page_config_router, tags=["page-configs"])
router.add_router("/admin/", rbac_router, tags=["admin"])
