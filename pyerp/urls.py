"""Root URL configuration for pyERP."""

from django.conf import settings
from django.conf.urls.static import static
from django.urls import include, path

from apps.core.admin import admin_site

urlpatterns = [
    path("admin/", admin_site.urls),
    path("api/v1/", include("pyerp.api")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
