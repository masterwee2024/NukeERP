"""Middleware — company context and conditional CSRF."""

from django.middleware.csrf import CsrfViewMiddleware
from django.utils.deprecation import MiddlewareMixin

from apps.core.models import Company


class ConditionalCSRFMiddleware(CsrfViewMiddleware):
    """CSRF middleware that skips checks for /api/v1/ routes (handled by JWT)."""

    def process_view(self, request, callback, callback_args, callback_kwargs):
        if request.path.startswith("/api/v1/"):
            request.csrf_processing_done = True
            return None
        return super().process_view(request, callback, callback_args, callback_kwargs)


class CompanyMiddleware(MiddlewareMixin):
    """Reads X-Company-Id header and sets request.company.

    Falls back to user's default/current company if no header is provided.
    """

    def process_request(self, request):
        company_id = request.META.get("HTTP_X_COMPANY_ID")
        company = None

        if company_id:
            try:
                company = Company.objects.get(id=company_id, is_active=True)
            except (Company.DoesNotExist, ValueError):
                pass

        if (
            company is None
            and hasattr(request, "user")
            and request.user.is_authenticated
        ):
            company = request.user.current_company
            if company is None or not company.is_active:
                from apps.core.models import UserCompany

                uc = (
                    UserCompany.objects.filter(user=request.user, is_default=True)
                    .select_related("company")
                    .first()
                )
                if uc:
                    company = uc.company
                else:
                    uc = (
                        UserCompany.objects.filter(user=request.user)
                        .select_related("company")
                        .first()
                    )
                    if uc:
                        company = uc.company

        request.company = company
