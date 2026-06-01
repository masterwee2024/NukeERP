"""Core API — all /api/v1/core/ endpoints."""

from ninja import Router

from apps.core.api.menu_api import router as menu_router

router = Router()
router.add_router("/menus/", menu_router, tags=["menus"])
