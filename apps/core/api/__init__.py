"""Core API — all /api/v1/core/ endpoints."""

from ninja import Router

from apps.core.api.attachment_api import router as attachment_router
from apps.core.api.audit_api import router as audit_router
from apps.core.api.auth_api import router as auth_router
from apps.core.api.company_api import router as company_router
from apps.core.api.email_settings_api import router as email_settings_router
from apps.core.api.menu_api import router as menu_router
from apps.core.api.numbering_api import router as numbering_router
from apps.core.api.page_config_api import router as page_config_router
from apps.core.api.rbac_api import router as rbac_router
from apps.core.api.user_api import router as user_admin_router
from apps.core.api.workflow_api import admin_router as workflow_admin_router
from apps.core.api.workflow_api import router as workflow_execution_router

router = Router()
router.add_router("/attachments/", attachment_router, tags=["attachments"])
router.add_router("/auth/", auth_router, tags=["auth"])
router.add_router("/companies/", company_router, tags=["companies"])
router.add_router("/menus/", menu_router, tags=["menus"])
router.add_router("/page-configs/", page_config_router, tags=["page-configs"])
router.add_router("/admin/", rbac_router, tags=["admin"])
router.add_router("/admin/", user_admin_router, tags=["admin"])
router.add_router("/admin/", workflow_admin_router, tags=["admin"])
router.add_router("/admin/", email_settings_router, tags=["admin"])
router.add_router("/admin/", numbering_router, tags=["admin"])
router.add_router("/admin/", audit_router, tags=["admin"])
router.add_router("/workflows/", workflow_execution_router, tags=["workflows"])
