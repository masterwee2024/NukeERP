"""API root router — all /api/v1/ endpoints."""

from django.urls import path
from ninja import NinjaAPI
from ninja.security import django_auth

from apps.core.api import router as core_router

api = NinjaAPI(
    auth=django_auth,
    urls_namespace="api-v1",
    title="pyERP API",
    version="1.0.0",
)

# Core endpoints (auth endpoints are public)
api.add_router("/core/", core_router, tags=["core"])

urlpatterns = [
    path("", api.urls),
]
