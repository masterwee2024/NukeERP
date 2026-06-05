"""API root router — all /api/v1/ endpoints."""

from django.urls import path
from ninja import NinjaAPI

from apps.core.api import router as core_router
from apps.core.api.auth import JWTAuth
from apps.financial.api.account_api import router as financial_account_router
from apps.financial.api.journal_api import router as financial_journal_router
from apps.financial.api.period_api import router as financial_period_router
from apps.financial.api.tax_api import router as financial_tax_router

api = NinjaAPI(
    auth=JWTAuth(),
    urls_namespace="api-v1",
    title="pyERP API",
    version="1.0.0",
)

# Core endpoints
api.add_router("/core/", core_router, tags=["core"])

# Financial endpoints
api.add_router("/financial/", financial_account_router, tags=["financial"])
api.add_router("/financial/", financial_journal_router, tags=["financial"])
api.add_router("/financial/", financial_tax_router, tags=["financial"])
api.add_router("/financial/", financial_period_router, tags=["financial"])

urlpatterns = [
    path("", api.urls),
]
