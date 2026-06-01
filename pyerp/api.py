"""API root router — all /api/v1/ endpoints."""

from django.urls import include, path

api_patterns = [
    # Module endpoints will be registered here as they are built
    # Example: path("financial/", include("apps.financial.api.urls")),
]

urlpatterns = [
    path("", include(api_patterns)),
]
