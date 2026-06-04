"""API root router — all /api/v1/ endpoints."""

from django.urls import path
from ninja import NinjaAPI

from apps.core.api import router as core_router
from apps.core.api.auth import JWTAuth
from apps.financial.api.account_api import router as financial_router

api = NinjaAPI(
    auth=JWTAuth(),
    urls_namespace="api-v1",
    title="pyERP API",
    version="1.0.0",
)

# Core endpoints
api.add_router("/core/", core_router, tags=["core"])

# Financial endpoints
api.add_router("/financial/", financial_router, tags=["financial"])

urlpatterns = [
    path("", api.urls),
]
