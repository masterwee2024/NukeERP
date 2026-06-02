"""Middleware — company context and CSRF exemption for API routes."""

from django.utils.deprecation import MiddlewareMixin
from django.views.decorators.csrf import csrf_exempt

from apps.core.models import Company


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
