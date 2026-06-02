"""API root router — all /api/v1/ endpoints."""

from django.urls import path
from django.views.decorators.csrf import csrf_exempt
from ninja import NinjaAPI
from ninja.security import django_auth

from apps.core.api import router as core_router
from apps.core.api.auth import JWTAuth

api = NinjaAPI(
    auth=[django_auth, JWTAuth()],
    urls_namespace="api-v1",
    title="pyERP API",
    version="1.0.0",
)

# Core endpoints
api.add_router("/core/", core_router, tags=["core"])

# Apply csrf_exempt to all NinjaAPI views
urlpatterns, app_name, namespace = api.urls
for pattern in urlpatterns:
    if hasattr(pattern, "callback"):
        pattern.callback = csrf_exempt(pattern.callback)

urlpatterns = [
    path("", (urlpatterns, app_name, namespace)),
]
