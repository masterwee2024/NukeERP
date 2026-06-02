"""API root router — all /api/v1/ endpoints."""

from django.urls import path
from ninja import NinjaAPI
from ninja.security.session import SessionAuth

from apps.core.api import router as core_router
from apps.core.api.auth import JWTAuth

api = NinjaAPI(
    # SessionAuth without CSRF — API routes use JWT, CSRF not applicable
    auth=[SessionAuth(csrf=False), JWTAuth()],
    urls_namespace="api-v1",
    title="pyERP API",
    version="1.0.0",
)

# Core endpoints
api.add_router("/core/", core_router, tags=["core"])

urlpatterns = [
    path("", api.urls),
]
